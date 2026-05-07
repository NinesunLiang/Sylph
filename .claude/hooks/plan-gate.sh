#!/usr/bin/env bash

# harness-kit:managed v2.1.0

# plan-gate.sh — PreToolUse:Edit Hook [DISABLED: harness.yaml 默认关闭]
# 注意：此脚本已注册到 settings.json（PreToolUse:Edit|Write），但默认被 harness.yaml plan_gate: false 关闭。
# 恢复激活请：harness.yaml hooks_enabled.plan_gate=true

# 功能：当编辑 plan.md/executor.md 时，注入 Gate 提醒（软阻断，给 AI 判断空间）

#

# 触发时机说明（v6.0.0 重新设计）：

# - plan-gate 不再自动检测 rpe/ 目录，不再自动启用

# - 正确的触发路径：用户 → /lx-rpe skill → skill 内部 Gate-R/P/X/E

# - plan-gate.sh 的职责：当 plan_gate: true 时，提供 hook 层的 Gate 提醒（辅助）

# - plan_gate: false（默认）→ exit 0，不干预任何任务模式（rpe/todo 均不受影响）

#

# 设计原则：

# - lx-rpe skill 已有完整 Gate-R/P/X/E 四阶段门禁（AI 层软约束）

# - plan-gate.sh 是 hook 层辅助提醒，不替代 skill 层逻辑

# - 软阻断 = 注入提醒 + AI 可判断是否继续，而非 exit 2 硬阻断

# - 小任务（lx-todo 路径）完全不受此 hook 影响


source "$(dirname "$0")/harness_config.sh"
# plan_gate: false（默认）→ 直接放行，不影响 rpe 和 todo 任何工作流
hc_enabled "plan_gate" || exit 0

# ─── 以下仅在 plan_gate: true 时执行 ────────────────────────────
INPUT=$(cat)

# 提取 file_path
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

[ -z "$FILE_PATH" ] && exit 0
BASENAME=$(basename "$FILE_PATH")
EXEC_DOC=$(hc_get "workflow.executor_doc" "executor.md")
PLAN_DOC=$(hc_get "workflow.plan_doc" "plan.md")
DOC_ROOT=$(hc_get "workflow.doc_root" "rpe")

# 仅对 rpe/ 目录下的 plan.md / executor.md 生效
case "$BASENAME" in
    "$PLAN_DOC"|"$EXEC_DOC") ;;
    *) exit 0 ;;
esac

# 确认文件路径在 rpe/ 目录下（不影响其他 plan.md）
if ! echo "$FILE_PATH" | grep -q "$DOC_ROOT/"; then
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LATEST_EXEC=$(find "$PROJECT_ROOT/$DOC_ROOT" -name "$EXEC_DOC" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
[ -z "$LATEST_EXEC" ] && exit 0
FEATURE=$(echo "$LATEST_EXEC" | sed "s|.*/${DOC_ROOT}/||;s|/${EXEC_DOC}||")

get_incomplete_steps() {
    local exec_file="$1"
    grep -oE 'Step [0-9]+' "$exec_file" 2>/dev/null | sort -u | while read -r step; do
        step_num=$(echo "$step" | grep -oE '[0-9]+')
        if ! grep -qE "Step $step_num.*✅|Step $step_num.*\[x\]" "$exec_file" 2>/dev/null; then
            echo "$step_num"
        fi
    done
}
check_research_gate() {
    grep -qE "Step $1.*research.*✅|research.*✅.*Step $1" "$2" 2>/dev/null
}
check_plan_gate() {
    grep -qE "Step $1.*plan.*✅|plan.*✅.*Step $1" "$2" 2>/dev/null
}

INCOMPLETE_STEPS=$(get_incomplete_steps "$LATEST_EXEC")
FIRST_INCOMPLETE=$(echo "$INCOMPLETE_STEPS" | head -1)
[ -z "$FIRST_INCOMPLETE" ] && exit 0

# ─── 软阻断：注入提醒而非 exit 2 ──────────────────────────────
# AI 读到提醒后可自行判断：继续（说明已确认）或回到正确流程
if [ "$BASENAME" = "$PLAN_DOC" ]; then
    if ! check_research_gate "$FIRST_INCOMPLETE" "$LATEST_EXEC"; then
        printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "⚠️ [Gate-R 提醒] 正在编辑 %s 的 plan.md，但 Step %s 的 research 尚未标记完成。lx-rpe 正确流程：Research → Plan → Execute。如已完成 research 只是未标记，请先在 executor.md 标记 research ✅ 再继续；或说明原因后继续编辑。"}}\n' \
            "$FEATURE" "$FIRST_INCOMPLETE"
        exit 0
    fi
fi

if [ "$BASENAME" = "$EXEC_DOC" ]; then
    if ! check_plan_gate "$FIRST_INCOMPLETE" "$LATEST_EXEC"; then
        printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "⚠️ [Gate-P 提醒] 正在推进 Step %s 但 plan 尚未标记完成。lx-rpe 正确流程：Plan 门禁通过后才可执行。如 plan 已完成只是未标记，请先在 executor.md 标记 plan ✅；或说明原因后继续。"}}\n' \
            "$FIRST_INCOMPLETE"
        exit 0
    fi
fi

exit 0
