#!/usr/bin/env bash

# write-lock-release.sh (PostToolUse) - Carror OS 一人成军释放锁


TOOL_NAME="$1"
if [[ "$TOOL_NAME" != "
edit" && "$TOOL_NAME" != "
write" && "$TOOL_NAME" != "
replace" && "$TOOL_NAME" != "
str_replace" ]]; then exit 0
fi
# 从 stdin 读取包含请求参数的
JSONTOOL_INPUT=$(cat)
FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"
filePath"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [[ -z "$FILE_PATH" ]]; then FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"
file_path"\s*:\s*"[^"]*"' | cut -d'"' -f4)
fi
if [[ -n "$FILE_PATH" ]]; then python3 .claude/scripts/oma_lock_manager.py release "$FILE_PATH"
fi
exit 0
