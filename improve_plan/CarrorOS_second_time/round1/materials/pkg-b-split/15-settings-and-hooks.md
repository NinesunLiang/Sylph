# hook 注册配置 + hook 小脚本

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | settings.json(脱敏)/全部 .sh
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/settings.json`(全文)

```
     1	{
     2	  "env": {
     3	    "ANTHROPIC_AUTH_TOKEN": "<REDACTED>",
     4	    "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic",
     5	    "ANTHROPIC_MODEL": "kimi-k3",
     6	    "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-k3",
     7	    "ANTHROPIC_DEFAULT_SONNET_MODEL": "kimi-k3",
     8	    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "kimi-k3",
     9	    "CLAUDE_CODE_SUBAGENT_MODEL": "kimi-k3",
    10	    "ENABLE_TOOL_SEARCH": "false",
    11	    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1048576"
    12	  },
    13	  "enabledPlugins": {
    14	    "pyright-lsp@claude-plugins-official": true
    15	  },
    16	  "effortLevel": "xhigh",
    17	  "skipDangerousModePermissionPrompt": true,
    18	  "skipWorkflowUsageWarning": true,
    19	  "model": "opus",
    20	  "hooks": {
    21	    "PreToolUse": [
    22	      {
    23	        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob",
    24	        "hooks": [
    25	          {
    26	            "type": "command",
    27	            "command": "bash \".claude/hooks/hook-launcher.sh\" \"pretool-gate.py\""
    28	          }
    29	        ]
    30	      },
    31	      {
    32	        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob",
    33	        "hooks": [
    34	          {
    35	            "type": "command",
    36	            "command": "bash \".claude/hooks/hook-launcher.sh\" \"carroros-night-deny.py\""
    37	          }
    38	        ]
    39	      }
    40	    ],
    41	    "UserPromptSubmit": [
    42	      {
    43	        "hooks": [
    44	          {
    45	            "type": "command",
    46	            "command": "python3 \".claude/hooks/pretool-user-approve.py\"",
    47	            "timeout": 3000
    48	          }
    49	        ]
    50	      }
    51	    ],
    52	    "PostToolUse": [
    53	      {
    54	        "matcher": "*",
    55	        "hooks": [
    56	          {
    57	            "type": "command",
    58	            "command": "python3 \".claude/hooks/posttool-gate.py\"",
    59	            "timeout": 5000
    60	          }
    61	        ]
    62	      }
    63	    ],
    64	    "SessionStart": [
    65	      {
    66	        "hooks": [
    67	          {
    68	            "type": "command",
    69	            "command": "python3 \".claude/hooks/session-start.py\"",
    70	            "timeout": 3000
    71	          }
    72	        ]
    73	      }
    74	    ],
    75	    "Stop": [
    76	      {
    77	        "hooks": [
    78	          {
    79	            "type": "command",
    80	            "command": "python3 \".claude/hooks/stop-flywheel.py\"",
    81	            "timeout": 10000
    82	          }
    83	        ]
    84	      }
    85	    ]
    86	  },
    87	  "statusLine": {
    88	    "type": "command",
    89	    "command": "bash \".claude/hooks/statusline-command.sh\""
    90	  }
    91	}
