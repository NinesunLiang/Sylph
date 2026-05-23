#!/usr/bin/env bash
# lx-goal.sh — 目标模式（目标驱动自主执行）
# 用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|retry
# 目标模式: 给 AI 一个具体目标，AI 持续执行直到完成或过期，不干扰人，默认 6h 过期
# 与 lx-ghost 的区别: goal = 目标驱动（具体任务），ghost = 方向驱动（开源探索）
# 向后兼容: 旧 unattended-mode.json / .unattended-mode 文件标记仍可被 is_mode_active() 检测
#
# 哲学映射:
#   #3 先守护: gate 降级为 warn-only 而非硬阻断
#   #4 没验证=没做: task-done 逐项确认 + report 完整输出
#   #6 0信任: 危险操作记录 skipped_risks 而不是跳过
#   #7 文档优先: 完成时自动生成报告文档

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

# source harness_config for hc_get defaults
source "$SCRIPT_DIR/../../../hooks/harness_config.sh"

# Sanitize output to prevent JSON encoding errors from surrogate pairs and control characters
sanitize_output() {
    local input="$1"
    echo "$input" | LC_ALL=C sed 's/[\x00-\x1F\x7F]//g' | python3 -c '
import sys
text = sys.stdin.read()
# Strip surrogate characters (U+D800..U+DFFF) — must use ord() range check, not raw string \u escapes
text = ''.join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))
print(text, end="")
'
}

MODE_FILE="$STATE_DIR/lx-goal.json"

# 智能参数检测：第一个参数不是已知子命令 → 当作目标描述自动激活
_KNOWN_SUBCOMMANDS="on|off|status|set|report|poll|task-done|skip-risk|hard-boundary-hit|blocked-human|retry"
if [ -n "${1:-}" ] && ! echo "$1" | grep -Eq "^($_KNOWN_SUBCOMMANDS)$"; then
    exec bash "$0" on "$@"
fi

case "${1:-status}" in
    on)
        GOAL="${2:-目标任务未指定}"
        EXPIRY_HOURS="${3:-$(hc_get "goal_mode.default_expiry_hours" "6")}"
        # DG-007 安全修复: 用 json.dumps 序列化而非 heredoc 裸拼接
        # 避免 goal 中的换行/引号/特殊字符破坏 JSON 结构
        export _LX_GOAL="$GOAL"
        export _LX_EXPIRY_HOURS="$EXPIRY_HOURS"
        export _LX_MODE_FILE="$MODE_FILE"
        python3 <<'PYEOF'
import json, os
from datetime import datetime, timedelta, timezone

goal = os.environ['_LX_GOAL']
expiry_hours = int(os.environ['_LX_EXPIRY_HOURS'])
mode_file = os.environ['_LX_MODE_FILE']
expires = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()

data = {
    "active": True,
    "mode": "goal",
    "goal": goal,
    "expires_at": expires,
    "activated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    "retry_count": 0,
    "skipped_risks": [],
    "completed_tasks": [],
    "hard_boundary_hits": [],
    "blocked_human": []
}

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
        # 清理旧格式
        rm -f "$STATE_DIR/unattended-mode.json" "$STATE_DIR/.unattended-mode" 2>/dev/null
        # 创建 autonomous.active 信号供 completion-gate 等降级
        touch "$STATE_DIR/autonomous.active"
        DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$GOAL" | tr " " "-" | tr -cd "[:alnum:]-_" | head -c 50)
PLAN_DIR="$PROJECT_ROOT/.omc/plans/${DATE}/${SLUG}"
mkdir -p "$PLAN_DIR"
echo "{"phase":"draft","created_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}" > "$PLAN_DIR/state.json"
echo "# $GOAL

> goal模式自动创建 @ $(date)" > "$PLAN_DIR/prd.md"
echo "# Progress

" > "$PLAN_DIR/progress.md"
echo "# Checklist

