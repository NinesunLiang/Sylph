#!/usr/bin/env bash
# posttool-checkpoint.sh — PostToolUse:TaskUpdate + Stop — 工作流闭环：所有工作流结束时输出结构化 checkpoint
# Role: TaskUpdate(completed) / Stop 时自动生成过程摘要 + 决策记录 + 待处理 + 方向指引
# 覆盖: RPE / TODO / Task-Spec (TaskUpdate) + Goal / Ghost (Stop)
# 哲学 #5(以人为本): 人类拿到清晰的收尾报告，不需要自行推断下一步
# 哲学 #4(验证): 每个结论附带证据来源

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "posttool_checkpoint" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)
EVENT=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('hook_event_name', d.get('event', '')))
except: pass
" 2>/dev/null)

# TaskUpdate 路径: 只处理 completed 状态
if [ "$EVENT" = "PostToolUse" ] || [ -z "$EVENT" ]; then
    STATUS=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('status', ''))
except: pass
" 2>/dev/null)
    [ "$STATUS" = "completed" ] || { echo '{"continue": true}'; exit 0; }
    TRIGGER="TaskUpdate(completed)"
# Stop 路径: Goal/Ghost 模式结束或普通会话结束
elif [ "$EVENT" = "Stop" ]; then
    TRIGGER="Stop"
else
    echo '{"continue": true}'
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 提取任务描述
TASK_DESC=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    desc = d.get('tool_input', {}).get('description', '') or d.get('tool_input', {}).get('subject', '') or ''
    print(desc[:200])
except: pass
" 2>/dev/null)

# 收集状态数据
HANDOFF="$STATE_DIR/session-handoff.md"
TODO="$STATE_DIR/todo-queue.md"
SIGNALS="$STATE_DIR/error-signals.jsonl"
BUDGET="$STATE_DIR/retry-budget.json"

# 最近的决策
RECENT_DECISIONS=""
if [ -f "$HANDOFF" ]; then
    RECENT_DECISIONS=$(grep -E '^\|.*\|.*\|' "$HANDOFF" 2>/dev/null | tail -3 | head -3)
fi

# 待处理项
OPEN_TODOS=""
if [ -f "$TODO" ]; then
    OPEN_TODOS=$(grep -cE '^\[ \]' "$TODO" 2>/dev/null || echo "0")
fi

# 错误统计
ERROR_COUNT=$(wc -l < "$SIGNALS" 2>/dev/null | tr -d ' ' || echo "0")
ERROR_COUNT="${ERROR_COUNT:-0}"

# 重试统计
RETRY_ACTIVE=0
if [ -f "$BUDGET" ]; then
    RETRY_ACTIVE=$(${PYTHON_BIN:-python3} -c "
import json
try:
    d = json.load(open('$BUDGET'))
    sigs = d.get('signatures', {})
    active = sum(1 for v in sigs.values() if v.get('retry_count', 0) >= 3)
    print(active)
except: print(0)
" 2>/dev/null)
fi

# Gate 阻断计数
GATE_BLOCKS=$(grep -c 'oracle_gate.*blocked\|permission_gate.*blocked' "$HOME/.claude/flywheel.log" 2>/dev/null | tail -1 || echo "0")
GATE_BLOCKS="${GATE_BLOCKS:-0}"
# 本次会话 oracle-gate 阻断
ORACLE_BLOCKS=$(grep 'oracle_gate.*blocked' "$HOME/.claude/flywheel.log" 2>/dev/null | wc -l | tr -d ' ')
ORACLE_BLOCKS="${ORACLE_BLOCKS:-0}"

# 未提交文件
UNCOMMITTED=$(git -C "$PROJECT_ROOT" diff --name-only 2>/dev/null | wc -l | tr -d ' ')
UNCOMMITTED="${UNCOMMITTED:-0}"

# 构建 checkpoint
CHECKPOINT=$(cat <<CP
╔══════════════════════════════════════════╗
║  📋 Checkpoint — 工作流收尾              ║
╠══════════════════════════════════════════╣
║  任务: ${TASK_DESC:-未命名任务}
╠══════════════════════════════════════════╣
║  状态: ✅ 完成
║  错误: ${ERROR_COUNT} 条信号 | 重试上限: ${RETRY_ACTIVE} 个签名
║  未提交: ${UNCOMMITTED} 个文件 | 待办: ${OPEN_TODOS} 项
║  Gate阻断: oracle-gate ×${ORACLE_BLOCKS} | 总计 ×${GATE_BLOCKS}
╠══════════════════════════════════════════╣
║  📌 下一步建议:
║  · 有未提交文件 → 确认后 git commit
║  · 有待办项 → /lx-todo 继续处理
║  · 有重试上限 → 检查是否需要人工介入
║  · 全清 → 开启新任务或结束会话
╚══════════════════════════════════════════╝
CP
)

# 人类可见: 输出摘要到 stderr (Stop 事件无 additionalContext，只能走 stderr)
echo "📋 [Checkpoint] ${TASK_DESC:-未命名任务} — ✅ 完成 | 未提交:${UNCOMMITTED} | 待办:${OPEN_TODOS}" >&2
echo "   📌 下一步: 有未提交→commit | 有待办→/lx-todo | 全清→新任务" >&2

# Stop 事件: 不支持 additionalContext，只输出 continue:true
# PostToolUse 事件: 注入 additionalContext 给 AI
if [ "$EVENT" = "Stop" ]; then
    echo '{"continue": true}'
else
    echo "$CHECKPOINT" | ${PYTHON_BIN:-python3} - <<'PY'
import json, sys
ctx = sys.stdin.read()
ctx = ''.join(c for c in ctx if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': ctx}}, ensure_ascii=False))
PY
fi

flywheel_event "posttool_checkpoint" "generated" "P2" || true
exit 0
