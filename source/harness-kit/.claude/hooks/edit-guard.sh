#!/usr/bin/env bash
# edit-guard.sh — PreToolUse:Edit — 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁
# Role: 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁

source "$(dirname "$0")/harness_config.sh"
hc_enabled "edit_guard" || exit 0
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
READ_LOG="$STATE_DIR/read-tracker.txt"

# 无人值守模式: 跳过 Read-before-Edit 门禁（exit 0 + additionalContext）
UNATTENDED_FILE="$STATE_DIR/.unattended-mode"
if [ -f "$UNATTENDED_FILE" ]; then
    printf '{"continue":true,"hookSpecificOutput":{"additionalContext":"⚠️ 无人值守模式: 跳过 Read-before-Edit 检查"}}\n'
    exit 0
fi

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

# 无路径 → 放行（fail-open）
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# 仅检查配置的源代码文件扩展名
# R18 修复：case 的 * glob 不跨 /，先 basename 再匹配
# R24-S3 修复：set -f 禁用 pathname expansion，避免 cwd 有 main.go 时 $SOURCE_EXT 被展开为具体文件名
SOURCE_EXT=$(hc_get "project.source_extensions" "*.go")
_BASE=$(basename "$FILE_PATH")
_MATCH=false
set -f
for ext in $SOURCE_EXT; do
    # shellcheck disable=SC2254  # glob ${ext} is intentional (matches "*.go" as pattern)
    case "$_BASE" in
        ${ext}) _MATCH=true; break ;;
    esac
done
set +f
[ "$_MATCH" = false ] && exit 0

# 规范化路径
REAL_PATH=$(realpath "$FILE_PATH" 2>/dev/null)
if [ -z "$REAL_PATH" ]; then
    REAL_PATH="$FILE_PATH"
fi

# Fail-closed: 状态文件不存在 → 阻断（read-tracker 可能未初始化）
if [ ! -f "$READ_LOG" ]; then
    printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "⛔ [Read-before-Edit] 读文件追踪器未初始化，无法验证 Read-before-Edit。请确认 read-tracker hook 已启用。"}}\n'
    exit 2
fi

# 检查是否已读取（精确匹配整行）
if grep -qxF "$REAL_PATH" "$READ_LOG" 2>/dev/null; then
    exit 0
fi

# 阻断：源文件未 Read
cat >&2 <<EOF
[Read-before-Edit] 你正在编辑源代码文件但未先 Read。
文件: $FILE_PATH
宪法依据: 第六条（长对话稳定性）— 修改代码前必须先阅读当前内容
强制流程:
 1. 先 Read "$FILE_PATH"
 2. 再执行 Edit
EOF
exit 2
