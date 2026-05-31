#!/usr/bin/env bash
# pretool-plan-gate.sh — PreToolUse:Edit|Write|Bash — Plan-before-Execute 门禁
# 哲学 #3(先守护): 方案未审批→阻断执行
# 哲学 #6(0信任): 不信任 state.json (AI可写) → 从 lx-goal.json 验证 phase0_passed_at
# 触发: 跨3+文件或20+行变更时检查

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f
hc_enabled "pretool_plan_gate" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat 2>/dev/null || echo "")
TOOL_NAME=""
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
fi
[ -z "$TOOL_NAME" ] && { echo '{"continue": true}'; exit 0; }

# 只拦截 Edit/Write/Bash (会产生代码变更的工具)
[[ "$TOOL_NAME" =~ ^(Edit|Write|Bash)$ ]] || { echo '{"continue": true}'; exit 0; }

# ─── 快速估算变更规模 ───
ESTIMATED_FILES=0
ESTIMATED_LINES=0

if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
    if [ -n "$FILE_PATH" ]; then
        NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // empty' 2>/dev/null)
        if [ -n "$NEW_CONTENT" ]; then
            ESTIMATED_LINES=$(echo "$NEW_CONTENT" | wc -l | tr -d ' ')
        fi
        ESTIMATED_FILES=1
    fi
elif [ "$TOOL_NAME" = "Bash" ]; then
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
    FILE_COUNT=$(echo "$CMD" | grep -oE '[^ ]+\.(go|py|ts|js|sh|yaml|yml|json|md|toml|rs|rb|java|css|html)' 2>/dev/null | wc -l | tr -d ' ')
    ESTIMATED_FILES="${FILE_COUNT:-0}"
fi

# ─── RPE 计划目录放行: 允许写入 prd.md/progress.md/checklist.md ───
# 只放行这三种文件，state.json 不在白名单 (防止直接写 phase=executing 绕过 phase0-done)
if echo "$FILE_PATH" | grep -qE '\.omc/plans/.*/(prd|progress|checklist)\.md$' 2>/dev/null; then
    echo '{"continue": true}'; exit 0
fi
# Ghost RPE 目录同样放行
if echo "$FILE_PATH" | grep -qE '\.omc/chats/.*/progress\.md$' 2>/dev/null; then
    echo '{"continue": true}'; exit 0
fi

# ─── 非实质性Bash操作放行: 纯重命名/目录创建/信息查询 ───
# 只改文件名/路径不改内容的操作不应被拦截
if [ "$TOOL_NAME" = "Bash" ]; then
    # 检查是否只是非实质性操作 (git mv, mv, mkdir, ls, find, cp)
    # 排除内联编辑操作 (sed -i, awk -i, tee, > 重定向, cat > 等)
    if echo "$CMD" | grep -qE '^\s*(git\s+mv|mv\s+)\s' 2>/dev/null && \
       ! echo "$CMD" | grep -qE '\bsed\s+-i\b|\bawk\s+.*-i\b|\btee\b|[^>]>>?\s*\S|cat\s+>' 2>/dev/null; then
        echo '{"continue": true}'
        flywheel_event "pretool_plan_gate" "non_substantive_bypass" "P2" "cmd=git_mv" || true
        exit 0
    fi
    if echo "$CMD" | grep -qE '^\s*(mkdir|ls|find|cp|rmdir)\s' 2>/dev/null; then
        echo '{"continue": true}'
        flywheel_event "pretool_plan_gate" "non_substantive_bypass" "P2" "cmd=filesystem_ops" || true
        exit 0
    fi
fi

