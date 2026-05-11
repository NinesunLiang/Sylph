#!/usr/bin/env bash
# lx-unattended-toggle.sh — 切换无人值守模式
# 用法: lx-unattended on|off|status|set|report|poll|task-done
# 无人值守模式: AI 按目标持续执行直到完成，不干扰人，默认 6h 过期
# 向后兼容: 旧 .unattended-mode 文件标记仍可被 is_mode_active() 检测

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

# source harness_config for hc_get defaults
source "$SCRIPT_DIR/../hooks/harness_config.sh"

MODE_FILE="$STATE_DIR/unattended-mode.json"

case "${1:-status}" in
    on)
        GOAL="${2:-目标任务未指定}"
        EXPIRY_HOURS="${3:-$(hc_get "unattended_mode.default_expiry_hours" "6")}"
        EXPIRES=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(hours=$EXPIRY_HOURS)).isoformat())" 2>/dev/null)
        tmp="${MODE_FILE}.tmp.$$"
        cat > "$tmp" <<JSON
{
  "active": true,
  "mode": "unattended",
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
        rm -f "$STATE_DIR/.unattended-mode" 2>/dev/null
        # 创建 autonomous.active 信号供 completion-gate 等降级
        touch "$STATE_DIR/autonomous.active"
        echo "✅ 无人值守模式已开启 — 目标: $GOAL, ${EXPIRY_HOURS}h 过期"
        echo "   任务完成后执行: lx-unattended report 输出报告"
        ;;

    off)
        if [ -f "$MODE_FILE" ]; then
            rm -f "$MODE_FILE"
        fi
        rm -f "$STATE_DIR/.unattended-mode" 2>/dev/null
        rm -f "$STATE_DIR/autonomous.active" 2>/dev/null
        echo "✅ 无人值守模式已关闭"
        ;;

    status)
        if [ -f "$MODE_FILE" ]; then
            GOAL=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('goal','?'))" 2>/dev/null)
            EXP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','无'))" 2>/dev/null)
            DONE=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('completed_tasks',[])))" 2>/dev/null)
            SKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
            echo "📋 无人值守模式: 🟢 开启中"
            echo "   目标: $GOAL"
            echo "   过期: $EXP"
            echo "   已完成: $DONE  已跳过风险: $SKIP"
        elif [ -f "$STATE_DIR/.unattended-mode" ]; then
            echo "📋 无人值守模式: 🟢 开启中（旧格式）"
        else
            echo "📋 无人值守模式: ⚪ 已关闭"
        fi
        ;;

    set)
        KEY="$2"
        VALUE="$3"
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 无人值守模式未开启，无法修改"
            exit 1
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
" 2>/dev/null && echo "✅ 无人值守模式 $KEY 已更新为 $VALUE" || echo "❌ 更新失败"
        ;;

    report)
        if [ ! -f "$MODE_FILE" ]; then
            echo "⚠️ 无人值守模式未开启，无报告可输出"
            exit 1
        fi
        REPORT_FILE="$STATE_DIR/unattended-report.md"
        GOAL=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('goal','?'))" 2>/dev/null)
        DONE=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('completed_tasks',[])))" 2>/dev/null)
        SKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
        SKIP_LIST=$(python3 -c "
import json
d = json.load(open('$MODE_FILE'))
risks = d.get('skipped_risks', [])
for r in risks: print(f'- {r}')
" 2>/dev/null)
        {
            echo "# 无人值守模式执行报告"
            echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
            echo "## 目标"
            echo "$GOAL"
            echo ""
            echo "## 执行摘要"
            echo "- 已完成任务数: $DONE"
            echo "- 跳过风险数: $SKIP"
            echo ""
            echo "## 跳过的风险"
            if [ -n "$SKIP_LIST" ]; then
                echo "$SKIP_LIST"
            else
                echo "无"
            fi
        } > "$REPORT_FILE"
        echo "✅ 报告已生成: $REPORT_FILE"
        cat "$REPORT_FILE"
        ;;

    poll)
        # 无人值守模式轮询入口 — 由 loop skill 调用
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 无人值守模式未激活，停止轮询"
            exit 1
        fi
        GOAL=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('goal','?'))" 2>/dev/null)
        DONE=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('completed_tasks',[])))" 2>/dev/null)
        SKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
        RETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
        echo "🔄 无人值守轮询 $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "   目标: $GOAL"
        echo "   已完成: $DONE  已跳过风险: $SKIP  重试次数: $RETRY"

        # 集成 retry-budget.sh 状态检查（P0-1）
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

        echo "   请继续执行目标，完成后用 lx-unattended report 输出报告"
        ;;

    task-done)
        # 标记一项任务为已完成（修复 P0-3: JSON 字段死代码）
        DESCRIPTION="${2:-未知任务}"
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 无人值守模式未开启"
            exit 1
        fi
        TS=$(python3 -c "from datetime import datetime; print(datetime.now().isoformat())" 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
        _TASK_JSON=$(python3 -c "import json; print(json.dumps({'description':'$DESCRIPTION','timestamp':'$TS'}))" 2>/dev/null)
        python3 -c "
import json, os
file = '$MODE_FILE'
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

    *)
        echo "用法: lx-unattended on|off|status|set|report|poll|task-done"
        echo ""
        echo "子命令:"
        echo "  lx-unattended on \"目标描述\" [过期小时=6] — 开启无人值守模式"
        echo "  lx-unattended off — 关闭"
        echo "  lx-unattended status — 查看状态"
        echo "  lx-unattended set <json_key> <json_value> — 动态修改配置"
        echo "  lx-unattended report — 输出执行报告"
        echo "  lx-unattended poll — 轮询入口（loop skill 调用）"
        echo "  lx-unattended task-done \"描述\" — 标记任务完成"
        exit 1
        ;;
esac
