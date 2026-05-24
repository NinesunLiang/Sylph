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
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

# source harness_config for hc_get defaults
source "$SCRIPT_DIR/../../../hooks/harness_config.sh"

MODE_FILE="$STATE_DIR/lx-ghost.json"

# 智能参数检测：第一个参数不是已知子命令 → 当作方向描述自动激活
_KNOWN_SUBCOMMANDS="on|off|status|set|poll|skip-risk|hard-boundary-hit|blocked-human|retry"
if [ -n "${1:-}" ] && ! echo "$1" | grep -Eq "^($_KNOWN_SUBCOMMANDS)$"; then
    exec bash "$0" on "$@"
fi

case "${1:-status}" in
    on)
        DIRECTION="${2:-自主探索和修复系统问题}"
        INTERVAL="${3:-$(hc_get "ghost_mode.default_poll_interval" "600")}"
        EXPIRY_HOURS="${4:-$(hc_get "ghost_mode.default_expiry_hours" "3")}"
        # DG-007 安全修复: 用 json.dumps 序列化而非 heredoc 裸拼接
        # 避免 direction 中的换行/引号/特殊字符破坏 JSON 结构
        export _LX_DIRECTION="$DIRECTION"
        export _LX_INTERVAL="$INTERVAL"
        export _LX_EXPIRY_HOURS="$EXPIRY_HOURS"
        export _LX_MODE_FILE="$MODE_FILE"
        ${PYTHON_BIN:-python3} <<'PYEOF'
import json, os
from datetime import datetime, timedelta, timezone

direction = os.environ['_LX_DIRECTION']
interval = int(os.environ['_LX_INTERVAL'])
expiry_hours = int(os.environ['_LX_EXPIRY_HOURS'])
mode_file = os.environ['_LX_MODE_FILE']
expires = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()

data = {
    "active": True,
    "mode": "ghost",
    "direction": direction,
    "cycle_interval_seconds": interval,
    "expires_at": expires,
    "activated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    "retry_count": 0,
    "skipped_risks": [],
    "hard_boundary_hits": [],
    "blocked_human": []
}

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
        # 创建 autonomous.active 信号供 completion-gate 等降级
        touch "$STATE_DIR/autonomous.active"
        # 清理旧格式文件
        rm -f "$STATE_DIR/.unattended-mode" "$STATE_DIR/ghost-mode.active" 2>/dev/null
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$DIRECTION" | tr " " "-" | tr -cd "[:alnum:]-_" | head -c 50)
[ -z "$SLUG" ] && SLUG="ghost-$(date +%H%M%S)"
CHAT_DIR="$PROJECT_ROOT/.omc/chats/${DATE}/${SLUG}"
mkdir -p "$CHAT_DIR"
	${PYTHON_BIN:-python3} -c "import json; json.dump({'phase':'exploring','created_at':'$(date -u +%Y-%m-%dT%H:%M:%SZ)'},open('$CHAT_DIR/state.json','w'))"
	echo "# $DIRECTION

> ghost模式自动创建 @ $(date)" > "$CHAT_DIR/progress.md"
	echo "RPE文档层: $CHAT_DIR" >&2
	# Save chat_dir to lx-ghost.json for runtime subcommands
	export _LX_CHAT_DIR="$CHAT_DIR"
	export _LX_MODE_FILE="$MODE_FILE"
	${PYTHON_BIN:-python3} <<'PYEOF'
import json, os
chat_dir = os.environ['_LX_CHAT_DIR']
mode_file = os.environ['_LX_MODE_FILE']
d = json.load(open(mode_file))
d['rpe_chat_dir'] = chat_dir
tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
	# 计算 CronCreate 参数
	CRON_MIN=$((INTERVAL / 60))
	[ "$CRON_MIN" -lt 1 ] && CRON_MIN=1
	echo "✅ 幽灵模式已开启 — 方向: $DIRECTION, 每 ${INTERVAL}s 轮询, ${EXPIRY_HOURS}h 过期"
	echo "   autonomous.active 信号已创建，evidence/completion gate 降级为 warn-only"
	echo ""
	echo "🔧 [必须执行·Step 0.5.3] 注册 CronCreate 跨会话轮询:"
	echo ""
	echo "   CronCreate"
	echo "     cron: \"*/${CRON_MIN} * * * *\""
	echo "     prompt: \"lx-ghost poll → 读取: cat $CHAT_DIR/progress.md → 继续探索方向'$DIRECTION' → 记录发现 → 完成则 lx-ghost off\""
	echo "     recurring: true"
	echo "     durable: true"
	echo ""
	echo "   ⚠️ durable=true: 会话结束后继续轮询，跨会话恢复"
	echo "   ⚠️ 跳过此步 = 幽灵模式仅在当前会话有效，会话结束即消失"
        # 将决策链注入 AI 上下文（Oracle M1: 确保模式激活时 AI 立即看到决策链）
        DECISION_CHAIN="$PROJECT_ROOT/.claude/reference/autonomous-decision-chain.md"
        if [ -f "$DECISION_CHAIN" ]; then
            echo "[.claude/reference/autonomous-decision-chain.md]"
            cat "$DECISION_CHAIN"
            echo ""
        fi
        ;;

    off)
		# Write summary to RPE chat dir before cleanup
		if [ -f "$MODE_FILE" ]; then
			CHAT_DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_chat_dir',''))" 2>/dev/null)
			if [ -n "$CHAT_DIR" ] && [ -d "$CHAT_DIR" ]; then
				RETRY=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
				SKIP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
				HARD=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
				{
					echo ""
					echo "---"
					echo "## 退出摘要"
					echo "- 关闭时间: $(date)"
					echo "- 重试次数: ${RETRY:-0}"
					echo "- 跳过风险: ${SKIP:-0}"
					echo "- 硬边界拦截: ${HARD:-0}"
					echo ""
					echo "> 幽灵模式自动关闭 @ $(date)"
				} >> "$CHAT_DIR/progress.md"
				${PYTHON_BIN:-python3} -c "
