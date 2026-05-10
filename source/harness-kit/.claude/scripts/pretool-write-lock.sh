#!/usr/bin/env bash
# pretool-write-lock.sh — PreToolUse:Edit|Write — 写操作前获取 OMA 并发锁，防止多终端冲突
# Role: 写操作前获取 OMA 并发锁，防止多终端冲突

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

# 仅拦截直接写文件的工具
if [[ "$TOOL_NAME" != "edit" && "$TOOL_NAME" != "write" && "$TOOL_NAME" != "replace" && "$TOOL_NAME" != "str_replace" ]]; then
    exit 0
fi

# 提取文件路径 (支持 filePath 或 file_path)
FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"filePath"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [[ -z "$FILE_PATH" ]]; then
    FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | cut -d'"' -f4)
fi

if [[ -z "$FILE_PATH" ]]; then
    # 提取不到路径，放行
    exit 0
fi

# 尝试识别所属的 RPE Feature 终端 (基于当前工作目录是否在 rpe/feat-X 下)
CURRENT_DIR=$(pwd)
if [[ "$CURRENT_DIR" == *"/rpe/"* ]]; then
    # 提取 rpe/ 后面的目录名作为 owner
    OWNER=$(echo "$CURRENT_DIR" | sed 's|.*/rpe/||' | cut -d'/' -f1)
else
    OWNER="claude-term-$$"
fi

# 调用锁管理器 (阻塞式等待)
python3 .claude/scripts/oma_lock_manager.py acquire "$FILE_PATH" "$OWNER"
exit_code=$?
if [[ $exit_code -ne 0 ]]; then
    echo "🚫 [Carror OS] 并发锁引擎异常 (Exit $exit_code)。"
    exit 2
fi

# 成功抢到锁，由于标准输出被 Claude Code 捕获，此处静默退出
exit 0
