#!/bin/bash

# harness-kit:managed v1.0.2

# build-validator.sh — PostToolUse:Bash 构建失败自动记录 + 修复建议

# 功能：当 AI 执行构建命令失败时，自动记录错误到日志并给出针对性修复建议

# 输出格式：JSON hookSpecificOutput


source "$(dirname "$0")/harness_config.sh"
hc_enabled "build_validator" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    STDOUT_RESULT=$(echo "$INPUT" | jq -r '.tool_response.stdout // empty' 2>/dev/null)
    STDERR_RESULT=$(echo "$INPUT" | jq -r '.tool_response.stderr // empty' 2>/dev/null)
    EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // "0"' 2>/dev/null)
    # R23: PostToolUseFailure schema — 顶层 error 字段，无 tool_response
    EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null)
    TOP_ERROR=$(echo "$INPUT" | jq -r '.error // empty' 2>/dev/null)
    if [ "$EVENT" = "PostToolUseFailure" ]; then
        [ "$EXIT_CODE" = "0" ] && EXIT_CODE="1"
        [ -z "$STDERR_RESULT" ] && STDERR_RESULT="$TOP_ERROR"
    fi
else
    COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except:
    pass" 2>/dev/null)
    STDOUT_RESULT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_response', {}).get('stdout', ''))
except:
    pass" 2>/dev/null)
    STDERR_RESULT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_response', {}).get('stderr', ''))
except:
    pass" 2>/dev/null)
    EXIT_CODE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_response', {}).get('exit_code', '0'))
except:
    pass" 2>/dev/null)
fi

if [ -z "$COMMAND" ]; then
    echo '{"continue": true}'
    exit 0
fi

BUILD_CMDS=$(hc_get "build_validator.build_commands" "go build go test npm run build npm test pytest python -m pytest cargo build make mvn gradle webpack vite tsc")
IS_BUILD=false
CMD_PREFIX=$(echo "$COMMAND" | awk '{print $1}')
CMD_PREFIX2=$(echo "$COMMAND" | awk '{print $1, $2}')

if echo "$BUILD_CMDS" | grep -qF "$CMD_PREFIX2"; then
    IS_BUILD=true
elif echo "$BUILD_CMDS" | grep -qwF "$CMD_PREFIX"; then
    IS_BUILD=true
fi

if [ "$IS_BUILD" = false ]; then
    echo '{"continue": true}'
    exit 0
fi

if [ "$EXIT_CODE" = "0" ] || [ "$EXIT_CODE" = "" ]; then
    echo '{"continue": true}'
    exit 0
fi

FULL_OUTPUT="${STDOUT_RESULT}${STDERR_RESULT}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
LOG_FILE="$STATE_DIR/build-errors.log"
mkdir -p "$STATE_DIR"

export COMMAND
export FULL_OUTPUT
export EXIT_CODE
export LOG_FILE
export PROJECT_ROOT
export SCRIPT_DIR

