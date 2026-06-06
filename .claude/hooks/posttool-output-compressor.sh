#!/usr/bin/env bash
# posttool-output-compressor.sh — PostToolUse:Read|Bash — 工具输出压缩
# Role: 压缩 Read/Bash 工具的输出，减少低阶模型的上下文膨胀，不损失关键信息
# P0: 纯规则压缩（行数/字数阈值），利用磁盘缓存去重
#
# 挂载点: PostToolUse → Read / Bash / .*
# 输入: stdin JSON(hook_event_name, tool_name, tool_input, tool_response, args)
# 输出: additionalContext 注入压缩语义，不影响原始 tool_result
#
# 配置（harness.yaml）:
#   output_compressor.enabled: true/false
#   output_compressor.read_line_limit: 100
#   output_compressor.bash_char_limit: 2000

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "output_compressor" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)
# 快速预过滤: 只处理 Read 和 Bash 事件
# 提取工具名和环境变量
TOOL_NAME=""
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .args.tool_name // empty' 2>/dev/null)
    if [ -z "$TOOL_NAME" ]; then
        # 从 matcher 推断
        if echo "$INPUT" | jq -e '.tool_input.command // .args.command' &>/dev/null; then
            TOOL_NAME="Bash"
        elif echo "$INPUT" | jq -e '.tool_input.file_path // .args.filePath // .args.file_path' &>/dev/null; then
            TOOL_NAME="Read"
        fi
    fi
else
    # 无 jq 回退
    TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_name', '') or d.get('args', {}).get('tool_name', ''))
except: pass" 2>/dev/null)
    if [ -z "$TOOL_NAME" ]; then
        if echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Bash' if d.get('tool_input', {}).get('command') or d.get('args', {}).get('command') else '')" 2>/dev/null | grep -q 'Bash'; then
            TOOL_NAME="Bash"
        elif echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Read' if d.get('tool_input', {}).get('file_path') or d.get('args', {}).get('filePath') else '')" 2>/dev/null | grep -q 'Read'; then
            TOOL_NAME="Read"
        fi
    fi
fi

[ "$TOOL_NAME" != "Read" ] && [ "$TOOL_NAME" != "Bash" ] && { echo '{"continue": true}'; exit 0; }

# 提取配置参数
READ_LINE_LIMIT=$(hc_get "output_compressor.read_line_limit" "100")
BASH_CHAR_LIMIT=$(hc_get "output_compressor.bash_char_limit" "2000")

# 用 Python 执行核心压缩逻辑（可处理复杂文本操作）
# 设置环境变量供 python 使用
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR/output-cache" 2>/dev/null

export STATE_DIR
export CC_READ_LINE_LIMIT="$READ_LINE_LIMIT"
export CC_BASH_CHAR_LIMIT="$BASH_CHAR_LIMIT"

echo "$INPUT" | "${PYTHON_BIN:-python3}" "$SCRIPT_DIR/posttool-output-compressor.py"
exit 0
