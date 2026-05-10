#!/usr/bin/env bash
# read-tracker.sh — PostToolUse:Read — 记录已读文件路径供 edit-guard 检查 Read-before-Edit
# Role: 记录已读文件路径供 edit-guard 检查 Read-before-Edit

source "$(dirname "$0")/harness_config.sh"
hc_enabled "read_tracker" || exit 0
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
READ_LOG="$STATE_DIR/read-tracker.txt"

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

# 轮转：超过配置行数时归档
ROTATION_LINE_COUNT=$(hc_get "read_tracker.rotation_line_count" "500")
ARCHIVE_GENS=$(hc_get "read_tracker.archive_generations" "4")
if [ -f "$READ_LOG" ]; then
    LINE_COUNT=$(wc -l < "$READ_LOG" 2>/dev/null || echo 0)
    if [ "$LINE_COUNT" -gt "$ROTATION_LINE_COUNT" ] 2>/dev/null; then
        i=$ARCHIVE_GENS
        while [ "$i" -ge 1 ]; do
            [ -f "${READ_LOG}.${i}" ] && mv "${READ_LOG}.${i}" "${READ_LOG}.$((i+1))" 2>/dev/null
            i=$((i - 1))
        done
        [ -f "$READ_LOG" ] && mv "$READ_LOG" "${READ_LOG}.1" 2>/dev/null
    fi
fi

# 去重写入（工具调用为顺序执行，竞态风险极低）
if [ -f "$READ_LOG" ] && grep -qxF "$REAL_PATH" "$READ_LOG" 2>/dev/null; then
    exit 0
fi
echo "$REAL_PATH" >> "$READ_LOG" 2>/dev/null
exit 0