import json
sf = '$CHAT_DIR/state.json'
d = json.load(open(sf))
d['phase'] = 'completed'
d['completed_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
json.dump(d, open(sf, 'w'), indent=2, ensure_ascii=False)
" 2>/dev/null
			fi
			rm -f "$MODE_FILE"
		fi
		# 清理旧格式文件
		rm -f "$STATE_DIR/ghost-mode.json" "$STATE_DIR/ghost-mode.active" 2>/dev/null
		rm -f "$STATE_DIR/autonomous.active" 2>/dev/null
		echo "✅ 幽灵模式已关闭，所有 hook 恢复正常阻断"
		;;
    status)
        if [ -f "$MODE_FILE" ]; then
            DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('direction','?'))" 2>/dev/null)
            EXP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','无'))" 2>/dev/null)
            INT=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('cycle_interval_seconds','?'))" 2>/dev/null)
            RETRY=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
            SKIP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
            HARD=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
            echo "📋 幽灵模式 (lx-ghost): 🟢 开启中"
            echo "   方向: $DIR"
            echo "   间隔: ${INT}s"
            echo "   过期: $EXP"
            echo "   重试: $RETRY  跳过风险: $SKIP  硬边界: $HARD"
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
        export _LX_KEY="$KEY"
        export _LX_VALUE="$VALUE"
        export _LX_SET_MODE_FILE="$MODE_FILE"
        ${PYTHON_BIN:-python3} <<'PYEOF'
import json, os
key = os.environ['_LX_KEY']
value_str = os.environ['_LX_VALUE']
mode_file = os.environ['_LX_SET_MODE_FILE']

d = json.load(open(mode_file))
# 尝试解析 JSON 值（数字/布尔/对象），失败则当字符串
try:
    value = json.loads(value_str)
except (json.JSONDecodeError, ValueError):
    value = value_str