```

## `.claude/hooks/statusline-command.sh`(全文)

```
     1	#!/usr/bin/env bash
     2	set -u
     3	
     4	ROOT="${CARROROS_ROOT:-$(pwd)}"
     5	PYTHON="${PYTHON:-python3}"
     6	SCRIPT="$ROOT/.claude/scripts/statusline.py"
     7	FALLBACK="$ROOT/.claude/scripts/fallback_engine.py"
     8	
     9	fallback_event() {
    10	  local reason="$1"
    11	  if command -v "$PYTHON" >/dev/null 2>&1 && [ -f "$FALLBACK" ]; then
    12	    "$PYTHON" "$FALLBACK" cli_hook_failed low >/dev/null 2>&1 || true
    13	  fi
    14	  printf 'CarrorOS L1_BASE FALLBACK %s\n' "$reason" | cut -c 1-160
    15	}
    16	
    17	if ! command -v "$PYTHON" >/dev/null 2>&1; then
    18	  printf 'CarrorOS L1_BASE FALLBACK python_missing\n'
    19	  exit 0
    20	fi
    21	
    22	if [ ! -f "$SCRIPT" ]; then
    23	  fallback_event "no_statusline_script"
    24	  exit 0
    25	fi
    26	
    27	OUTPUT="$("$PYTHON" "$SCRIPT" 2>/dev/null)"
    28	STATUS=$?
    29	
    30	if [ "$STATUS" -ne 0 ] || [ -z "$OUTPUT" ]; then
    31	  fallback_event "cli_hook_failed"
    32	  exit 0
    33	fi
    34	
    35	printf '%s\n' "$OUTPUT" | head -n 1 | tr '\r\n' ' ' | cut -c 1-160
    36	exit 0```

## `.claude/hooks/hook-launcher.sh`(全文)

```
     1	#!/usr/bin/env bash
     2	# CarrorOS Hook Launcher
     3	# 用 $0 定位自身，切到项目根目录，再跑对应 hook
     4	# settings.json 里写: .claude/hooks/hook-launcher.sh <hook_name>.py
     5	
     6	set -euo pipefail
     7	
     8	# 从 launcher 自身路径定位项目根
     9	LAUNCHER_DIR="$(cd "$(dirname "$0")" && pwd)"
    10	PROJECT_ROOT="$(cd "$LAUNCHER_DIR/../.." && pwd)"
    11	
    12	HOOK_NAME="${1:-}"
    13	if [ -z "$HOOK_NAME" ]; then
    14	  echo "{\"continue\":true,\"message\":\"hook-launcher: missing hook name\"}"
    15	  exit 0
    16	fi
    17	
    18	HOOK_PATH="$LAUNCHER_DIR/$HOOK_NAME"
    19	
    20	# H3 fail-closed：关键 hook 缺失 = 治理链断裂，必须阻断而非静默放行。
    21	# 名单与 settings.json PreToolUse 注册项一一对应；新增关键 hook 时同步加入。
    22	CRITICAL_HOOKS="pretool-gate.py carroros-night-deny.py"
    23	_is_critical_hook() {
    24	  case " $CRITICAL_HOOKS " in
    25	    *" $1 "*) return 0 ;;
    26	    *) return 1 ;;
    27	  esac
    28	}
    29	
    30	if [ ! -f "$HOOK_PATH" ]; then
    31	  if _is_critical_hook "$HOOK_NAME"; then
    32	    echo "{\"continue\":true,\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"hook-launcher: CRITICAL hook missing: $HOOK_NAME — 治理链断裂，fail-closed 阻断本次工具调用。恢复该文件后重试。\"}}"
    33	    echo "hook-launcher: BLOCKED - critical hook missing: $HOOK_NAME" >&2
    34	    exit 2
    35	  fi
    36	  echo "{\"continue\":true,\"message\":\"hook-launcher: hook not found: $HOOK_NAME\"}"
    37	  exit 0
    38	fi
    39	
    40	cd "$PROJECT_ROOT"
    41	
    42	# Sol 复审 P1-SOL-2 锁紧：生产路径显式清除 night-deny 的测试覆写变量，
    43	# 保证 marker 根只能由 hook 文件 __file__ 锚定（模型/会话环境无法拐根）。
    44	unset NIGHT_DENY_ROOT
    45	
    46	case "$HOOK_NAME" in
    47	  *.sh)
    48	    exec bash "$HOOK_PATH"
    49	    ;;
    50	  *)
    51	    exec python3 "$HOOK_PATH"
    52	    ;;
    53	esac
