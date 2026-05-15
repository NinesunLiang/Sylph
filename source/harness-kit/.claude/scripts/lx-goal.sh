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
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

# source harness_config for hc_get defaults
source "$SCRIPT_DIR/../../../hooks/harness_config.sh"

MODE_FILE="$STATE_DIR/lx-goal.json"

# 智能参数检测：第一个参数不是已知子命令 → 当作目标描述自动激活
_KNOWN_SUBCOMMANDS="on|off|status|set|report|poll|task-done|skip-risk|retry"
if [ -n "${1:-}" ] && ! echo "$1" | grep -Eq "^($_KNOWN_SUBCOMMANDS)$"; then
    exec bash "$0" on "$@"
fi

case "${1:-status}" in
    on)
        GOAL="${2:-目标任务未指定}"
        EXPIRY_HOURS="${3:-$(hc_get "goal_mode.default_expiry_hours" "6")}"
        EXPIRES=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(hours=$EXPIRY_HOURS)).isoformat())" 2>/dev/null)
        tmp="${MODE_FILE}.tmp.$$"
        cat > "$tmp" <<JSON
{
  "active": true,
  "mode": "goal",
  "goal": "$GOAL",
  "expires_at": "$EXPIRES",
  "activated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "retry_count": 0,
  "skipped_risks": [],
  "completed_tasks": []
}
JSON
        mv -f "$tmp" "$MODE_FILE" 2>/dev/null
        # 清理旧格式
        rm -f "$STATE_DIR/unattended-mode.json" "$STATE_DIR/.unattended-mode" 2>/dev/null
        # 创建 autonomous.active 信号供 completion-gate 等降级
        touch "$STATE_DIR/autonomous.active"
        echo "✅ 目标模式已开启 — 目标: $GOAL, ${EXPIRY_HOURS}h 过期"
        echo "   autonomous.active 信号已创建，所有 hook 降级为 warn-only"
        echo "   使用 CronCreate 跨会话恢复（无 10 轮上限）"
        echo "   任务逐项标记: lx-goal task-done \"完成项描述\""
        echo "   完成后输出报告: lx-goal report"
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
            RETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
            echo "📋 目标模式 (lx-goal): 🟢 开启中"
            echo "   目标: $GOAL"
            echo "   过期: $EXP"
            echo "   已完成: $DONE  跳过风险: $SKIP  重试: $RETRY"
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
        RETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
        SKIP_LIST=$(python3 -c "
import json
d = json.load(open('$MODE_FILE'))
risks = d.get('skipped_risks', [])
for r in risks:
    desc = r.get('description', r) if isinstance(r, dict) else r
    print(f'- {desc}')
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
            echo "$GOAL"
            echo ""
            echo "## 基本信息"
            echo "- 激活时间: $ACTIVATED"
            echo "- 过期时间: $EXPIRES"
            echo ""
            echo "## 执行摘要"
            echo "- 已完成任务数: $DONE"
            echo "- 跳过风险数: $SKIP"
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
            echo "## 验证状态"
            echo "VERIFIED: 报告生成完毕（$DONE 项完成，$SKIP 项风险跳过，$RETRY 次重试）"
        } > "$REPORT_FILE"
        echo "✅ 报告已生成: $REPORT_FILE"
        cat "$REPORT_FILE"
        ;;

    poll)
        # 目标模式轮询入口 — 由 CronCreate / ralph-loop 调用（无 10 轮上限）
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
        RETRY=$(python3 -c "import json; d=json.load(open('$POLL_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
        echo "🔄 目标轮询 $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "   目标: $GOAL"
        echo "   已完成: $DONE  已跳过风险: $SKIP  重试次数: $RETRY"

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
        TS=$(python3 -c "from datetime import datetime; print(datetime.now().isoformat())" 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
        _TASK_JSON=$(python3 -c "import json; print(json.dumps({'description':'$DESCRIPTION','timestamp':'$TS'}))" 2>/dev/null)
        python3 -c "
import json, os
file = '$TASK_FILE'
try:
    d = json.load(open(file))
except:
    d = {}
tasks = d.get('completed_tasks', [])
tasks.append(${_TASK_JSON:-'{}'})
d['completed_tasks'] = tasks
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null
        echo "✅ 已标记任务完成: $DESCRIPTION"
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
        python3 -c "
import json, os
file = '$TASK_FILE'
d = json.load(open(file))
risks = d.get('skipped_risks', [])
risks.append({'description': '$DESCRIPTION', 'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'})
d['skipped_risks'] = risks
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null && echo "📝 已记录跳过的风险: $DESCRIPTION" || echo "❌ 记录失败"
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
        echo "用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|retry"
        echo ""
        echo "子命令:"
        echo "  lx-goal on \"目标描述\" [过期小时=6]"
        echo "    示例: lx-goal on \"完成 feature-registry 中所有 P0 条目的同步\""
        echo "    示例: lx-goal on \"将 test 覆盖率从 45% 提升到 80%\" 8"
        echo "  lx-goal off"
        echo "  lx-goal status"
        echo "  lx-goal set <json_key> <json_value>"
        echo "  lx-goal report                    输出执行报告"
        echo "  lx-goal poll                      轮询入口（CronCreate 调用）"
        echo "  lx-goal task-done \"描述\"          标记任务完成"
        echo "  lx-goal skip-risk \"描述\"          记录跳过的风险"
        echo "  lx-goal retry                     重试计数 +1"
        echo ""
        echo "驱动方式:"
        echo "  使用 CronCreate 调度 lx-goal poll   (跨会话恢复，无 10 轮上限)"
        echo "  /ralph-loop:ralph-loop \"...\"       (自愈循环)"
        echo ""
        echo "与 lx-ghost 的区别:"
        echo "  lx-goal = 目标驱动（具体任务），lx-ghost = 方向驱动（开放探索）"
        exit 1
        ;;
esac
