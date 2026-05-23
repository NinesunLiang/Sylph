#!/usr/bin/env bash
# pretool-plan-gate.sh — PreToolUse:Edit|Write|Bash — Plan-before-Execute 门禁
# 哲学 #3(先守护): 方案未审批→阻断执行
# 哲学 #6(0信任): AI不得自行决定"不需要计划"
# 触发: 跨3+文件或20+行变更时, 检查 .omc/plans/ 下是否有已审批方案

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

# 从 tool_input 中提取 file_path (Edit/Write) 或分析 Bash 命令
if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
    if [ -n "$FILE_PATH" ]; then
        # 新文件? 估算行数
        NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // empty' 2>/dev/null)
        if [ -n "$NEW_CONTENT" ]; then
            ESTIMATED_LINES=$(echo "$NEW_CONTENT" | wc -l | tr -d ' ')
        fi
        ESTIMATED_FILES=1
    fi
elif [ "$TOOL_NAME" = "Bash" ]; then
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
    # 检测多文件操作
    FILE_COUNT=$(echo "$CMD" | grep -oE '[^ ]+\.(go|py|ts|js|sh|yaml|yml|json|md|toml)' 2>/dev/null | wc -l | tr -d ' ')
    ESTIMATED_FILES="${FILE_COUNT:-0}"
fi

# ─── 门禁判断 ───
if [ "$ESTIMATED_FILES" -lt 3 ] && [ "$ESTIMATED_LINES" -lt 20 ]; then
    # 小变更, 放行
    echo '{"continue": true}'; exit 0
fi

# ─── 大变更: 检查是否有已审批方案 ───
PLANS_DIR="$PROJECT_ROOT/.omc/plans"
HAS_APPROVED=false
PLAN_PATH=""

if [ -d "$PLANS_DIR" ]; then
    set +f  # 临时启用glob (set -f在第10行禁用了通配符展开)
    for state_file in "$PLANS_DIR"/*/*/state.json; do
        set -f
        [ -f "$state_file" ] || continue
        PHASE=$(python3 -c "import json; print(json.load(open('$state_file')).get('phase',''))" 2>/dev/null || echo "")
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

# ─── 阻断: 无已审批方案 ───
echo "⛔ [Plan Gate] 检测到中等以上变更 (${ESTIMATED_FILES}文件/${ESTIMATED_LINES}行)，但无已审批方案。

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
