#!/bin/bash

# harness-kit:managed v1.0.2

# read-tracker.sh — PostToolUse:Read Hook

# 功能：记录已读取的文件路径（realpath 规范化），供 edit-guard.sh 检查

# 退出码：始终 0（fail-open，记录失败不阻断正常操作）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "read_tracker" || exit 0
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
READ_LOG="$STATE_DIR/read-files.log"

# 提取 file_path 字段
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except:
    pass" 2>/dev/null)
fi

# 无路径 → 静默退出
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# 规范化路径（realpath 解析符号链接和相对路径）
REAL_PATH=$(realpath "$FILE_PATH" 2>/dev/null)
if [ -z "$REAL_PATH" ]; then
    REAL_PATH="$FILE_PATH"
fi

# 确保状态目录存在
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# 去重写入（工具调用为顺序执行，竞态风险极低）
if [ -f "$READ_LOG" ] && grep -qxF "$REAL_PATH" "$READ_LOG" 2>/dev/null; then
    exit 0
fi
echo "$REAL_PATH" >> "$READ_LOG" 2>/dev/null
exit 0
