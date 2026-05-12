#!/usr/bin/env bash
# compact-detect.sh — UserPromptSubmit — 检测 /compact 命令，保存 compact 前 usage 供 token 追踪
# Role: 检测 /compact 命令，保存 compact 前 usage 供 token 追踪

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Config gate: 从 harness.yaml 读取启停开关
source "$SCRIPT_DIR/harness_config.sh" 2>/dev/null || true
# 兜底：harness_config.sh 可能不存在，确保 hc_enabled 有定义
if ! command -v hc_enabled &>/dev/null; then
    hc_enabled() { return 0; }
fi
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
    grep -E '^## |^\*\*' "$INJECT_KERNEL" 2>/dev/null | head -10
fi

# 注入 AGENTS.md 治理框架纲要
INJECT_AGENTS="$PROJECT_ROOT/AGENTS.md"
if [ -f "$INJECT_AGENTS" ]; then
    echo ""
    echo "--- 治理框架纲要 ---"
    grep -E '^## |^### ' "$INJECT_AGENTS" 2>/dev/null | head -15
fi

# 注入 skill 关联图谱（C7 关联编排知识密度）
SKILL_GRAPH="$PROJECT_ROOT/.claude/reference/skill-graph.md"
if [ -f "$SKILL_GRAPH" ]; then
    echo ""
    echo "--- Skill 关联图谱 ---"
    grep -E '^\|' "$SKILL_GRAPH" 2>/dev/null | head -20
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

# 注入 session-dump 恢复上下文（E8 双层动态加载 — 第 2 层: compact 后恢复）
SESSION_DUMP="$PROJECT_ROOT/.omc/state/session-dump.json"
if [ -f "$SESSION_DUMP" ]; then
    python3 -c "
import json
try:
    with open('$SESSION_DUMP') as f:
        d = json.load(f)
except:
    exit(0)

parts = []
gs = d.get('git_state', {})
mf = gs.get('modified_files', [])
if mf:
    parts.append('▪ 更改文件（%d个）: %s' % (len(mf), ', '.join(mf[:4])))
    if len(mf) > 4:
        parts.append('  ... 共 %d 个' % len(mf))

af = d.get('active_features', [])
if af:
    names = []
    for a in af:
        if isinstance(a, dict): names.append(str(a.get('name', a.get('feature', ''))))
        else: names.append(str(a))
    parts.append('▪ 活跃特性: %s' % ' | '.join(names[:3]))

el = d.get('edit_log', [])
if el:
    parts.append('▪ 编辑文件: %d 个' % len(el))

if parts:
    for p in parts:
        print(p)
" 2>/dev/null || true
fi

echo ""
echo "═══════════════════════════════════════════════"
echo " 知识已恢复，继续当前任务。"
echo "═══════════════════════════════════════════════"
echo ""

exit 0