RESULT=$(python3 - <<'PYEOF'
import json, os, re, sys
from datetime import datetime, timezone

command = os.environ.get('COMMAND', '')
full_output = os.environ.get('FULL_OUTPUT', '')
exit_code = os.environ.get('EXIT_CODE', '1')
log_file = os.environ.get('LOG_FILE', '')
project_root = os.environ.get('PROJECT_ROOT', '')
script_dir = os.environ.get('SCRIPT_DIR', '')

timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def _classify_and_suggest_fallback(output, cmd):
    categories = []
    # --- Go 错误 ---
    if re.search(r'\.go:\d+:\d+:', output):
        go_errors = re.findall(r'(\S+\.go:\d+:\d+):\s*(.+)', output)
        if go_errors:
            file_path, error_msg = go_errors[0]
            categories.append({
                "type": "go_compile",
                "file": file_path.split(':')[0],
                "line": file_path.split(':')[1],
                "message": error_msg.strip()[:200],
                "suggestions": [
                    f"检查 {file_path.split(':')[0]}:{file_path.split(':')[1]} 的语法",
                    "运行 `go vet ./...` 检查潜在问题",
                    "确认导入包路径正确 (`go mod tidy`)"
                ]
            })
    if 'undefined:' in output.lower() or 'undeclared name' in output.lower():
        categories.append({
            "type": "go_undefined",
            "message": "未定义的标识符",
            "suggestions": [
                "检查变量/函数名拼写是否正确",
                "确认是否在正确的包作用域内",
                "运行 `go mod tidy` 确保依赖完整"
            ]
        })
    if 'imported and not used' in output:
        categories.append({
            "type": "go_unused_import",
            "message": "导入了未使用的包",
            "suggestions": [
                "删除未使用的 import",
                "如果需要使用 side effect，改为 `_ \"package\"`"
            ]
        })
    # --- TypeScript/JavaScript 错误 ---
    ts_match = re.search(r'error\s+(TS\d+):\s*(.+)', output)
    if ts_match:
        categories.append({
            "type": "typescript",
            "code": ts_match.group(1),
            "message": ts_match.group(2).strip()[:200],
            "suggestions": [
                "查阅 TypeScript 文档: https://www.typescriptlang.org/docs/handbook/release-notes/",
                "运行 `npx tsc --noEmit` 查看完整类型错误列表",
                "检查 tsconfig.json 的 strict 设置"
            ]
        })
    if "cannot find module" in output.lower() or "module not found" in output.lower():
        categories.append({
            "type": "missing_module",
            "message": "找不到模块",
            "suggestions": [
                "运行 `npm install` 或 `pnpm install` 安装依赖",
                "检查 import 路径是否正确",
                "确认 node_modules 是否存在 (`ls node_modules/`)"
            ]
        })
    # --- Python 错误 ---
    py_match = re.search(r'((?:Type|Value|Import|Attribute|Name|Key|Index|Runtime|Syntax)Error):\s*(.+)', output)
    if py_match:
        categories.append({
            "type": "python_error",
            "error_type": py_match.group(1),
            "message": py_match.group(2).strip()[:200],
            "suggestions": [
                f"检查 {py_match.group(1)} 的具体原因",
                "运行 `python -m py_compile <file>` 检查语法",
                "确认虚拟环境已激活且依赖已安装 (`pip list`)"
            ]
        })
    if "no module named" in output.lower():
        categories.append({
            "type": "python_missing_module",
            "message": "找不到 Python 模块",
            "suggestions": [
                "运行 `pip install <module_name>` 安装缺失的包",
                "确认使用了正确的 Python 解释器 (`which python`)",
                "检查 PYTHONPATH 环境变量"
            ]
        })
    # --- Rust 错误 ---
    if re.search(r'error\[E\d+\]:', output):
        rust_match = re.search(r'error\[(E\d+)\]:\s*(.+)', output)
        if rust_match:
            categories.append({
                "type": "rust_compile",
                "code": rust_match.group(1),
                "message": rust_match.group(2).strip()[:200],
                "suggestions": [
                    f"运行 `rustc --explain {rust_match.group(1)}` 获取详细解释",
                    "运行 `cargo check` 快速验证",
                    "检查 borrow checker 相关的所有权和生命周期"
                ]
            })
    # --- Make 错误 ---
    if "make:" in output or "Makefile" in output:
        categories.append({
            "type": "make_error",
            "message": "Make 构建失败",
            "suggestions": [
                "检查 Makefile 中的目标和依赖",
                "运行 `make -n` 查看实际执行的命令",
                "确认所有依赖工具已安装"
            ]
        })
    # --- 通用错误模式 ---
    if "permission denied" in output.lower():
        categories.append({
            "type": "permission",
            "message": "权限被拒绝",
            "suggestions": [
                "检查文件/目录权限 (`ls -la`)",
                "确认有足够的执行权限",
                "不要使用 sudo，检查项目目录所有权"
            ]
        })
    if "out of memory" in output.lower() or "oom" in output.lower():
        categories.append({
            "type": "oom",
            "message": "内存不足",
            "suggestions": [
                "减少并行度 (如 `GOMAXPROCS=1` 或 `--max-old-space-size`)",
                "关闭其他占用内存的程序",
                "增加 swap 空间"
            ]
        })
    # --- 无匹配分类时的通用建议 ---
    if not categories:
        categories.append({
            "type": "unknown",
            "message": f"构建命令退出码 {exit_code}",
            "suggestions": [
                "仔细阅读第一条错误信息（通常后续错误是级联的）",
                "运行 `git diff` 确认最近的改动",
                "尝试最小化复现：只编译修改的文件",
                "检查 CI/CD 是否有相同的失败"
            ]
        })
    return categories

# Try shared error_classifier.py first
_ec_path = os.path.abspath(os.path.join(script_dir, '..', 'scripts', 'error_classifier.py'))
_ec_available = False
if os.path.exists(_ec_path):
    try:
        sys.path.insert(0, os.path.dirname(_ec_path))
        from error_classifier import classify_error as _ec_classify
        def classify_and_suggest(output, cmd):
            return _ec_classify(cmd, exit_code, output)
        _ec_available = True
    except Exception:
        pass

if not _ec_available:
    classify_and_suggest = _classify_and_suggest_fallback

errors = classify_and_suggest(full_output, command)

log_entry = {
    "timestamp": timestamp,
    "command": command[:500],
    "exit_code": exit_code,
    "errors": errors,
    "output_excerpt": full_output[:2000]
}

with open(log_file, 'a', encoding='utf-8') as f:
    f.write(f"=== {timestamp} ===\n")
    f.write(f"Command: {command}\n")
    f.write(f"Exit Code: {exit_code}\n")
    for err in errors:
        f.write(f"\n[{err['type'].upper()}] {err.get('message', '')}\n")
        for i, sug in enumerate(err.get('suggestions', []), 1):
            f.write(f"  {i}. {sug}\n")
    f.write(f"\n--- Output Excerpt ---\n")
    lines = full_output.split('\n')[:50]
    f.write('\n'.join(lines))
    f.write("\n\n")

msg_parts = [f"[构建失败] 命令: {command[:100]}"]
msg_parts.append(f"退出码: {exit_code}")
for err in errors:
    msg_parts.append(f"\n错误类型: {err['type']}")
    if err.get('file'):
        msg_parts.append(f"文件: {err['file']}:{err.get('line', '?')}")
    if err.get('message'):
        msg_parts.append(f"信息: {err['message'][:150]}")
    msg_parts.append("修复建议:")
    for i, sug in enumerate(err.get('suggestions', []), 1):
        msg_parts.append(f"  {i}. {sug}")
msg_parts.append(f"\n详细日志: {log_file}")

msg = '\n'.join(msg_parts)
msg_escaped = msg.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')

print(f'{{"continue": true, "hookSpecificOutput": {{"hookEventName": "PostToolUse", "additionalContext": "{msg_escaped}"}}}}')
PYEOF)

if [ -n "$RESULT" ]; then
    echo "$RESULT"
else
    echo '{"continue": true}'
fi

exit 0