# ─── 门禁判断 ───
# DG-114: 增加会话级累计编辑检测，防止分步绕过
CUMULATIVE_FILES=0
CHURN_LOG="$PROJECT_ROOT/.omc/state/edit-churn-log.jsonl"
if [ -f "$CHURN_LOG" ]; then
    SESSION_START=$(${PYTHON_BIN:-python3} -c "
import json,os,time
sf='$PROJECT_ROOT/.omc/state/session-start.txt'
if os.path.exists(sf):
    try:
        with open(sf) as f: ts=int(f.read().strip()); print(ts)
    except: print(0)
else: print(0)" 2>/dev/null || echo "0")
    if [ "$SESSION_START" -gt 0 ] 2>/dev/null; then
        CUMULATIVE_FILES=$(${PYTHON_BIN:-python3} -c "
import json,os
count=set()
ss=$SESSION_START
lf='$CHURN_LOG'
if os.path.exists(lf):
    try:
        with open(lf) as f:
            for line in f:
                try:
                    r=json.loads(line.strip())
                    if r.get('ts',0) >= ss:
                        count.add(r.get('file',''))
                except: pass
    except: pass
print(len(count))" 2>/dev/null || echo "0")
    fi
fi
TOTAL_FILES=$((ESTIMATED_FILES + CUMULATIVE_FILES))

# Bash操作无法估算行数→只看文件数。Edit/Write→看文件数或行数
if [ "$TOOL_NAME" = "Bash" ]; then
    if [ "$ESTIMATED_FILES" -lt 2 ] && [ "$TOTAL_FILES" -lt 3 ]; then
        echo '{"continue": true}'; exit 0
    fi
else
    # Edit/Write: 可以估算行数 → 单次文件数或累计文件数或行数任一超标即阻断
    if [ "$ESTIMATED_FILES" -lt 2 ] && [ "$TOTAL_FILES" -lt 3 ] && [ "$ESTIMATED_LINES" -lt 15 ]; then
        echo '{"continue": true}'; exit 0
    fi
fi

# ─── 自主模式感知 ──────────────────────────────────────────
STATE_DIR="$PROJECT_ROOT/.omc/state"
MODE=$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")

# Ghost 模式: 探索驱动，允许代码变更 (permission-gate + pre-ask-guard 提供安全网)
if [ "$MODE" = "ghost" ]; then
    echo '{"continue": true}'
    flywheel_event "pretool_plan_gate" "ghost_mode_allow" "P2" "files=$ESTIMATED_FILES lines=$ESTIMATED_LINES" || true
    exit 0
fi

# Goal 模式: 必须通过 phase0-done 验证 (检查 lx-goal.json 而非 state.json)
# 哲学 #6 (0信任): state.json 是 AI 可写的，不可信。lx-goal.json 的 phase0_passed_at 只有 phase0-done 写入
if [ "$MODE" = "goal" ]; then
    GOAL_FILE="$STATE_DIR/tokens/lx-goal.json"
    if [ -f "$GOAL_FILE" ]; then
        PHASE0_PASSED=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$GOAL_FILE', encoding='utf-8')); print(d.get('phase0_passed_at',''))" 2>/dev/null || echo "")
        if [ -n "$PHASE0_PASSED" ]; then
            echo '{"continue": true}'
            flywheel_event "pretool_plan_gate" "goal_phase0_verified" "P2" "passed_at=$PHASE0_PASSED" || true
            exit 0
        fi
    fi
    # Phase 0 未完成 → 阻断
    echo "⛔ [Plan Gate] 目标模式活跃，但 Phase 0 未完成 (phase0_passed_at 缺失)。

    AI 必须先调用 phase0-done 完成计划阶段:
      lx-goal phase0-done

    这会验证 prd.md 已写入子任务/验收标准/风险点，
    然后将 phase0_passed_at 写入 lx-goal.json，解锁代码变更。
    注意: 直接写 state.json 无效 — plan gate 只信任 lx-goal.json。
    " >&2
    flywheel_event "pretool_plan_gate" "blocked_phase0_incomplete" "P1" "mode=goal" || true
    exit 2
fi

# ─── Normal 模式: 传统 Plan-before-Execute 检查 ──────────
PLANS_DIR="$PROJECT_ROOT/.omc/plans"
HAS_APPROVED=false
PLAN_PATH=""

if [ -d "$PLANS_DIR" ]; then
    set +f
    for state_file in "$PLANS_DIR"/*/*/state.json; do
        set -f
        [ -f "$state_file" ] || continue
        PHASE=$(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('$state_file', encoding='utf-8')).get('phase',''))" 2>/dev/null || echo "")
        if [ "$PHASE" = "approved" ] || [ "$PHASE" = "executing" ]; then
            HAS_APPROVED=true
            PLAN_PATH=$(dirname "$state_file")
            break
        fi
    done
fi

if [ "$HAS_APPROVED" = true ]; then
    echo '{"continue": true}'
    flywheel_event "pretool_plan_gate" "approved_plan_active" "P2" "plan=$PLAN_PATH" || true
    exit 0
fi

# ─── 概念审查后门禁: Oracle/Meta-Oracle 近期 APPROVED → 必须有实现方案 ───
# 防止「概念 APPROVED → 跳过实现方案审核 → 直接改代码」(DG-114)
ORACLE_VERDICT="$STATE_DIR/oracle-verdicts.md"
META_VERDICT="$STATE_DIR/meta-oracle-verdicts.md"
CONCEPT_RECENT=false
for _vf in "$ORACLE_VERDICT" "$META_VERDICT"; do
    if [ -f "$_vf" ]; then
        _AGE=$(${PYTHON_BIN:-python3} -c "import os,time; print(int(time.time()-os.path.getmtime('$_vf')))" 2>/dev/null || echo 999)
        # tail -1: 只检查最新条目，避免追加日志中旧 APPROVED 条目造成误报 (Meta-Oracle ADVISORY)
        if [ "$_AGE" -lt 600 ] && tail -1 "$_vf" 2>/dev/null | grep -qiE "approved|accept"; then
            CONCEPT_RECENT=true; break
        fi
    fi
done
if [ "$CONCEPT_RECENT" = true ]; then
    echo "⛔ [Plan Gate] 检测到近期概念审查已通过 (Oracle/Meta-Oracle APPROVED)，但缺少实现方案。

    AI 必须先:
    1. 输出具体的实现方案 (改动文件/行数/逻辑)
    2. 等用户审批后才能执行代码变更

    概念审查通过 ≠ 可以直接改代码。方案→双审→执行，不可跳过。
    " >&2
    flywheel_event "pretool_plan_gate" "blocked_concept_without_impl_plan" "P1" "tool=$TOOL_NAME" || true
    exit 2
fi

# ─── 阻断: 无已审批方案 ───
echo "⛔ [Plan Gate] 检测到中等以上变更 (本次${ESTIMATED_FILES}文件/${ESTIMATED_LINES}行, 本会话累计${CUMULATIVE_FILES}文件)，但无已审批方案。

AI 必须:
1. 先写 PRD 到 .omc/plans/{date}/{feature_slug}/prd.md
2. 输出方案摘要给用户
3. 等用户说 '同意'/'do' 后更新 state.json phase=approved
4. 才能执行代码变更

当前已有方案目录:
$(set +f; ls "$PLANS_DIR"/*/*/state.json 2>/dev/null | head -5 || echo '  (无)')
" >&2

flywheel_event "pretool_plan_gate" "blocked_no_plan" "P1" "tool=$TOOL_NAME files=$ESTIMATED_FILES lines=$ESTIMATED_LINES" || true
exit 2