" > "$PLAN_DIR/checklist.md"
log_info "RPE文档层: $PLAN_DIR"
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$GOAL" | tr " " "-" | tr -cd "[:alnum:]-_" | head -c 50)
PLAN_DIR="$PROJECT_ROOT/.omc/plans/${DATE}/${SLUG}"
mkdir -p "$PLAN_DIR"
python3 -c "import json; json.dump({'phase':'draft','created_at':'$(date -u +%Y-%m-%dT%H:%M:%SZ)'},open('$PLAN_DIR/state.json','w'))"
echo "# $GOAL

> goal模式自动创建 @ $(date)" > "$PLAN_DIR/prd.md"
echo "# Progress

" > "$PLAN_DIR/progress.md"
echo "# Checklist

" > "$PLAN_DIR/checklist.md"
echo "RPE文档层: $PLAN_DIR" >&2
echo "✅ 目标模式已开启 — 目标: $(sanitize_output "$GOAL"), ${EXPIRY_HOURS}h 过期"
        echo "   autonomous.active 信号已创建，evidence/completion gate 降级为 warn-only"
        echo "   任务逐项标记: lx-goal task-done \"完成项描述\""
        echo "   完成后输出报告: lx-goal report"
        echo ""
        # Scope-from-Goal: 自动推导文件范围，注入 pretool-edit-scope 的 current-scope.txt
        # 意志延伸的物理物化 — 目标激活时自动限定编辑范围（Meta-Oracle scope-from-goal 方案）
        bash "$PROJECT_ROOT/.claude/scripts/auto-scope.sh" 2>/dev/null || true

        # 将决策链注入 AI 上下文（Oracle M1: 确保模式激活时 AI 立即看到决策链）
        DECISION_CHAIN="$PROJECT_ROOT/.claude/reference/autonomous-decision-chain.md"
        if [ -f "$DECISION_CHAIN" ]; then
            echo "[.claude/reference/autonomous-decision-chain.md]"
            cat "$DECISION_CHAIN"
            echo ""
        fi
        ;;

    off)
        if [ -f "$MODE_FILE" ]; then
            rm -f "$MODE_FILE"
        fi
        # 清理旧格式
        rm -f "$STATE_DIR/unattended-mode.json" "$STATE_DIR/.unattended-mode" 2>/dev/null
        rm -f "$STATE_DIR/autonomous.active" 2>/dev/null
        echo "✅ 目标模式已关闭，所有 hook 恢复正常阻断"
        ;;

    status)
        if [ -f "$MODE_FILE" ]; then
            GOAL=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('goal','?'))" 2>/dev/null)
            EXP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','无'))" 2>/dev/null)
            DONE=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('completed_tasks',[])))" 2>/dev/null)
            SKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
            HARD=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
            RETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
            echo "📋 目标模式 (lx-goal): 🟢 开启中"
            echo "   目标: $(sanitize_output "$GOAL")"
            echo "   过期: $EXP"
            BLOCKED=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('blocked_human',[])))" 2>/dev/null)
            echo "   已完成: $DONE  跳过风险: $SKIP  硬边界: $HARD  推迟决策: $BLOCKED  重试: $RETRY"
        elif [ -f "$STATE_DIR/unattended-mode.json" ]; then
            echo "📋 目标模式 (旧格式 unattended-mode.json): 🟡 兼容中"
            echo "   建议执行 lx-goal off && lx-goal on \"目标\" 迁移到新格式"
        elif [ -f "$STATE_DIR/.unattended-mode" ]; then
            echo "📋 目标模式 (旧格式 .unattended-mode): 🟡 兼容中"
        else
            echo "📋 目标模式 (lx-goal): ⚪ 已关闭"
        fi
        ;;

    set)
        KEY="$2"
        VALUE="$3"
        if [ ! -f "$MODE_FILE" ]; then
            # 回退旧格式
            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
                echo "⚠️ 使用旧格式 unattended-mode.json，建议迁移到 lx-goal.json"
                MODE_FILE="$STATE_DIR/unattended-mode.json"
            else
                echo "❌ 目标模式未开启，无法修改"
                exit 1
            fi
        fi
        python3 -c "
