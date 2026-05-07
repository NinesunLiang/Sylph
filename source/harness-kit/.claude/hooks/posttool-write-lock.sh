#!/usr/bin/env bash

# write-lock-release.sh (PostToolUse) — Carror OS OMA 并发锁释放
# 集成 harness_config.sh，支持通过 harness.yaml 启用/禁用

# Source harness config for feature toggle support
HARNESS_CONFIG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/harness_config.sh"
if [ -f "$HARNESS_CONFIG" ]; then
    # shellcheck source=harness_config.sh
    . "$HARNESS_CONFIG" 2>/dev/null
    if ! hc_enabled "oma_lock" 2>/dev/null; then
        exit 0
    fi
fi

TOOL_INPUT=$(cat)

# 从 stdin JSON 读 tool_name（兼容 settings.json 无位置参数场景）
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$TOOL_INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null)
else
    TOOL_NAME=$(echo "$TOOL_INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    [ -z "$TOOL_NAME" ] && TOOL_NAME=$(echo "$TOOL_INPUT" | grep -o '"tool"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
fi
[ -z "$TOOL_NAME" ] && TOOL_NAME="$1"
TOOL_NAME=$(echo "$TOOL_NAME" | tr '[:upper:]' '[:lower:]')

if [[ "$TOOL_NAME" != "edit" && "$TOOL_NAME" != "write" && "$TOOL_NAME" != "replace" && "$TOOL_NAME" != "str_replace" ]]; then
    exit 0
fi

FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"filePath"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [[ -z "$FILE_PATH" ]]; then
    FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | cut -d'"' -f4)
fi

if [[ -n "$FILE_PATH" ]]; then
    python3 .claude/scripts/oma_lock_manager.py release "$FILE_PATH" 2>/dev/null
fi
exit 0
