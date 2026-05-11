#!/usr/bin/env bash
# lx-unattended-toggle.sh — 切换无人值守模式
# 用法: lx-unattended on|off|status|set
# 无人值守模式: AI 按目标持续执行直到完成，不干扰人，默认 6h 过期
# 向后兼容: 旧 .unattended-mode 文件标记仍可被 is_mode_active() 检测

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

MODE_FILE="$STATE_DIR/unattended-mode.json"

case "${1:-status}" in
    on)
        GOAL="${2:-目标任务未指定}"
        EXPIRY_HOURS="${3:-6}"
        EXPIRES=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(hours=$EXPIRY_HOURS)).isoformat())" 2>/dev/null)
        cat > "$MODE_FILE" <<JSON
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
import json
d = json.load(open('$MODE_FILE'))
d['$KEY'] = $VALUE
json.dump(d, open('$MODE_FILE','w'), indent=2)
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

    *)
        echo "用法: lx-unattended on|off|status|set|report"
        echo ""
        echo "子命令:"
        echo "  lx-unattended on \"目标描述\" [过期小时=6]"
        echo "  lx-unattended off"
        echo "  lx-unattended status"
        echo "  lx-unattended set <json_key> <json_value>"
        echo "  lx-unattended report — 输出执行报告"
        exit 1
        ;;
esac