import json, os
file = '$MODE_FILE'
d = json.load(open(file))
d['$KEY'] = $VALUE
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null && echo "✅ 目标模式 $KEY 已更新为 $VALUE" || echo "❌ 更新失败"
        ;;

    report)
        # 支持新旧格式
        REPORT_FILE="$STATE_DIR/goal-report.md"
        if [ ! -f "$MODE_FILE" ]; then
            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
                MODE_FILE="$STATE_DIR/unattended-mode.json"
                REPORT_FILE="$STATE_DIR/goal-report.md"
            else
                echo "⚠️ 目标模式未开启，无报告可输出"
                exit 1
            fi
        fi
        GOAL=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('goal','?'))" 2>/dev/null)
        DONE=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('completed_tasks',[])))" 2>/dev/null)
        SKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
        HARD=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
        RETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
        BLOCKED=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('blocked_human',[])))" 2>/dev/null)
        SKIP_LIST=$(python3 -c "
import json
d = json.load(open('$MODE_FILE'))
risks = d.get('skipped_risks', [])
for r in risks:
    desc = r.get('description', r) if isinstance(r, dict) else r
    print(f'- {desc}')
" 2>/dev/null)
        HARD_LIST=$(python3 -c "
import json
d = json.load(open('$MODE_FILE'))
hits = d.get('hard_boundary_hits', [])
for h in hits:
    desc = h.get('description', '?')
    reason = h.get('reason', '?')
    human = h.get('human_action', '?')
    print(f'- **操作**: {desc}')
    print(f'  **原因**: {reason}')
    print(f'  **需人类执行**: {human}')
    print()
" 2>/dev/null)
        BLOCKED_LIST=$(python3 -c "
import json
d = json.load(open('$MODE_FILE'))
blocked = d.get('blocked_human', [])
for b in blocked:
    desc = b.get('description', '?')
    rec = b.get('ai_recommendation', '?')
    rat = b.get('rationale', '?')
    print(f'- **决策**: {desc}')
    print(f'  **AI 推荐**: {rec}')
    print(f'  **依据**: {rat}')
    print()
" 2>/dev/null)
        TASK_LIST=$(python3 -c "
import json
d = json.load(open('$MODE_FILE'))
tasks = d.get('completed_tasks', [])
for t in tasks:
    desc = t.get('description', t) if isinstance(t, dict) else t
    ts = t.get('timestamp', '') if isinstance(t, dict) else ''
    print(f'- [x] {desc}  ({ts})')
" 2>/dev/null)
        ACTIVATED=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('activated_at','?'))" 2>/dev/null)
        EXPIRES=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','?'))" 2>/dev/null)
        {
            echo "# 目标模式执行报告"
            echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
            echo "## 目标"
            echo "$(sanitize_output "$GOAL")"
            echo ""
            echo "## 基本信息"
            echo "- 激活时间: $ACTIVATED"
            echo "- 过期时间: $EXPIRES"
            echo ""
            echo "## 执行摘要"
            echo "- 已完成任务数: $DONE"
            echo "- 跳过风险数: $SKIP"
            echo "- 硬边界拦截数: $HARD"
            echo "- 推迟决策数: $BLOCKED"
            echo "- 重试次数: $RETRY"
            echo ""
            echo "## 已完成任务"
            if [ -n "$TASK_LIST" ]; then
                echo "$TASK_LIST"
            else
                echo "无"
            fi
            echo ""
            echo "## 跳过的风险"
            if [ -n "$SKIP_LIST" ]; then
                echo "$SKIP_LIST"
            else
                echo "无"
            fi
            echo ""
            echo "## ⚠️ 需人为决策汇总"
            echo ""
            echo "| # | 类型 | 描述 | AI 推荐 | 依据 |"
            echo "|---|------|------|---------|------|"
            # 用 Python 从 JSON 生成聚合汇总表
            python3 -c "
import json
d = json.load(open('$MODE_FILE'))
hits = d.get('hard_boundary_hits', [])
blocked = d.get('blocked_human', [])
idx = 0
for h in hits:
    idx += 1
    desc = h.get('description', '?')
    reason = h.get('reason', '?')
    human = h.get('human_action', '?')
    print(f'| {idx} | 硬边界 | {desc} | {human} | {reason} |')
for b in blocked:
    idx += 1
    desc = b.get('description', '?')
    rec = b.get('ai_recommendation', '?')
    rat = b.get('rationale', '?')
    print(f'| {idx} | 推迟决策 | {desc} | {rec} | {rat} |')
if idx == 0:
    print('| - | - | 无需人类介入的项 | - | - |')
" 2>/dev/null
            echo ""
            echo "## ⚠️ 需人类介入项（硬边界）"
            if [ -n "$HARD_LIST" ]; then
                echo "$HARD_LIST"
            else
                echo "无"
            fi
            echo ""
            echo "## 推迟决策项（裁决链 Level 3 — 需人类裁决）"
            if [ -n "$BLOCKED_LIST" ]; then
                echo "$BLOCKED_LIST"
            else
                echo "无"
            fi
            echo ""
            echo "## 验证状态"
            echo "VERIFIED: 报告生成完毕（$DONE 项完成，$SKIP 项风险跳过，$HARD 项硬边界拦截，$BLOCKED 项推迟决策，$RETRY 次重试）"
        } > "$REPORT_FILE"
        echo "✅ 报告已生成: $REPORT_FILE"
        cat "$REPORT_FILE"
        ;;

    poll)
        # 目标模式轮询入口 — 由 loop skill / ralph-loop 调用
        POLL_FILE="$MODE_FILE"
        if [ ! -f "$POLL_FILE" ]; then
            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
                POLL_FILE="$STATE_DIR/unattended-mode.json"
            else
                echo "❌ 目标模式未激活，停止轮询"
                exit 1
            fi
        fi

        # 检查过期
        EXPIRES=$(python3 -c "import json; d=json.load(open('$POLL_FILE')); print(d.get('expires_at',''))" 2>/dev/null)
        if [ -n "$EXPIRES" ]; then
            EXPIRED=$(python3 -c "
from datetime import datetime
try:
    exp = datetime.fromisoformat('$EXPIRES')
    print('yes' if datetime.now() > exp else 'no')
except: print('no')" 2>/dev/null)
            if [ "$EXPIRED" = "yes" ]; then
                echo "⏰ 目标模式已过期（$EXPIRES），自动关闭"
                rm -f "$POLL_FILE" "$STATE_DIR/autonomous.active" 2>/dev/null
                # 过期时自动生成报告
                if [ -f "$MODE_FILE" ]; then
                    echo "   生成过期报告..."
                    bash "$0" report 2>/dev/null
                fi
                exit 0
            fi
        fi

        GOAL=$(python3 -c "import json; d=json.load(open('$POLL_FILE')); print(d.get('goal','?'))" 2>/dev/null)
        DONE=$(python3 -c "import json; d=json.load(open('$POLL_FILE')); print(len(d.get('completed_tasks',[])))" 2>/dev/null)
        SKIP=$(python3 -c "import json; d=json.load(open('$POLL_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
        HARD=$(python3 -c "import json; d=json.load(open('$POLL_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
        RETRY=$(python3 -c "import json; d=json.load(open('$POLL_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
        echo "🔄 目标轮询 $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "   目标: $(sanitize_output "$GOAL")"
        echo "   已完成: $DONE  已跳过风险: $SKIP  硬边界: $HARD  重试次数: $RETRY"

        # 集成 retry-budget.sh 状态检查
        RETRY_SCRIPT="$SCRIPT_DIR/retry-budget.sh"
        if [ -f "$RETRY_SCRIPT" ]; then
            RETRY_CTX=$(bash "$RETRY_SCRIPT" check 2>&1)
            RETRY_EXIT=$?
            if [ $RETRY_EXIT -eq 2 ] && [ -n "$RETRY_CTX" ]; then
                echo "⚠️ [Retry Budget BLOCKED] 以下错误已达 3 次上限，需人工干预:"
                echo "$RETRY_CTX" | head -5
            elif [ $RETRY_EXIT -eq 0 ]; then
                echo "   retry-budget: 正常"
            fi
        fi

        echo "   请继续执行目标，完成后用 lx-goal task-done 或 lx-goal report 输出报告"
        ;;

    task-done)
        # 标记一项任务为已完成
        DESCRIPTION="${2:-未知任务}"
        TASK_FILE="$MODE_FILE"
        if [ ! -f "$TASK_FILE" ]; then
            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
                TASK_FILE="$STATE_DIR/unattended-mode.json"
            else
                echo "❌ 目标模式未开启"
                exit 1
            fi
        fi
        export _LX_DESC="$DESCRIPTION"
        export _LX_TASK_FILE="$TASK_FILE"
        python3 <<'PYEOF'
import json, os
from datetime import datetime

desc = os.environ['_LX_DESC']
task_file = os.environ['_LX_TASK_FILE']

try:
    d = json.load(open(task_file))
except:
    d = {}
tasks = d.get('completed_tasks', [])
tasks.append({'description': desc, 'timestamp': datetime.now().isoformat()})
d['completed_tasks'] = tasks
tmp = task_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, task_file)
PYEOF
        echo "✅ 已标记任务完成: $(sanitize_output "$DESCRIPTION")"
        ;;

    skip-risk)
        # 记录跳过的风险（供 permission-gate 等调用）
        DESCRIPTION="${2:-未知风险}"
        TASK_FILE="$MODE_FILE"
        if [ ! -f "$TASK_FILE" ]; then
            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
                TASK_FILE="$STATE_DIR/unattended-mode.json"
            else
                echo "❌ 目标模式未开启"
                exit 1
            fi
        fi
        export _LX_DESC="$DESCRIPTION"
        export _LX_TASK_FILE="$TASK_FILE"
        python3 <<'PYEOF'
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
task_file = os.environ['_LX_TASK_FILE']

d = json.load(open(task_file))
risks = d.get('skipped_risks', [])
risks.append({'description': desc, 'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
d['skipped_risks'] = risks
tmp = task_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, task_file)
PYEOF
        echo "📝 已记录跳过的风险: $(sanitize_output "$DESCRIPTION")"
        ;;

    hard-boundary-hit)
        # 记录硬边界拦截项（rm / git写 / 敏感文件 / API Key）
        # 这些是物理禁区，绝不可执行，必须报告人类介入
        DESCRIPTION="${2:-未知硬边界}"
        REASON="${3:-未知原因}"
        HUMAN_ACTION="${4:-请人工审阅并决定是否执行}"
        TASK_FILE="$MODE_FILE"
        if [ ! -f "$TASK_FILE" ]; then
            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
                TASK_FILE="$STATE_DIR/unattended-mode.json"
            else
                echo "❌ 目标模式未开启"
                exit 1
            fi
        fi
        export _LX_DESC="$DESCRIPTION"
        export _LX_REASON="$REASON"
        export _LX_HUMAN_ACTION="$HUMAN_ACTION"
        export _LX_TASK_FILE="$TASK_FILE"
        python3 <<'PYEOF'
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
reason = os.environ['_LX_REASON']
human_action = os.environ['_LX_HUMAN_ACTION']
task_file = os.environ['_LX_TASK_FILE']

d = json.load(open(task_file))
hits = d.get('hard_boundary_hits', [])
hits.append({
    'description': desc,
    'reason': reason,
    'human_action': human_action,
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
})
d['hard_boundary_hits'] = hits
tmp = task_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, task_file)
PYEOF
        echo "🛑 硬边界拦截已记录: $(sanitize_output "$DESCRIPTION") (原因: $(sanitize_output "$REASON"))"
        ;;

	    blocked-human)
	        # 记录推迟到退出报告的人类决策项（裁决链 Level 3 blocked_human）
	        # 与 hard-boundary-hit 不同：这些不是物理禁区，而是 AI 无法确定需要人类裁决
	        DESCRIPTION="${2:-未知决策}"
	        AI_RECOMMENDATION="${3:-AI 推荐方案未提供}"
	        RATIONALE="${4:-决策依据未提供}"
	        TASK_FILE="$MODE_FILE"
	        if [ ! -f "$TASK_FILE" ]; then
	            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
	                TASK_FILE="$STATE_DIR/unattended-mode.json"
	            else
	                echo "❌ 目标模式未开启"
	                exit 1
	            fi
	        fi
        export _LX_DESC="$DESCRIPTION"
        export _LX_AI_RECOMMENDATION="$AI_RECOMMENDATION"
        export _LX_RATIONALE="$RATIONALE"
        export _LX_TASK_FILE="$TASK_FILE"
        python3 <<'PYEOF'
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
ai_recommendation = os.environ['_LX_AI_RECOMMENDATION']
rationale = os.environ['_LX_RATIONALE']
task_file = os.environ['_LX_TASK_FILE']

d = json.load(open(task_file))
blocked = d.get('blocked_human', [])
blocked.append({
    'description': desc,
    'ai_recommendation': ai_recommendation,
    'rationale': rationale,
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
})
d['blocked_human'] = blocked
tmp = task_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, task_file)
PYEOF
        echo "🤔 推迟决策已记录: $(sanitize_output "$DESCRIPTION") → 推荐: $(sanitize_output "$AI_RECOMMENDATION")"
	        ;;

    retry)
        # 增加重试计数
        TASK_FILE="$MODE_FILE"
        if [ ! -f "$TASK_FILE" ]; then
            if [ -f "$STATE_DIR/unattended-mode.json" ]; then
                TASK_FILE="$STATE_DIR/unattended-mode.json"
            else
                echo "❌ 目标模式未开启"
                exit 1
            fi
        fi
        python3 -c "