```

## `.claude/skills/lx-ghost/scripts/lx-ghost.sh`(全文)

```
     1	#!/usr/bin/env bash
     2	# lx-ghost.sh — 幽灵模式（方向驱动自主探索）
     3	# 用法: lx-ghost on|off|status|set <key> <value>|poll
     4	# 幽灵模式: 给 AI 一个"方向"，AI 自主探索并修复，不干扰人，默认 3h 过期
     5	# 与 lx-goal 的区别: ghost = 方向驱动（开源探索），goal = 目标驱动（具体任务）
     6	# 同时创建 autonomous.active 信号供所有 hook 降级
     7	#
     8	# 哲学映射:
     9	#   #3 先守护: gate 降级为 warn-only 而非硬阻断
    10	#   #4 没验证=没做: poll 报告 + completion 软评分
    11	#   #6 0信任: 危险操作记录 skipped_risks 而不是跳过
    12	
    13	SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    14	PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
    15	STATE_DIR="$PROJECT_ROOT/.omc/state"
    16	mkdir -p "$STATE_DIR" 2>/dev/null
    17	
    18	# source harness_config for hc_get defaults
    19	source "$SCRIPT_DIR/../../../hooks/harness_config.sh"
    20	
    21	mkdir -p "$STATE_DIR/tokens" 2>/dev/null
    22	MODE_FILE="$STATE_DIR/tokens/lx-ghost.json"
    23	
    24	# 智能参数检测：第一个参数不是已知子命令 → 当作方向描述自动激活
    25	_KNOWN_SUBCOMMANDS="on|off|status|set|poll|skip-risk|hard-boundary-hit|blocked-human|retry"
    26	if [ -n "${1:-}" ] && ! echo "$1" | grep -Eq "^($_KNOWN_SUBCOMMANDS)$"; then
    27	    exec bash "$0" on "$@"
    28	fi
    29	
    30	case "${1:-status}" in
    31	    on)
    32	        DIRECTION="${2:-自主探索和修复系统问题}"
    33	        INTERVAL="${3:-$(hc_get "ghost_mode.default_poll_interval" "600")}"
    34	        EXPIRY_HOURS="${4:-$(hc_get "ghost_mode.default_expiry_hours" "3")}"
    35	        # DG-007 安全修复: 用 json.dumps 序列化而非 heredoc 裸拼接
    36	        # 避免 direction 中的换行/引号/特殊字符破坏 JSON 结构
    37	        export _LX_DIRECTION="$DIRECTION"
    38	        export _LX_INTERVAL="$INTERVAL"
    39	        export _LX_EXPIRY_HOURS="$EXPIRY_HOURS"
    40	        export _LX_MODE_FILE="$MODE_FILE"
    41	        ${PYTHON_BIN:-python3} <<'PYEOF'
    42	import json, os
    43	from datetime import datetime, timedelta, timezone
    44	
    45	direction = os.environ['_LX_DIRECTION']
    46	interval = int(os.environ['_LX_INTERVAL'])
    47	expiry_hours = int(os.environ['_LX_EXPIRY_HOURS'])
    48	mode_file = os.environ['_LX_MODE_FILE']
    49	expires = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
    50	
    51	data = {
    52	    "active": True,
    53	    "mode": "ghost",
    54	    "direction": direction,
    55	    "cycle_interval_seconds": interval,
    56	    "expires_at": expires,
    57	    "activated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    58	    "retry_count": 0,
    59	    "skipped_risks": [],
    60	    "hard_boundary_hits": [],
    61	    "blocked_human": []
    62	}
    63	
    64	tmp = mode_file + '.tmp.' + str(os.getpid())
    65	with open(tmp, 'w', encoding='utf-8') as f:
    66	    json.dump(data, f, indent=2, ensure_ascii=False)
    67	os.rename(tmp, mode_file)
    68	PYEOF
    69	        # 创建 autonomous.active 信号供 completion-gate 等降级
    70	        touch "$STATE_DIR/tokens/autonomous.active"
    71	        # 清理旧格式文件
    72	        rm -f "$STATE_DIR/.unattended-mode" "$STATE_DIR/ghost-mode.active" 2>/dev/null
    73	DATE=$(date +%Y-%m-%d)
    74	SLUG=$(echo "$DIRECTION" | tr " " "-" | tr -cd "[:alnum:]-_" | head -c 50)
    75	[ -z "$SLUG" ] && SLUG="ghost-$(date +%H%M%S)"
    76	CHAT_DIR="$PROJECT_ROOT/.omc/chats/${DATE}/${SLUG}"
    77	mkdir -p "$CHAT_DIR"
    78		${PYTHON_BIN:-python3} -c "import json; json.dump({'phase':'exploring','created_at':'$(date -u +%Y-%m-%dT%H:%M:%SZ)'},open('$CHAT_DIR/state.json','w'))"
    79		echo "# $DIRECTION
    80	
    81	> ghost模式自动创建 @ $(date)" > "$CHAT_DIR/progress.md"
    82		echo "RPE文档层: $CHAT_DIR" >&2
    83		# Save chat_dir to lx-ghost.json for runtime subcommands
    84		export _LX_CHAT_DIR="$CHAT_DIR"
    85		export _LX_MODE_FILE="$MODE_FILE"
    86		${PYTHON_BIN:-python3} <<'PYEOF'
    87	import json, os
    88	chat_dir = os.environ['_LX_CHAT_DIR']
    89	mode_file = os.environ['_LX_MODE_FILE']
    90	d = json.load(open(mode_file))
    91	d['rpe_chat_dir'] = chat_dir
    92	tmp = mode_file + '.tmp.' + str(os.getpid())
    93	with open(tmp, 'w', encoding='utf-8') as f:
    94	    json.dump(d, f, indent=2, ensure_ascii=False)
    95	os.rename(tmp, mode_file)
    96	PYEOF
    97		# 计算 CronCreate 参数
    98		CRON_MIN=$((INTERVAL / 60))
    99		[ "$CRON_MIN" -lt 1 ] && CRON_MIN=1
   100		echo "✅ 幽灵模式已开启 — 方向: $DIRECTION, 每 ${INTERVAL}s 轮询, ${EXPIRY_HOURS}h 过期"
   101		echo "   autonomous.active 信号已创建，evidence/completion gate 降级为 warn-only"
   102		echo ""
   103		echo "🔧 [必须执行·Step 0.5.3] 注册 CronCreate 跨会话轮询:"
   104		echo ""
   105		echo "   CronCreate"
   106		echo "     cron: \"*/${CRON_MIN} * * * *\""
   107		echo "     prompt: \"lx-ghost poll → 读取: cat $CHAT_DIR/progress.md → 继续探索方向'$DIRECTION' → 记录发现 → 完成则 lx-ghost off\""
   108		echo "     recurring: true"
   109		echo "     durable: true"
   110		echo ""
   111		echo "   ⚠️ durable=true: 会话结束后继续轮询，跨会话恢复"
   112		echo "   ⚠️ 跳过此步 = 幽灵模式仅在当前会话有效，会话结束即消失"
   113	        # 将决策链注入 AI 上下文（Oracle M1: 确保模式激活时 AI 立即看到决策链）
   114	        DECISION_CHAIN="$PROJECT_ROOT/.claude/reference/autonomous-decision-chain.md"
   115	        if [ -f "$DECISION_CHAIN" ]; then
   116	            echo "[.claude/reference/autonomous-decision-chain.md]"
   117	            cat "$DECISION_CHAIN"
   118	            echo ""
   119	        fi
   120	        ;;
   121	
   122	    off)
   123			# Write summary to RPE chat dir before cleanup
   124			if [ -f "$MODE_FILE" ]; then
   125				CHAT_DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_chat_dir',''))" 2>/dev/null)
   126				if [ -n "$CHAT_DIR" ] && [ -d "$CHAT_DIR" ]; then
   127					RETRY=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
   128					SKIP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
   129					HARD=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
   130					{
   131						echo ""
   132						echo "---"
   133						echo "## 退出摘要"
   134						echo "- 关闭时间: $(date)"
   135						echo "- 重试次数: ${RETRY:-0}"
   136						echo "- 跳过风险: ${SKIP:-0}"
   137						echo "- 硬边界拦截: ${HARD:-0}"
   138						echo ""
   139						echo "> 幽灵模式自动关闭 @ $(date)"
   140					} >> "$CHAT_DIR/progress.md"
   141					${PYTHON_BIN:-python3} -c "
   142	import json
   143	sf = '$CHAT_DIR/state.json'
   144	d = json.load(open(sf))
   145	d['phase'] = 'completed'
   146	d['completed_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
   147	json.dump(d, open(sf, 'w'), indent=2, ensure_ascii=False)
   148	" 2>/dev/null
   149				fi
   150				rm -f "$MODE_FILE"
   151			fi
   152			# 清理旧格式文件
   153			rm -f "$STATE_DIR/ghost-mode.json" "$STATE_DIR/ghost-mode.active" 2>/dev/null
   154			rm -f "$STATE_DIR/tokens/autonomous.active" 2>/dev/null
   155			echo "✅ 幽灵模式已关闭，所有 hook 恢复正常阻断"
   156			;;
   157	    status)
   158	        if [ -f "$MODE_FILE" ]; then
   159	            DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('direction','?'))" 2>/dev/null)
   160	            EXP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','无'))" 2>/dev/null)
   161	            INT=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('cycle_interval_seconds','?'))" 2>/dev/null)
   162	            RETRY=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
   163	            SKIP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
   164	            HARD=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
   165	            echo "📋 幽灵模式 (lx-ghost): 🟢 开启中"
   166	            echo "   方向: $DIR"
   167	            echo "   间隔: ${INT}s"
   168	            echo "   过期: $EXP"
   169	            echo "   重试: $RETRY  跳过风险: $SKIP  硬边界: $HARD"
   170	        elif [ -f "$STATE_DIR/ghost-mode.json" ]; then
   171	            echo "📋 幽灵模式 (旧格式 ghost-mode.json): 🟡 兼容中"
   172	            echo "   建议执行 lx-ghost off && lx-ghost on \"方向\" 迁移到新格式"
   173	        else
   174	            echo "📋 幽灵模式 (lx-ghost): ⚪ 已关闭"
   175	        fi
   176	        if [ -f "$STATE_DIR/tokens/autonomous.active" ]; then
   177	            echo "   autonomous.active 信号: ✅ 存在"
   178	        fi
   179	        ;;
   180	
   181	    set)
   182	        KEY="$2"
   183	        VALUE="$3"
   184	        if [ ! -f "$MODE_FILE" ]; then
   185	            echo "❌ 幽灵模式未开启，无法修改"
   186	            exit 1
   187	        fi
   188	        export _LX_KEY="$KEY"
   189	        export _LX_VALUE="$VALUE"
   190	        export _LX_SET_MODE_FILE="$MODE_FILE"
   191	        ${PYTHON_BIN:-python3} <<'PYEOF'
   192	import json, os
   193	key = os.environ['_LX_KEY']
   194	value_str = os.environ['_LX_VALUE']
   195	mode_file = os.environ['_LX_SET_MODE_FILE']
   196	
   197	d = json.load(open(mode_file))
   198	# 尝试解析 JSON 值（数字/布尔/对象），失败则当字符串
   199	try:
   200	    value = json.loads(value_str)
   201	except (json.JSONDecodeError, ValueError):
   202	    value = value_str
   203	d[key] = value
   204	
   205	tmp = mode_file + '.tmp.' + str(os.getpid())
   206	with open(tmp, 'w', encoding='utf-8') as f:
   207	    json.dump(d, f, indent=2, ensure_ascii=False)
   208	os.rename(tmp, mode_file)
   209	print(f"✅ 幽灵模式 {key} 已更新为 {value}")
   210	PYEOF
   211	        ;;
   212	
   213	    poll)
   214	        # 幽灵模式轮询入口 — 由 loop skill / ralph-loop 调用
   215	        if [ ! -f "$MODE_FILE" ]; then
   216	            # 回退检查旧格式
   217	            if [ -f "$STATE_DIR/ghost-mode.json" ]; then
   218	                DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$STATE_DIR/ghost-mode.json')); print(d.get('direction','?'))" 2>/dev/null)
   219	                echo "⚠️ 旧格式 ghost-mode.json 存在，建议迁移: lx-ghost off && lx-ghost on \"$DIR\""
   220	            else
   221	                echo "❌ 幽灵模式未激活，停止轮询"
   222	            fi
   223	            exit 1
   224	        fi
   225	
   226	        # 检查过期
   227	        EXPIRES=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at',''))" 2>/dev/null)
   228	        if [ -n "$EXPIRES" ]; then
   229	            EXPIRED=$(${PYTHON_BIN:-python3} -c "
   230	from datetime import datetime
   231	try:
   232	    exp = datetime.fromisoformat('$EXPIRES')
   233	    print('yes' if datetime.now() > exp else 'no')
   234	except: print('no')" 2>/dev/null)
   235	            if [ "$EXPIRED" = "yes" ]; then
   236	                echo "⏰ 幽灵模式已过期（$EXPIRES），自动关闭"
   237	                rm -f "$MODE_FILE" "$STATE_DIR/tokens/autonomous.active" 2>/dev/null
   238	                exit 0
   239	            fi
   240	        fi
   241	
   242		echo "🔄 Ghost Poll #$((RETRY + 1)) | 方向: $DIR | 过期: $EXPIRES"
   243		echo ""
   244		CHAT_DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_chat_dir',''))" 2>/dev/null)
   245		echo "📋 执行指令:"
   246		echo "   1. 读取上次探索上下文: cat $CHAT_DIR/progress.md"
   247		echo "   2. 继续围绕方向: $DIR"
   248		echo "   3. 记录发现: 追加到 $CHAT_DIR/progress.md"
   249		echo "   4. 如有风险: lx-ghost skip-risk '风险描述'"
   250		echo "   5. 如方向完成: lx-ghost off"
   251		echo ""
   252		echo "   📊 已重试: $RETRY | 已跳过风险: $SKIP | 硬边界: $(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)"
   253			;;
   254	
   255	    skip-risk)
   256			# 记录跳过的风险（供 permission-gate 等调用）
   257			DESCRIPTION="${2:-未知风险}"
   258			if [ ! -f "$MODE_FILE" ]; then
   259				echo "❌ 幽灵模式未开启"
   260				exit 1
   261			fi
   262			export _LX_DESC="$DESCRIPTION"
   263			export _LX_MODE_FILE="$MODE_FILE"
   264			${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
   265	import json, os
   266	from datetime import datetime, timezone
   267	
   268	desc = os.environ['_LX_DESC']
   269	mode_file = os.environ['_LX_MODE_FILE']
   270	
   271	d = json.load(open(mode_file))
   272	risks = d.get('skipped_risks', [])
   273	risks.append({'description': desc, 'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
   274	d['skipped_risks'] = risks
   275	
   276	# Append to RPE progress.md
   277	chat_dir = d.get('rpe_chat_dir', '')
   278	if chat_dir:
   279	    progress_file = os.path.join(chat_dir, 'progress.md')
   280	    if os.path.exists(progress_file):
   281	        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   282	        with open(progress_file, 'a') as pf:
   283	            pf.write(f'\n- [skip-risk] {desc}  ({ts})\n')
   284	
   285	tmp = mode_file + '.tmp.' + str(os.getpid())
   286	with open(tmp, 'w', encoding='utf-8') as f:
   287	    json.dump(d, f, indent=2, ensure_ascii=False)
   288	os.rename(tmp, mode_file)
   289	PYEOF
   290			echo "📝 已记录跳过的风险: $DESCRIPTION"
   291			;;
   292	
   293	    hard-boundary-hit)
   294			# 记录硬边界拦截项（rm / git写 / 敏感文件 / API Key）
   295			DESCRIPTION="${2:-未知硬边界}"
   296			REASON="${3:-未知原因}"
   297			HUMAN_ACTION="${4:-请人工审阅并决定是否执行}"
   298			if [ ! -f "$MODE_FILE" ]; then
   299				echo "❌ 幽灵模式未开启"
   300				exit 1
   301			fi
   302			export _LX_DESC="$DESCRIPTION"
   303			export _LX_REASON="$REASON"
   304			export _LX_HUMAN_ACTION="$HUMAN_ACTION"
   305			export _LX_MODE_FILE="$MODE_FILE"
   306			${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
   307	import json, os
   308	from datetime import datetime, timezone
   309	
   310	desc = os.environ['_LX_DESC']
   311	reason = os.environ['_LX_REASON']
   312	human_action = os.environ['_LX_HUMAN_ACTION']
   313	mode_file = os.environ['_LX_MODE_FILE']
   314	
   315	d = json.load(open(mode_file))
   316	hits = d.get('hard_boundary_hits', [])
   317	hits.append({
   318	    'description': desc,
   319	    'reason': reason,
   320	    'human_action': human_action,
   321	    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   322	})
   323	d['hard_boundary_hits'] = hits
   324	
   325	# Append to RPE progress.md
   326	chat_dir = d.get('rpe_chat_dir', '')
   327	if chat_dir:
   328	    progress_file = os.path.join(chat_dir, 'progress.md')
   329	    if os.path.exists(progress_file):
   330	        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   331	        with open(progress_file, 'a') as pf:
   332	            pf.write(f'\n- [hard-boundary] {desc} — {reason}  ({ts})\n')
   333	
   334	tmp = mode_file + '.tmp.' + str(os.getpid())
   335	with open(tmp, 'w', encoding='utf-8') as f:
   336	    json.dump(d, f, indent=2, ensure_ascii=False)
   337	os.rename(tmp, mode_file)
   338	PYEOF
   339			echo "🛑 硬边界拦截已记录: $DESCRIPTION (原因: $REASON)"
   340			;;
   341	
   342	    blocked-human)
   343			# 记录推迟到退出报告的人类决策项（裁决链 Level 3 blocked_human）
   344			# 与 hard-boundary-hit 不同：这些不是物理禁区，而是 AI 无法确定需要人类裁决
   345			DESCRIPTION="${2:-未知决策}"
   346			AI_RECOMMENDATION="${3:-AI 推荐方案未提供}"
   347			RATIONALE="${4:-决策依据未提供}"
   348			if [ ! -f "$MODE_FILE" ]; then
   349				echo "❌ 幽灵模式未开启"
   350				exit 1
   351			fi
   352			export _LX_DESC="$DESCRIPTION"
   353			export _LX_AI_RECOMMENDATION="$AI_RECOMMENDATION"
   354			export _LX_RATIONALE="$RATIONALE"
   355			export _LX_MODE_FILE="$MODE_FILE"
   356			${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
   357	import json, os
   358	from datetime import datetime, timezone
   359	
   360	desc = os.environ['_LX_DESC']
   361	ai_recommendation = os.environ['_LX_AI_RECOMMENDATION']
   362	rationale = os.environ['_LX_RATIONALE']
   363	mode_file = os.environ['_LX_MODE_FILE']
   364	
   365	d = json.load(open(mode_file))
   366	blocked = d.get('blocked_human', [])
   367	blocked.append({
   368	    'description': desc,
   369	    'ai_recommendation': ai_recommendation,
   370	    'rationale': rationale,
   371	    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   372	})
   373	d['blocked_human'] = blocked
   374	
   375	# Append to RPE progress.md
   376	chat_dir = d.get('rpe_chat_dir', '')
   377	if chat_dir:
   378	    progress_file = os.path.join(chat_dir, 'progress.md')
   379	    if os.path.exists(progress_file):
   380	        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   381	        with open(progress_file, 'a') as pf:
   382	            pf.write(f'\n- [blocked-human] {desc} → {ai_recommendation}  ({ts})\n')
   383	
   384	tmp = mode_file + '.tmp.' + str(os.getpid())
   385	with open(tmp, 'w', encoding='utf-8') as f:
   386	    json.dump(d, f, indent=2, ensure_ascii=False)
   387	os.rename(tmp, mode_file)
   388	PYEOF
   389			echo "🤔 推迟决策已记录: $DESCRIPTION → 推荐: $AI_RECOMMENDATION"
   390			;;
   391	
   392	    retry)
   393	        # 增加重试计数（供 retry-budget 对接）
   394	        if [ ! -f "$MODE_FILE" ]; then
   395	            echo "❌ 幽灵模式未开启"
   396	            exit 1
   397	        fi
   398	        ${PYTHON_BIN:-python3} -c "
   399	import json, os
   400	file = '$MODE_FILE'
   401	d = json.load(open(file))
   402	d['retry_count'] = d.get('retry_count', 0) + 1
   403	tmp = file + '.tmp.' + str(os.getpid())
   404	with open(tmp, 'w') as f:
   405	    json.dump(d, f, indent=2, ensure_ascii=False)
   406	os.rename(tmp, file)
   407	" 2>/dev/null && echo "📝 重试计数 +1（当前: $(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('$MODE_FILE')).get('retry_count',0))" 2>/dev/null)）"
   408	        ;;
   409	
   410	    *)
   411	        echo "用法: lx-ghost on|off|status|set|poll|skip-risk|hard-boundary-hit|blocked-human|retry"
   412	        echo ""
   413	        echo "子命令:"
   414	        echo "  lx-ghost on \"方向描述\" [间隔秒数=600] [过期小时=3]"
   415	        echo "    示例: lx-ghost on \"将项目四维评分提升到 90+\""
   416	        echo "    示例: lx-ghost on \"检查所有 shell 脚本安全隐患\" 300 2"
   417	        echo "  lx-ghost off"
   418	        echo "  lx-ghost status"
   419	        echo "  lx-ghost set <json_key> <json_value>"
   420	        echo "  lx-ghost poll                    (loop skill 轮询入口)"
   421	        echo "  lx-ghost skip-risk \"描述\"       (记录跳过的风险)"
   422	        echo "  lx-ghost blocked-human \"决策\" \"AI推荐\" \"依据\"     (记录推迟到报告的人类决策)"
   423	        echo "  lx-ghost hard-boundary-hit \"操作\" \"原因\" \"需人类执行\"  (记录硬边界拦截)"
   424	        echo "  lx-ghost retry                   (重试计数 +1)"
   425	        echo ""
   426	        echo "驱动方式:"
   427	        echo "  /loop 600s lx-ghost poll         (定时轮询)"
   428	        echo "  /ralph-loop:ralph-loop \"...\"     (自愈循环)"
   429	        echo ""
   430	        echo "与 lx-goal 的区别:"
   431	        echo "  lx-ghost = 方向驱动（开源探索），lx-goal = 目标驱动（具体任务）"
   432	        exit 1
   433	        ;;
   434	esac
