#!/usr/bin/env python3
"""build-validator.py — PostToolUse:Bash / PostToolUseFailure:Bash — 构建失败自动记录错误日志并给出针对性修复建议
Role: 构建失败自动记录错误日志并给出针对性修复建议

等效移植自 build-validator.sh (343行)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, hc_emit_hook_json, flywheel_event, output_continue


def _classify_and_suggest_fallback(output, cmd, exit_code_val='1'):
    """Fallback error classifier (no shared error_classifier.py available)."""
    categories = []

    # --- Go errors ---
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
    # --- TypeScript/JavaScript errors ---
    ts_match = re.search(r'([^\s]+\.(ts|tsx|js|jsx)):(\d+):\d+\s+-\s+error\s+(TS\d+):\s*(.+)', output)
    if ts_match:
        categories.append({
            "type": "typescript",
            "file": ts_match.group(1),
            "line": ts_match.group(3),
            "code": ts_match.group(4),
            "message": f"[{ts_match.group(4)}] {ts_match.group(5).strip()[:160]}",
            "suggestions": [
                f"检查 {ts_match.group(1)}:{ts_match.group(3)} 的类型错误",
                "运行 `npx tsc --noEmit` 查看完整类型错误列表",
                "检查 tsconfig.json 的 strict 设置"
            ]
        })
    else:
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
    # --- Python errors ---
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
    # --- Rust errors ---
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
    # --- Make errors ---
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
    # --- Common error patterns ---
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
    # --- Unknown ---
    if not categories:
        categories.append({
            "type": "unknown",
            "message": f"构建命令退出码 {exit_code_val}",
            "suggestions": [
                "仔细阅读第一条错误信息（通常后续错误是级联的）",
                "运行 `git diff` 确认最近的改动",
                "尝试最小化复现：只编译修改的文件",
                "检查 CI/CD 是否有相同的失败"
            ]
        })
    return categories


def main():
    # ─── hc_enabled 门禁 ───
    if not hc_enabled('build_validator'):
        output_continue()
        return

    flywheel_event('build_validator', 'active', 'P2')

    # 读取 stdin
    INPUT = sys.stdin.read()

    # ─── 解析 JSON ───
    try:
        data = json.loads(INPUT)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    COMMAND = ''
    STDOUT_RESULT = ''
    STDERR_RESULT = ''
    EXIT_CODE = '0'
    EVENT = ''
    TOP_ERROR = ''

    COMMAND = data.get('tool_input', {}).get('command', '') or ''
    if not COMMAND:
        COMMAND = data.get('args', {}).get('command', '') or ''
    STDOUT_RESULT = data.get('tool_response', {}).get('stdout', '') or ''
    STDERR_RESULT = data.get('tool_response', {}).get('stderr', '') or ''
    EXIT_CODE = str(data.get('tool_response', {}).get('exit_code', '0') or '0')
    EVENT = data.get('hook_event_name', '') or ''
    TOP_ERROR = data.get('error', '') or ''

    if EVENT == 'PostToolUseFailure':
        if EXIT_CODE == '0':
            EXIT_CODE = '1'
        if not STDERR_RESULT:
            STDERR_RESULT = TOP_ERROR

    if not COMMAND:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # ─── Build command check ───
    BUILD_CMDS = hc_get('build_validator.build_commands', 'go build go test npm run build npm test pytest python -m pytest cargo build make mvn gradle webpack vite tsc')
    cmd_parts = COMMAND.split()
    CMD_PREFIX = cmd_parts[0] if cmd_parts else ''
    CMD_PREFIX2 = ' '.join(cmd_parts[:2]) if len(cmd_parts) >= 2 else ''

    IS_BUILD = False
    build_list = BUILD_CMDS.split()
    if CMD_PREFIX2 in build_list:
        IS_BUILD = True
    elif CMD_PREFIX in build_list:
        IS_BUILD = True

    if not IS_BUILD:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    if EXIT_CODE in ('0', ''):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # ─── 路径 ───
    SCRIPT_DIR = _HOOKS_DIR
    PROJECT_ROOT = (SCRIPT_DIR / '../..').resolve()
    STATE_DIR = PROJECT_ROOT / '.omc' / 'state'
    LOG_FILE = STATE_DIR / 'build-errors.log'
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    full_output = STDOUT_RESULT + STDERR_RESULT

    # ─── Classifier ───
    SCRIPT_DIR_STR = str(SCRIPT_DIR)
    exit_code_str = EXIT_CODE

    # Try shared error_classifier.py first
    _ec_path = os.path.abspath(os.path.join(SCRIPT_DIR_STR, '..', 'scripts', 'error_classifier.py'))
    _ec_available = False
    classify_and_suggest = None

    if os.path.exists(_ec_path):
        try:
            sys.path.insert(0, os.path.dirname(_ec_path))
            from error_classifier import classify_error as _ec_classify  # type: ignore
            def classify_and_suggest(output, cmd):
                return _ec_classify(cmd, exit_code_str, output)
            _ec_available = True
        except Exception:
            pass

    if not _ec_available:
        classify_and_suggest = lambda output, cmd: _classify_and_suggest_fallback(output, cmd, exit_code_str)

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    errors = classify_and_suggest(full_output, COMMAND)

    # ─── Write log ───
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"=== {timestamp} ===\n")
        f.write(f"Command: {COMMAND}\n")
        f.write(f"Exit Code: {EXIT_CODE}\n")
        for err in errors:
            f.write(f"\n[{err['type'].upper()}] {err.get('message', '')}\n")
            for i, sug in enumerate(err.get('suggestions', []), 1):
                f.write(f"  {i}. {sug}\n")
        f.write("\n--- Output Excerpt ---\n")
        lines = full_output.split('\n')[:50]
        f.write('\n'.join(lines))
        f.write("\n\n")

    # ─── Rotation: keep last max_log_entries ───
    max_entries = int(hc_get('build_validator.max_log_entries', '50'))
    with open(LOG_FILE, 'r', encoding='utf-8') as rf:
        raw = rf.read()
    entries = [e for e in raw.split('=== ')[1:] if e.strip()]
    if len(entries) > max_entries:
        keep = entries[-max_entries:]
        with open(LOG_FILE, 'w', encoding='utf-8') as wf:
            for entry in keep:
                wf.write('=== ' + entry + ('\n' if not entry.endswith('\n') else ''))

    # ─── Build output message ───
    msg_parts = [f"[构建失败] 命令: {COMMAND[:100]}"]
    msg_parts.append(f"退出码: {EXIT_CODE}")
    for err in errors:
        msg_parts.append(f"\n错误类型: {err['type']}")
        if err.get('file'):
            msg_parts.append(f"文件: {err['file']}:{err.get('line', '?')}")
        if err.get('message'):
            msg_parts.append(f"信息: {err['message'][:150]}")
        msg_parts.append("修复建议:")
        for i, sug in enumerate(err.get('suggestions', []), 1):
            msg_parts.append(f"  {i}. {sug}")
    msg_parts.append(f"\n详细日志: {LOG_FILE}")
    msg = '\n'.join(msg_parts)
    msg_escaped = msg.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')

    result_json = json.dumps({
        'continue': True,
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': msg
        }
    })
    print(result_json)
    sys.exit(0)


if __name__ == '__main__':
    main()
