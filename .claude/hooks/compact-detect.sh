#!/usr/bin/env bash
# compact-detect.sh — UserPromptSubmit Hook
#
# 检测用户输入是否为 /compact，保存 compact 前 usage 供 token_writer 处理
# 流程：
#   UserPromptSubmit (此脚本) → token_writer.sh --increment (下一次 PostToolUse)
#
# 依赖：token-tracking-index.json（由 token_writer.sh 维护）
# 输出：.omc/state/token-compact-state.json（写入预 compact 状态）
#
# 不阻塞：任何失败都 exit 0，不干扰用户流程

# 故意不设 set -e: 本 hook 永不阻塞，任何失败静默 exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Config gate: 从 harness.yaml 读取启停开关
source "$SCRIPT_DIR/harness_config.sh" 2>/dev/null || true
hc_enabled "compact_detect" || exit 0

STATE_DIR="$PROJECT_ROOT/.omc/state"
INDEX_FILE="$STATE_DIR/token-tracking-index.json"
COMPACT_STATE="$STATE_DIR/token-compact-state.json"

# 读取 STDIN（UserPromptSubmit 会传入用户输入）
INPUT=$(cat 2>/dev/null || echo "")

# 清理输入（移除 ANSI 码、首尾空格）
CLEAN_INPUT=$(echo "$INPUT" | sed 's/\x1b\[[0-9;]*m//g' | tr -d '[:space:]')

# 匹配 /compact 命令（含各种变体：/compact、compact、/compact  等）
case "$CLEAN_INPUT" in
    /compact|compact|/compact*)
        ;;
    *)
        exit 0
        ;;
esac

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# 读取当前 usage
USAGE=0
if [ -f "$INDEX_FILE" ]; then
    USAGE=$(python3 -c "
import json
try:
    d = json.load(open('$INDEX_FILE'))
    print(d.get('usage', 0))
except:
    print('0')
" 2>/dev/null)
fi

# 写入 compact state
cat > "$COMPACT_STATE" <<EOF
{
  "pre_compact_usage": $USAGE,
  "detected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%s)"
}
EOF

# ─── /compact 后知识注入 — 防止 AI 失忆 ──────────────────────
# 注入到 stdout，hook 框架会传递给 AI 作为 additionalContext
INJECT_INDEX="$PROJECT_ROOT/.claude/index.md"
INJECT_KERNEL="$PROJECT_ROOT/.claude/kernel.md"
echo ""
echo "═══════════════════════════════════════════════"
echo " /compact 检测 — 项目知识重新注入"
echo "═══════════════════════════════════════════════"

# 注入 index.md 铁律速查（约 30 行）
if [ -f "$INJECT_INDEX" ]; then
    echo ""
    echo "--- 铁律速查 ---"
    grep -A 20 '^| \#' "$INJECT_INDEX" 2>/dev/null | head -25
    echo ""
    echo "--- 治理规则 ---"
    grep -E '^\|`|^\| 文件' "$INJECT_INDEX" 2>/dev/null | head -10
fi

# 注入 kernel.md 架构铁律（约 15 行）
if [ -f "$INJECT_KERNEL" ]; then
    echo ""
    echo "--- 架构铁律 ---"
    grep -E '^\*\*' "$INJECT_KERNEL" 2>/dev/null | head -10
fi

# 注入 AGENTS.md 治理框架纲要
INJECT_AGENTS="$PROJECT_ROOT/AGENTS.md"
if [ -f "$INJECT_AGENTS" ]; then
    echo ""
    echo "--- 治理框架纲要 ---"
    grep -E '^## |^### ' "$INJECT_AGENTS" 2>/dev/null | head -15
fi

# 注入会话状态恢复
echo ""
echo "--- 当前会话状态 ---"
if [ -f "$PROJECT_ROOT/.omc/state/session-handoff.md" ]; then
    echo "▪ 上次会话交接："
    grep -E '^(#|## )|Feature:|进度:|关键决策|踩坑记录' "$PROJECT_ROOT/.omc/state/session-handoff.md" 2>/dev/null | head -10
fi
if [ -f "$PROJECT_ROOT/.omc/state/todo-queue.md" ]; then
    echo "▪ 当前 Todo："
    head -10 "$PROJECT_ROOT/.omc/state/todo-queue.md" 2>/dev/null
fi

echo ""
echo "═══════════════════════════════════════════════"
echo " 知识已恢复，继续当前任务。"
echo "═══════════════════════════════════════════════"
echo ""

exit 0