```

## `.claude/skills/lx-goal/scripts/lx-goal.sh`(全文)

```
     1	#!/usr/bin/env bash
     2	# lx-goal.sh — 兼容 wrapper，实际逻辑委托给 lx-goal.py
     3	# 用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|retry
     4	
     5	SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
     6	exec python3 "$SCRIPT_DIR/lx-goal.py" "$@"
     7	
```

## `.claude/profiles/merge-profile.sh`(全文)

```
     1	#!/bin/bash
     2	
     3	# merge-profile.sh — v5.3.0 base+diff 合并工具
     4	# 用法：
     5	#   bash .claude/profiles/merge-profile.sh go       # 合并 base+go
     6	#   bash .claude/profiles/merge-profile.sh node      # 合并 base+node
     7	#   bash .claude/profiles/merge-profile.sh python    # 合并 base+python
     8	#   bash .claude/profiles/merge-profile.sh rust      # 合并 base+rust
     9	#   bash .claude/profiles/merge-profile.sh go --dry-run  # 预览不写文件
    10	#   bash .claude/profiles/merge-profile.sh --list    # 列出可用 profile
    11	#
    12	# 合并规则：
    13	#   1. 从 base/harness.yaml 读取所有通用字段
    14	#   2. 用 {lang}/harness.yaml 的字段覆盖（同名 section.key 以 diff 为准）
    15	#   3. diff 中的 hooks_enabled 子键做"增量覆盖"（不替换整块，仅覆盖出现的键）
    16	#   4. 输出合并后的完整 harness.yaml
    17	
    18	set -eo pipefail
    19	RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
    20	SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    21	BASE="$SCRIPT_DIR/base/harness.yaml"
    22	OUTPUT="${CLAUDE_DIR:-.claude}/harness.yaml"
    23	
    24	# ── --list ────────────────────────────────────────────────────────
    25	if [ "$1" = "--list" ]; then
    26	    echo "可用 profile："
    27	    for d in "$SCRIPT_DIR"/*/; do
    28	        name=$(basename "$d")
    29	        [[ "$name" == "base" ]] && continue
    30	        [ -f "$d/harness.yaml" ] && echo "  $name"
    31	    done
    32	    exit 0
    33	fi
    34	
    35	LANG="${1:-}"
    36	DRY_RUN=false
    37	[ "$2" = "--dry-run" ] && DRY_RUN=true
    38	
    39	# ── 参数校验 ──────────────────────────────────────────────────────
    40	if [ -z "$LANG" ]; then
    41	    echo -e "${RED}[ERROR]${NC} 请指定语言: go / node / python / rust"
    42	    echo "  用法: bash .claude/profiles/merge-profile.sh <lang> [--dry-run]"
    43	    exit 1
    44	fi
    45	
    46	DIFF="$SCRIPT_DIR/$LANG/harness.yaml"
    47	
    48	if [ ! -f "$BASE" ]; then
    49	    echo -e "${RED}[ERROR]${NC} base/harness.yaml 不存在: $BASE"
    50	    exit 1
    51	fi
    52	if [ ! -f "$DIFF" ]; then
    53	    echo -e "${RED}[ERROR]${NC} 未找到 profile: $DIFF"
    54	    exit 1
    55	fi
    56	
    57	# ── Python3 合并核心 ──────────────────────────────────────────────
    58	_MERGE_PY=$(mktemp "${TMPDIR:-/tmp}/.merge_profile_py.XXXXXX") || { echo "创建临时文件失败"; exit 1; }
    59	
    60	cat > "$_MERGE_PY" << 'PYEOF'
    61	import sys
    62	
    63	def parse_yaml_flat(path):
    64	    """解析 YAML 为嵌套 dict（支持2层 + 列表）"""
    65	    result = {}
    66	    current_section = None
    67	    current_list_key = None
    68	    current_list = []
    69	    with open(path, encoding='utf-8') as f:
    70	        for raw in f:
    71	            line = raw.rstrip('\n\r')
    72	            stripped = line.strip()
    73	            if not stripped or stripped.startswith('#'):
    74	                if current_list_key and current_list:
    75	                    if current_section not in result:
    76	                        result[current_section] = {}
    77	                    result[current_section][current_list_key] = current_list[:]
    78	                    current_list_key, current_list = None, []
    79	                continue
    80	            indent = len(line) - len(line.lstrip())
    81	            if stripped.startswith('- '):
    82	                if current_list_key:
    83	                    current_list.append(stripped[2:].strip().strip('"').strip("'"))
    84	                continue
    85	            if current_list_key and current_list:
    86	                if current_section not in result:
    87	                    result[current_section] = {}
    88	                result[current_section][current_list_key] = current_list[:]
    89	                current_list_key, current_list = None, []
    90	            if ':' in stripped:
    91	                colon = stripped.index(':')
    92	                key = stripped[:colon].strip()
    93	                val = stripped[colon+1:].strip()
    94	                if val and val[0] in ('"', "'") and val[-1] == val[0]:
    95	                    val = val[1:-1]
    96	                if indent == 0:
    97	                    if val:
    98	                        result[key] = val
    99	                    else:
   100	                        current_section = key
   101	                        if key not in result:
   102	                            result[key] = {}
   103	                elif indent > 0 and current_section:
   104	                    if val:
   105	                        result[current_section][key] = val
   106	                    else:
   107	                        current_list_key = key
   108	                        current_list = []
   109	        if current_list_key and current_list and current_section:
   110	            result[current_section][current_list_key] = current_list[:]
   111	    return result
   112	
   113	
   114	def merge(base, diff):
   115	    merged = {}
   116	    for k, v in base.items():
   117	        if isinstance(v, dict):
   118	            merged[k] = dict(v)
   119	        elif isinstance(v, list):
   120	            merged[k] = list(v)
   121	        else:
   122	            merged[k] = v
   123	    for k, v in diff.items():
   124	        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
   125	            merged[k] = {**merged[k], **v}
   126	        elif isinstance(v, list):
   127	            merged[k] = list(v)
   128	        else:
   129	            merged[k] = v
   130	    return merged
   131	
   132	
   133	def val_to_yaml(v, indent=2):
   134	    pad = ' ' * indent
   135	    if isinstance(v, list):
   136	        return '\n' + '\n'.join(f"{pad}- {item}" for item in v)
   137	    if isinstance(v, bool):
   138	        return 'true' if v else 'false'
   139	    s = str(v)
   140	    if any(c in s for c in ['#', ':', '{', '}', '[', ']', ',', '&', '*', '?', '|', '<', '>', '=', '!', '%', '@', '`']):
   141	        return f'"{s}"'
   142	    return s
   143	
   144	
   145	base_data = parse_yaml_flat(sys.argv[1])
   146	diff_data = parse_yaml_flat(sys.argv[2])
   147	lang = sys.argv[3]
   148	merged = merge(base_data, diff_data)
   149	
   150	SECTION_ORDER = [
   151	    'project', 'protected_files', 'architecture', 'workflow',
   152	    'task_decomposition', 'knowledge', 'turn_counter', 'fuzzy_detection',
   153	    'lsp_suggest', 'subagent_guard', 'completion_gate', 'bash_audit',
   154	    'permission_gate', 'sublimation', 'correction_detector',
   155	    'session_handoff', 'error_dna', 'coupling', 'hooks_enabled',
   156	]
   157	
   158	lines = [
   159	    f"# harness-kit harness.yaml — {lang} profile (base+diff merged)",
   160	    f"# 由 merge-profile.sh 生成，源文件: profiles/base + profiles/{lang}",
   161	    "# 手动编辑此文件的修改在下次 merge 时会被覆盖",
   162	    "",
   163	]
   164	
   165	seen = set()
   166	for section in SECTION_ORDER:
   167	    if section not in merged:
   168	        continue
   169	    seen.add(section)
   170	    v = merged[section]
   171	    lines.append(f"{section}:")
   172	    if isinstance(v, dict):
   173	        for sk, sv in v.items():
   174	            yv = val_to_yaml(sv)
   175	            if yv.startswith('\n'):
   176	                lines.append(f"  {sk}:{yv}")
   177	            else:
   178	                lines.append(f"  {sk}: {yv}")
   179	    else:
   180	        lines.append(f"  {val_to_yaml(v)}")
   181	    lines.append("")
   182	
   183	for section, v in merged.items():
   184	    if section in seen:
   185	        continue
   186	    lines.append(f"{section}:")
   187	    if isinstance(v, dict):
   188	        for sk, sv in v.items():
   189	            yv = val_to_yaml(sv)
   190	            if yv.startswith('\n'):
   191	                lines.append(f"  {sk}:{yv}")
   192	            else:
   193	                lines.append(f"  {sk}: {yv}")
   194	    else:
   195	        lines.append(f"  {val_to_yaml(v)}")
   196	    lines.append("")
   197	
   198	print('\n'.join(lines))
   199	PYEOF
   200	
   201	MERGED=$(${PYTHON_BIN:-python3} "$_MERGE_PY" "$BASE" "$DIFF" "$LANG")
   202	rm -f "$_MERGE_PY"
   203	
   204	# ── 输出 ──────────────────────────────────────────────────────────
   205	if [ "$DRY_RUN" = true ]; then
   206	    echo -e "${YELLOW}[DRY-RUN]${NC} 合并结果（不写文件）："
   207	    echo "---"
   208	    echo "$MERGED"
   209	    echo "---"
   210	    LINES=$(echo "$MERGED" | wc -l | tr -d ' ')
   211	    echo -e "${GREEN}[INFO]${NC} 合并后 $LINES 行（base 覆盖 + $LANG diff）"
   212	else
   213	    mkdir -p "$(dirname "$OUTPUT")"
   214	    echo "$MERGED" > "$OUTPUT"
   215	    LINES=$(wc -l < "$OUTPUT" | tr -d ' ')
   216	    echo -e "${GREEN}[OK]${NC} 已写入 $OUTPUT（$LINES 行，base + $LANG diff 合并）"
   217	fi
```