import json, os
file = '$TASK_FILE'
d = json.load(open(file))
d['retry_count'] = d.get('retry_count', 0) + 1
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null && echo "📝 重试计数 +1"
        ;;

    *)
        echo "用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|hard-boundary-hit|blocked-human|retry"
        echo ""
        echo "子命令:"
        echo "  lx-goal on \"目标描述\" [过期小时=6]"
        echo "    示例: lx-goal on \"完成 feature-registry 中所有 P0 条目的同步\""
        echo "    示例: lx-goal on \"将 test 覆盖率从 45% 提升到 80%\" 8"
        echo "  lx-goal off"
        echo "  lx-goal status"
        echo "  lx-goal set <json_key> <json_value>"
        echo "  lx-goal report                    输出执行报告"
        echo "  lx-goal poll                      轮询入口（loop skill 调用）"
        echo "  lx-goal task-done \"描述\"          标记任务完成"
        echo "  lx-goal skip-risk \"描述\"          记录跳过的风险"
        echo "  lx-goal blocked-human \"决策\" \"AI推荐\" \"依据\"     记录推迟到报告的人类决策"
	        echo "  lx-goal hard-boundary-hit \"操作\" \"原因\" \"需人类执行\"  记录硬边界拦截"
        echo "  lx-goal retry                     重试计数 +1"
        echo ""
        echo "驱动方式:"
        echo "  /loop 600s lx-goal poll            (定时轮询)"
        echo "  /ralph-loop:ralph-loop \"...\"       (自愈循环)"
        echo ""
        echo "与 lx-ghost 的区别:"
        echo "  lx-goal = 目标驱动（具体任务），lx-ghost = 方向驱动（开放探索）"
        exit 1
        ;;
esac
