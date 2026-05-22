#!/usr/bin/env bash
# fuzzy-block.sh — PreToolUse — 模糊指令硬阻断（C1 指令清晰度门禁）
# Role: 模糊指令硬阻断 — turn-counter 标记模糊指令后阻断所有工具调用，强制 AI 先澄清

source "$(dirname "$0")/harness_config.sh"
hc_enabled "fuzzy_block" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"
set -f

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FUZZY_MARKER="$PROJECT_ROOT/.omc/state/.fuzzy-block-active"

if [ ! -f "$FUZZY_MARKER" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 读取标记中的警告信息
WARNING_MSG=$(cat "$FUZZY_MARKER" 2>/dev/null || echo "模糊指令")

# 自动/无人值守模式降级为记录
if [ "$(is_mode_active "$PROJECT_ROOT/.omc/state")" != "normal" ]; then
    echo "[fuzzy-block] ${WARNING_MSG}（自主模式，降级为记录不阻断）" >&2
    rm -f "$FUZZY_MARKER"
    echo '{"continue": true}'
    exit 0
fi

# 硬阻断：标记存在 + 非自主模式 → Agentic UI 菜单
FUZZY_MSG_ESCAPED=$(echo "$WARNING_MSG" | head -c 200)
agentic_menu_two \
    "模糊指令阻断" \
    "指令不明确，无法执行具体工具调用。原因: ${FUZZY_MSG_ESCAPED}" \
    "向用户澄清具体目标" "暂停执行，向用户提问明确后再继续" \
    flywheel_event "fuzzy_block" "blocked" "P2" || true
    exit 0
