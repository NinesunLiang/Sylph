#!/usr/bin/env bash
# lx-ghost.sh — 幽灵模式（方向驱动自主探索）
# 用法: lx-ghost on|off|status|set <key> <value>|poll
# 幽灵模式: 给 AI 一个"方向"，AI 自主探索并修复，不干扰人，默认 3h 过期
# 与 lx-goal 的区别: ghost = 方向驱动（开源探索），goal = 目标驱动（具体任务）
# 同时创建 autonomous.active 信号供所有 hook 降级
#
# 哲学映射:
#   #3 先守护: gate 降级为 warn-only 而非硬阻断
#   #4 没验证=没做: poll 报告 + completion 软评分
#   #6 0信任: 危险操作记录 skipped_risks 而不是跳过

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

# source harness_config for hc_get defaults
source "$SCRIPT_DIR/../../../hooks/harness_config.sh"

MODE_FILE="$STATE_DIR/lx-ghost.json"

# 智能参数检测：第一个参数不是已知子命令 → 当作方向描述自动激活
_KNOWN_SUBCOMMANDS="on|off|status|set|poll|skip-risk|retry"
if [ -n "${1:-}" ] && ! echo "$1" | grep -Eq "^($_KNOWN_SUBCOMMANDS)$"; then
    exec bash "$0" on "$@"
fi

case "${1:-status}" in
    on)
        DIRECTION="${2:-自主探索和修复系统问题}"
        INTERVAL="${3:-$(hc_get "ghost_mode.default_poll_interval" "600")}"
        EXPIRY_HOURS="${4:-$(hc_get "ghost_mode.default_expiry_hours" "3")}"
        EXPIRES=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(hours=$EXPIRY_HOURS)).isoformat())" 2>/dev/null)
        # 原子写入 lx-ghost.json
        tmp="${MODE_FILE}.tmp.$$"
        cat > "$tmp" <<JSON
{
  "active": true,
  "mode": "ghost",
  "direction": "$DIRECTION",
  "cycle_interval_seconds": $INTERVAL,
  "expires_at": "$EXPIRES",
  "activated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "retry_count": 0,
  "skipped_risks": []
}
JSON
        mv -f "$tmp" "$MODE_FILE" 2>/dev/null
        # 创建 autonomous.active 信号供 completion-gate 等降级
        touch "$STATE_DIR/autonomous.active"
        # 清理旧格式文件
        rm -f "$STATE_DIR/.unattended-mode" "$STATE_DIR/ghost-mode.active" 2>/dev/null
        echo "✅ 幽灵模式已开启 — 方向: $DIRECTION, 每 ${INTERVAL}s 轮询, ${EXPIRY_HOURS}h 过期"
        echo "   autonomous.active 信号已创建，所有 hook 降级为 warn-only"
        echo "   使用 CronCreate 驱动（无 10 轮上限，持续到过期或手动停止）"
        echo "   停止: /lx-ghost off 或 CronDelete <job-id>"
        ;;

    off)
        if [ -f "$MODE_FILE" ]; then
            rm -f "$MODE_FILE"
        fi
        # 清理旧格式文件
        rm -f "$STATE_DIR/ghost-mode.json" "$STATE_DIR/ghost-mode.active" 2>/dev/null
        rm -f "$STATE_DIR/autonomous.active" 2>/dev/null
        echo "✅ 幽灵模式已关闭，所有 hook 恢复正常阻断"
        ;;

    status)
        if [ -f "$MODE_FILE" ]; then
            DIR=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('direction','?'))" 2>/dev/null)
            EXP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','无'))" 2>/dev/null)
            INT=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('cycle_interval_seconds','?'))" 2>/dev/null)
            RETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
            SKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
            echo "📋 幽灵模式 (lx-ghost): 🟢 开启中"
            echo "   方向: $DIR"
            echo "   间隔: ${INT}s"
            echo "   过期: $EXP"
            echo "   重试: $RETRY  跳过风险: $SKIP"
        elif [ -f "$STATE_DIR/ghost-mode.json" ]; then
            echo "📋 幽灵模式 (旧格式 ghost-mode.json): 🟡 兼容中"
            echo "   建议执行 lx-ghost off && lx-ghost on \"方向\" 迁移到新格式"
        else
            echo "📋 幽灵模式 (lx-ghost): ⚪ 已关闭"
        fi
        if [ -f "$STATE_DIR/autonomous.active" ]; then
            echo "   autonomous.active 信号: ✅ 存在"
        fi
        ;;

    set)
        KEY="$2"
        VALUE="$3"
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 幽灵模式未开启，无法修改"
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
" 2>/dev/null && echo "✅ 幽灵模式 $KEY 已更新为 $VALUE" || echo "❌ 更新失败"
        ;;

    poll)
        # 幽灵模式轮询入口 — 由 loop skill / ralph-loop 调用
        if [ ! -f "$MODE_FILE" ]; then
            # 回退检查旧格式
            if [ -f "$STATE_DIR/ghost-mode.json" ]; then
                DIR=$(python3 -c "import json; d=json.load(open('$STATE_DIR/ghost-mode.json')); print(d.get('direction','?'))" 2>/dev/null)
                echo "⚠️ 旧格式 ghost-mode.json 存在，建议迁移: lx-ghost off && lx-ghost on \"$DIR\""
            else
                echo "❌ 幽灵模式未激活，停止轮询"
            fi
            exit 1
        fi

        # 检查过期
        EXPIRES=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at',''))" 2>/dev/null)
        if [ -n "$EXPIRES" ]; then
            EXPIRED=$(python3 -c "
from datetime import datetime
try:
    exp = datetime.fromisoformat('$EXPIRES')
    print('yes' if datetime.now() > exp else 'no')
except: print('no')" 2>/dev/null)
            if [ "$EXPIRED" = "yes" ]; then
                echo "⏰ 幽灵模式已过期（$EXPIRES），自动关闭"
                rm -f "$MODE_FILE" "$STATE_DIR/autonomous.active" 2>/dev/null
                exit 0
            fi
        fi

        echo "=== 幽灵轮询 [$(date -u +%Y-%m-%dT%H:%M:%SZ)] ==="
        DIR=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('direction','?'))" 2>/dev/null)
        RETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
        SKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
        echo "  方向: $DIR"
        echo "  重试次数: $RETRY  已跳过风险: $SKIP"

        # 状态面板：检查活跃特征 + 未提交变更
        if [ -d "$PROJECT_ROOT/rpe" ]; then
            ACTIVE=$(ls "$PROJECT_ROOT/rpe/" 2>/dev/null | head -5 | tr '\n' ' ')
            [ -n "$ACTIVE" ] && echo "  活跃特征: $ACTIVE"
        fi
        MODIFIED=$(cd "$PROJECT_ROOT" && git diff --name-only 2>/dev/null | head -10 | tr '\n' ' ')
        [ -n "$MODIFIED" ] && echo "  未提交变更: $MODIFIED"

        # 集成 retry-budget.sh 状态检查
        RETRY_SCRIPT="$SCRIPT_DIR/retry-budget.sh"
        if [ -f "$RETRY_SCRIPT" ]; then
            RETRY_CTX=$(bash "$RETRY_SCRIPT" check 2>&1)
            RETRY_EXIT=$?
            if [ $RETRY_EXIT -eq 2 ] && [ -n "$RETRY_CTX" ]; then
                echo "⚠️ [Retry Budget BLOCKED] 以下错误已达 3 次上限，需人工干预:"
                echo "$RETRY_CTX" | head -5
            elif [ $RETRY_EXIT -eq 0 ]; then
                echo "  retry-budget: 正常"
            fi
        fi

        # 四维评分检查（如果项目有评分机制）
        SCORE_SCRIPT="$SCRIPT_DIR/auto-score.sh"
        if [ -f "$SCORE_SCRIPT" ]; then
            echo "  评分检查: 可用 (bash auto-score.sh)"
        fi

        echo "  命令: ${DIR}"
        echo "  自主探索并修复，发现问题自行处理（最多 3 次），无法处理的记录等待人工"
        echo "  ⚡ 注意保持方向感，不要偏离方向做无关优化"
        ;;

    skip-risk)
        # 记录跳过的风险（供 permission-gate 等调用）
        DESCRIPTION="${2:-未知风险}"
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 幽灵模式未开启"
            exit 1
        fi
        python3 -c "
