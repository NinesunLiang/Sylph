#!/usr/bin/env bash
# plan-gate.sh — PreToolUse:Edit|Write [默认关闭] — 编辑前检查是否跳过规划阶段
# Role: 编辑前检查是否跳过规划阶段

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
if [ -z "$LATEST_EXEC" ]; then
    printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "⛔ [Plan Gate] 未找到 executor.md。lx-rpe: Research → Plan → Execute，缺少执行计划。"}}\n'
    exit 2
fi

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

# ─── Gate-R: Research 未完成 → 硬拦截 ──────────────────────────────
if [ "$BASENAME" = "$PLAN_DOC" ]; then
    if ! check_research_gate "$FIRST_INCOMPLETE" "$LATEST_EXEC"; then
        printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "⛔ [Gate-R 硬拦截] Step %s research 未完成，禁止编辑 plan.md。lx-rpe: Research → Plan → Execute"}}\n' \
            "$FIRST_INCOMPLETE"
        exit 2
    fi
fi

# ─── Gate-P: Plan 未完成 → 硬拦截 ──────────────────────────────
if [ "$BASENAME" = "$EXEC_DOC" ]; then
    if ! check_plan_gate "$FIRST_INCOMPLETE" "$LATEST_EXEC"; then
        printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "⛔ [Gate-P 硬拦截] Step %s plan 未完成，禁止执行。lx-rpe: Research → Plan → Execute"}}\n' \
            "$FIRST_INCOMPLETE"
        exit 2
    fi
fi

# ─── 所有步骤已完成 → 放行 ──────────────────────────────
exit 0
