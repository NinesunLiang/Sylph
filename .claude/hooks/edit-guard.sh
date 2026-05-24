#!/usr/bin/env bash
# edit-guard.sh — PreToolUse:Edit — 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁
# Role: 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁

source "$(dirname "$0")/harness_config.sh"
hc_enabled "edit_guard" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
READ_LOG="$STATE_DIR/read-tracker.txt"

# 统一模式检测: ghost/unattended 模式下跳过 Read-before-Edit 门禁
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" != "normal" ]; then
    printf '⚠️ %s模式: 跳过 Read-before-Edit 检查' "$MODE" | hc_emit_hook_json "PreToolUse" "true"
    exit 0
fi

# 提取 file_path 字段
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('args', {}).get('filePath', data.get('tool_input', {}).get('file_path', '')))
except:
    pass" 2>/dev/null)
fi

# 无路径 → 放行（fail-open）
if [ -z "$FILE_PATH" ]; then
    echo '{"continue": true}'
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
[ "$_MATCH" = false ] && { echo '{"continue": true}'; exit 0; }

# 规范化路径
REAL_PATH=$(realpath "$FILE_PATH" 2>/dev/null || echo "$FILE_PATH")

# Fail-open: 状态文件不存在 → 放行（read-tracker 可能未工作）
if [ ! -f "$READ_LOG" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 检查是否已读取（精确匹配整行）
if grep -qxF "$REAL_PATH" "$READ_LOG" 2>/dev/null; then
    echo '{"continue": true}'
    exit 0
fi

# 阻断：源文件未 Read — Agentic UI 菜单
if [ "$MODE" != "normal" ]; then
    echo "[edit-guard] 自主模式: 跳过 Read-before-Edit 检查" >&2
    echo '{"continue": true}'
    exit 0
fi
flywheel_event "edit_guard" "blocked" "P2" || true
agentic_menu \
    "Read-before-Edit" \
    "文件: ${FILE_PATH} — 宪法第六条: 修改代码前必须先阅读当前内容" \
    "先 Read 再编辑" "Read ${FILE_PATH} 后再进行编辑操作" \
    "强制编辑" "跳过 Read 检查，直接编辑"