import json, os
file = '$MODE_FILE'
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
        # 增加重试计数（供 retry-budget 对接）
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 幽灵模式未开启"
            exit 1
        fi
        python3 -c "
import json, os
file = '$MODE_FILE'
d = json.load(open(file))
d['retry_count'] = d.get('retry_count', 0) + 1
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null && echo "📝 重试计数 +1（当前: $(python3 -c "import json; print(json.load(open('$MODE_FILE')).get('retry_count',0))" 2>/dev/null)）"
        ;;

    *)
        echo "用法: lx-ghost on|off|status|set|poll|skip-risk|retry"
        echo ""
        echo "子命令:"
        echo "  lx-ghost on \"方向描述\" [间隔秒数=600] [过期小时=3]"
        echo "    示例: lx-ghost on \"将项目四维评分提升到 90+\""
        echo "    示例: lx-ghost on \"检查所有 shell 脚本安全隐患\" 300 2"
        echo "  lx-ghost off"
        echo "  lx-ghost status"
        echo "  lx-ghost set <json_key> <json_value>"
        echo "  lx-ghost poll                    (loop skill 轮询入口)"
        echo "  lx-ghost skip-risk \"描述\"       (记录跳过的风险)"
        echo "  lx-ghost retry                   (重试计数 +1)"
        echo ""
        echo "驱动方式:"
        echo "  /loop 600s lx-ghost poll         (定时轮询)"
        echo "  /ralph-loop:ralph-loop \"...\"     (自愈循环)"
        echo ""
        echo "与 lx-goal 的区别:"
        echo "  lx-ghost = 方向驱动（开源探索），lx-goal = 目标驱动（具体任务）"
        exit 1
        ;;
esac