d[key] = value

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
print(f"✅ 幽灵模式 {key} 已更新为 {value}")
PYEOF
        ;;

    poll)
        # 幽灵模式轮询入口 — 由 loop skill / ralph-loop 调用
        if [ ! -f "$MODE_FILE" ]; then
            # 回退检查旧格式
            if [ -f "$STATE_DIR/ghost-mode.json" ]; then
                DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$STATE_DIR/ghost-mode.json')); print(d.get('direction','?'))" 2>/dev/null)
                echo "⚠️ 旧格式 ghost-mode.json 存在，建议迁移: lx-ghost off && lx-ghost on \"$DIR\""
            else
                echo "❌ 幽灵模式未激活，停止轮询"
            fi
            exit 1
        fi

        # 检查过期
        EXPIRES=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at',''))" 2>/dev/null)
        if [ -n "$EXPIRES" ]; then
            EXPIRED=$(${PYTHON_BIN:-python3} -c "
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

	echo "🔄 Ghost Poll #$((RETRY + 1)) | 方向: $DIR | 过期: $EXPIRES"
	echo ""
	CHAT_DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_chat_dir',''))" 2>/dev/null)
	echo "📋 执行指令:"
	echo "   1. 读取上次探索上下文: cat $CHAT_DIR/progress.md"
	echo "   2. 继续围绕方向: $DIR"
	echo "   3. 记录发现: 追加到 $CHAT_DIR/progress.md"
	echo "   4. 如有风险: lx-ghost skip-risk '风险描述'"
	echo "   5. 如方向完成: lx-ghost off"
	echo ""
	echo "   📊 已重试: $RETRY | 已跳过风险: $SKIP | 硬边界: $(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)"
		;;

    skip-risk)
		# 记录跳过的风险（供 permission-gate 等调用）
		DESCRIPTION="${2:-未知风险}"
		if [ ! -f "$MODE_FILE" ]; then
			echo "❌ 幽灵模式未开启"
			exit 1
		fi
		export _LX_DESC="$DESCRIPTION"
		export _LX_MODE_FILE="$MODE_FILE"
		${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
mode_file = os.environ['_LX_MODE_FILE']

d = json.load(open(mode_file))
risks = d.get('skipped_risks', [])
risks.append({'description': desc, 'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
d['skipped_risks'] = risks

# Append to RPE progress.md
chat_dir = d.get('rpe_chat_dir', '')
if chat_dir:
    progress_file = os.path.join(chat_dir, 'progress.md')
    if os.path.exists(progress_file):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\n- [skip-risk] {desc}  ({ts})\n')

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
		echo "📝 已记录跳过的风险: $DESCRIPTION"
		;;

    hard-boundary-hit)
		# 记录硬边界拦截项（rm / git写 / 敏感文件 / API Key）
		DESCRIPTION="${2:-未知硬边界}"
		REASON="${3:-未知原因}"
		HUMAN_ACTION="${4:-请人工审阅并决定是否执行}"
		if [ ! -f "$MODE_FILE" ]; then
			echo "❌ 幽灵模式未开启"
			exit 1
		fi
		export _LX_DESC="$DESCRIPTION"
		export _LX_REASON="$REASON"
		export _LX_HUMAN_ACTION="$HUMAN_ACTION"
		export _LX_MODE_FILE="$MODE_FILE"
		${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
reason = os.environ['_LX_REASON']
human_action = os.environ['_LX_HUMAN_ACTION']
mode_file = os.environ['_LX_MODE_FILE']

d = json.load(open(mode_file))
hits = d.get('hard_boundary_hits', [])
hits.append({
    'description': desc,
    'reason': reason,
    'human_action': human_action,
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
})
d['hard_boundary_hits'] = hits

# Append to RPE progress.md
chat_dir = d.get('rpe_chat_dir', '')
if chat_dir:
    progress_file = os.path.join(chat_dir, 'progress.md')
    if os.path.exists(progress_file):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\n- [hard-boundary] {desc} — {reason}  ({ts})\n')

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
		echo "🛑 硬边界拦截已记录: $DESCRIPTION (原因: $REASON)"
		;;

    blocked-human)
		# 记录推迟到退出报告的人类决策项（裁决链 Level 3 blocked_human）
		# 与 hard-boundary-hit 不同：这些不是物理禁区，而是 AI 无法确定需要人类裁决
		DESCRIPTION="${2:-未知决策}"
		AI_RECOMMENDATION="${3:-AI 推荐方案未提供}"
		RATIONALE="${4:-决策依据未提供}"
		if [ ! -f "$MODE_FILE" ]; then
			echo "❌ 幽灵模式未开启"
			exit 1
		fi
		export _LX_DESC="$DESCRIPTION"
		export _LX_AI_RECOMMENDATION="$AI_RECOMMENDATION"
		export _LX_RATIONALE="$RATIONALE"
		export _LX_MODE_FILE="$MODE_FILE"
		${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
ai_recommendation = os.environ['_LX_AI_RECOMMENDATION']
rationale = os.environ['_LX_RATIONALE']
mode_file = os.environ['_LX_MODE_FILE']

d = json.load(open(mode_file))
blocked = d.get('blocked_human', [])
blocked.append({
    'description': desc,
    'ai_recommendation': ai_recommendation,
    'rationale': rationale,
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
})
d['blocked_human'] = blocked

# Append to RPE progress.md
chat_dir = d.get('rpe_chat_dir', '')
if chat_dir:
    progress_file = os.path.join(chat_dir, 'progress.md')
    if os.path.exists(progress_file):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\n- [blocked-human] {desc} → {ai_recommendation}  ({ts})\n')

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
		echo "🤔 推迟决策已记录: $DESCRIPTION → 推荐: $AI_RECOMMENDATION"
		;;

    retry)
        # 增加重试计数（供 retry-budget 对接）
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 幽灵模式未开启"
            exit 1
        fi
        ${PYTHON_BIN:-python3} -c "
import json, os
file = '$MODE_FILE'
d = json.load(open(file))
d['retry_count'] = d.get('retry_count', 0) + 1
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null && echo "📝 重试计数 +1（当前: $(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('$MODE_FILE')).get('retry_count',0))" 2>/dev/null)）"
        ;;

    *)
        echo "用法: lx-ghost on|off|status|set|poll|skip-risk|hard-boundary-hit|blocked-human|retry"
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
        echo "  lx-ghost blocked-human \"决策\" \"AI推荐\" \"依据\"     (记录推迟到报告的人类决策)"
        echo "  lx-ghost hard-boundary-hit \"操作\" \"原因\" \"需人类执行\"  (记录硬边界拦截)"
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
