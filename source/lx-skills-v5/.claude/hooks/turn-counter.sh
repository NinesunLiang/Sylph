#!/usr/bin/env bash
# turn-counter.sh — UserPromptSubmit — 统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测
# Role: 统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测

source "$(dirname "$0")/harness_config.sh"
hc_enabled "turn_counter" || { cat > /dev/null; exit 0; }
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
STATE_FILE="$STATE_DIR/session-turns.json"
TODO_FILE="$STATE_DIR/todo-queue.md"
mkdir -p "$STATE_DIR"

# 保存用户原始输入（供模糊指令检测使用）
FUZZY_CHECK="$STATE_DIR/.last-user-prompt"
tee "$FUZZY_CHECK"

current_count=0
if [ -f "$STATE_FILE" ]; then
    if command -v jq &>/dev/null; then
        current_count=$(jq -r '.count // 0' "$STATE_FILE" 2>/dev/null || echo 0)
    else
        current_count=$(grep -o '"count"[[:space:]]*:[[:space:]]*[0-9]*' "$STATE_FILE" 2>/dev/null | sed 's/.*:[[:space:]]*//' | head -1)
        [ -z "$current_count" ] && current_count=0
    fi
fi
if ! [[ "$current_count" =~ ^[0-9]+$ ]]; then
    current_count=0
fi

new_count=$((current_count + 1))
updated_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "{\"count\": $new_count, \"updated\": \"$updated_at\"}" > "$STATE_FILE"

TODO_INTERVAL=$(hc_get "turn_counter.todo_refresh_interval" "10")
TODO_MAX=$(hc_get "turn_counter.todo_max_items" "15")
DOC_ROOT=$(hc_get "workflow.doc_root" "rpe")
EXEC_DOC=$(hc_get "workflow.executor_doc" "executor.md")

if [ "$TODO_INTERVAL" -gt 0 ] && [ $(( new_count % TODO_INTERVAL )) -eq 0 ]; then
    echo "═══ [轮次 $new_count] 锚定 ═══"

    # ─── 铁律摘要（压缩为1行）─────────────────────────────────────
    echo "铁律: 编造❌ 裁定🟢 证据🔒 Git审批✅ 冻结📦 隐私🔐"

    # ─── Pipeline Step ─────────────────────────────────────────
    PIPELINE_STEP_SCRIPT="$PROJECT_ROOT/.claude/scripts/pipeline-step.sh"
    if [ -f "$PIPELINE_STEP_SCRIPT" ]; then
        PIPELINE_CTX=$(bash "$PIPELINE_STEP_SCRIPT" inject 2>/dev/null)
        [ -n "$PIPELINE_CTX" ] && echo "$PIPELINE_CTX"
    fi

    # ─── Retry Budget ──────────────────────────────────────────
    RETRY_SCRIPT="$PROJECT_ROOT/.claude/scripts/retry-budget.sh"
    if [ -f "$RETRY_SCRIPT" ]; then
        RETRY_CTX=$(bash "$RETRY_SCRIPT" check 2>&1)
        [ $? -eq 2 ] && [ -n "$RETRY_CTX" ] && echo "$RETRY_CTX"
    fi

    # ─── Todo 队列（只当有活跃项时显示） ──────────────────────────
    PENDING=$(grep -cE '\[ \]|\[·\]' "$TODO_FILE" 2>/dev/null); PENDING="${PENDING:-0}"
    if [ -f "$TODO_FILE" ] && [ "$PENDING" -gt 0 ]; then
        echo "[待办: ${PENDING}项]"
        grep -E '\[ \]|\[·\]' "$TODO_FILE" 2>/dev/null | head -5
    fi

    LATEST_EXEC=$(find "$PROJECT_ROOT/$DOC_ROOT" -name "$EXEC_DOC" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
    if [ -n "$LATEST_EXEC" ]; then
        FEATURE=$(echo "$LATEST_EXEC" | sed "s|.*/${DOC_ROOT}/||;s|/${EXEC_DOC}||")
        ACTIVE_STEP=$(grep -E "^##.*🔄|^## Step.*进行中|^##.*in.progress" "$LATEST_EXEC" 2>/dev/null | head -1)
        [ -n "$ACTIVE_STEP" ] && echo "范围: $FEATURE $ACTIVE_STEP"
    fi

    # --- Session 目标锚定（E1 防漂移）---
    HANDOFF_FILE="$PROJECT_ROOT/.omc/state/session-handoff.md"
    if [ -f "$HANDOFF_FILE" ]; then
        HANDOFF_GOAL=$(grep -E '^## Feature:' "$HANDOFF_FILE" 2>/dev/null | head -2 | sed 's/^## //')
        [ -n "$HANDOFF_GOAL" ] && echo "$HANDOFF_GOAL" | head -1
    fi

    # --- E8 会话健康快照 ---
    ERROR_COUNT=0
    CONTRADICTION_COUNT=0
    if [ -f "$PROJECT_ROOT/.omc/state/error-dna.json" ]; then
        ERROR_COUNT=$(python3 -c "
import json
try:
    d = json.load(open('$PROJECT_ROOT/.omc/state/error-dna.json'))
    sigs = d.get('error_signatures', {})
    if isinstance(sigs, dict):
        print(sum(1 for v in sigs.values() if v.get('status') == 'active'))
    else:
        print(0)
except:
    print(0)" 2>/dev/null)
    fi
    if [ -f "$PROJECT_ROOT/.omc/state/contradiction-log.jsonl" ]; then
        CONTRADICTION_COUNT=$(grep -c '"contradiction": true' "$PROJECT_ROOT/.omc/state/contradiction-log.jsonl" 2>/dev/null); CONTRADICTION_COUNT="${CONTRADICTION_COUNT:-0}"
    fi
    # C8 可维护性: 三方漂移检测 — z 脚本存在+yaml 启用但 settings 未注册
    DRIFT_COUNT=0
    HARNESS_YAML="$PROJECT_ROOT/.claude/harness.yaml"
    SETTINGS_JSON="$PROJECT_ROOT/.claude/settings.json"
    if [ -f "$HARNESS_YAML" ] && [ -f "$SETTINGS_JSON" ]; then
        DRIFT_COUNT=$(python3 -c "
import os, re, json
hook_dir = '$PROJECT_ROOT/.claude/hooks'
yaml_path = '$HARNESS_YAML'
settings_path = '$SETTINGS_JSON'
disk_scripts = set(f.replace('.sh', '') for f in os.listdir(hook_dir) if f.endswith('.sh') and os.path.isfile(os.path.join(hook_dir, f)))
yaml_enabled = set()
try:
    with open(yaml_path) as f:
        for line in f:
            m = re.match(r'^hooks_enabled\.(\w+):\s*true', line)
            if m:
                yaml_enabled.add(m.group(1))
except: pass
settings_scripts = set()
try:
    with open(settings_path) as f:
        s = json.load(f)
    for hook_list in ['hooks', 'preToolUse', 'postToolUse', 'preToolUseFailure', 'postToolUseFailure', 'sessionStart', 'userPromptSubmit', 'stop']:
        for hook in s.get(hook_list, []):
            if isinstance(hook, dict) and 'script' in hook:
                name = os.path.basename(hook['script']).replace('.sh', '')
                settings_scripts.add(name)
except: pass
# z = on disk + yaml enabled but missing from settings
zombie = len((disk_scripts & yaml_enabled) - settings_scripts)
# orphan = in settings but missing from disk
orphan = len(settings_scripts - disk_scripts)
print(f'{zombie}+{orphan}')
" 2>/dev/null)
    fi
    # C5 工具生命周期: 追踪工具使用多样性 + 成功率
    TOOL_DIVERSITY=0
    TOOL_ERR_RATE=""
    TOTAL_OPS_FILE="$STATE_DIR/total-ops.txt"
    ERROR_DNA_JSONL="$STATE_DIR/error-dna.jsonl"
    if [ -f "$ERROR_DNA_JSONL" ]; then
        TOOL_DIVERSITY=$(grep -c '"error_type"' "$ERROR_DNA_JSONL" 2>/dev/null); TOOL_DIVERSITY="${TOOL_DIVERSITY:-0}"
    fi
    if [ -f "$TOTAL_OPS_FILE" ]; then
        TOTAL_OPS=$(cat "$TOTAL_OPS_FILE" 2>/dev/null || echo 0)
        if [ "$TOTAL_OPS" -gt 0 ] 2>/dev/null; then
            ERR_RATE=$((TOOL_DIVERSITY * 100 / TOTAL_OPS))
            TOOL_ERR_RATE="${ERR_RATE}%"
        fi
    fi
    echo "健康: 轮$new_count ctx${CTX_PCT:-?}% err$ERROR_COUNT 矛$CONTRADICTION_COUNT z${DRIFT_COUNT:-?} 工具${TOOL_DIVERSITY} err${TOOL_ERR_RATE:-?}"

    echo "═══ ═══"
fi

if [ -f "$FUZZY_CHECK" ]; then
    PROMPT=$(cat "$FUZZY_CHECK" 2>/dev/null)
    HAS_EXPLICIT_TARGET=false
    EXPLICIT_REGEX=$(hc_get "fuzzy_detection.explicit_target_regex" 'Step\s*[0-9]+|rpe/[a-zA-Z_]+|\.go$|\.md$|handler|logic|model|executor')
    if echo "$PROMPT" | grep -qE "$EXPLICIT_REGEX"; then
        HAS_EXPLICIT_TARGET=true
    fi

    # Ghost mode / Unattended mode 豁免：非 normal 模式下"继续""优化"等是合法指令，非模糊指令
    if [ "$(is_mode_active "$STATE_DIR")" != "normal" ]; then
        HAS_EXPLICIT_TARGET=true
    fi

    # 明确目标或长提示 → 清理模糊阻断标记（防止前任残留导致当前误阻断）
    if [ "$HAS_EXPLICIT_TARGET" = true ]; then
        rm -f "$PROJECT_ROOT/.omc/state/.fuzzy-block-active"
    fi

    if [ "$HAS_EXPLICIT_TARGET" = false ]; then
        FUZZY_VERBS=$(hc_get "fuzzy_detection.fuzzy_verbs" "继续 优化 修复 改进 完善 处理一下 看一下 搞一下")
        HAS_FUZZY_VERB=false
        FUZZY_VERB=""
        set -f
        for verb in $FUZZY_VERBS; do
            if echo "$PROMPT" | grep -qF "$verb"; then
                HAS_FUZZY_VERB=true
                FUZZY_VERB="$verb"
                break
            fi
        done
        set +f

        if [ "$HAS_FUZZY_VERB" = true ]; then
            # DF-01: 方向限定词检测 — "从机制上优化"有具体方向，非模糊指令
            # 模式: "从X上/角度/层面/方面" / "针对X" / "关于X" / "在X方面" = 具体方向
            if echo "$PROMPT" | grep -qE '(从.{1,8}(上|角度|层面|方面)|针对.{1,12}|关于.{1,12}|在.{1,8}方面)'; then
                HAS_FUZZY_VERB=false
                FUZZY_VERB=""
            fi
        fi
        if [ "$HAS_FUZZY_VERB" = true ]; then
            # 仅短+无结构化内容的提示才视为模糊指令（长提示含模板/表格是明确指令）
            PROMPT_LEN=${#PROMPT}
            HAS_STRUCTURED=false
            if echo "$PROMPT" | grep -qE '(\|.*\|.*\|.*\||[#]+\s|\*\*|`[^`]+`|---|\d+\.\s+\*\*)'; then
                HAS_STRUCTURED=true
            fi
            if [ "$PROMPT_LEN" -lt 100 ] && [ "$HAS_STRUCTURED" = false ]; then
                # 写模糊阻断标记（C1: fuzzy-block.sh 消费）
                echo "指令含模糊动词'$FUZZY_VERB'。请指定 Step 编号/文件路径/功能名称" > "$PROJECT_ROOT/.omc/state/.fuzzy-block-active"
            fi
            LATEST_EXEC_CHECK=$(find "$PROJECT_ROOT/$DOC_ROOT" -name "$EXEC_DOC" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
            INCOMPLETE_COUNT=0
            if [ -n "$LATEST_EXEC_CHECK" ]; then
                INCOMPLETE_COUNT=$(grep -cE '🔄|⏳|进行中|in.progress' "$LATEST_EXEC_CHECK" 2>/dev/null); INCOMPLETE_COUNT="${INCOMPLETE_COUNT:-0}"
            fi

            # 收集具体上下文：活跃 feature / scope 状态 + git 最近修改
            FEATURES=$(ls "$PROJECT_ROOT/$DOC_ROOT" 2>/dev/null | head -5 | tr '\n' ' ')
            SCOPE_FILE_STATE=""
            if [ -f "$PROJECT_ROOT/.omc/state/current-scope.txt" ]; then
                SCOPE_LINES=$(wc -l < "$PROJECT_ROOT/.omc/state/current-scope.txt" | tr -d ' ')
                SCOPE_FILE_STATE="(scope: ${SCOPE_LINES} entries)"
            fi
            GIT_DIFF_STAT=$(cd "$PROJECT_ROOT" 2>/dev/null && git diff --stat 2>/dev/null | head -3 | paste -sd '; ' -)

            if [ "$INCOMPLETE_COUNT" -gt 1 ]; then
                echo "⚠️ 模糊指令检测: 指令含模糊动词'$FUZZY_VERB'但无明确目标，且有 $INCOMPLETE_COUNT 个活跃 Step。"
                echo "⛔ 停止执行！必须要求用户澄清具体目标 — 不允许猜测或默认推进(§1.6)。"
                echo "可能意图: A.修复阻塞Step B.继续开发进行中Step C.代码优化。请指定具体目标(§1.6)。"
                echo "当前 RPE 实例: $FEATURES $SCOPE_FILE_STATE"
                [ -n "$GIT_DIFF_STAT" ] && echo "最近未提交修改: $GIT_DIFF_STAT"
                echo "建议: 指定文件路径（如 ${FEATURES%% *}/handler.go）或 Step 编号"
            else
                echo "⚠️ 模糊指令检测: 指令含模糊动词'$FUZZY_VERB'但无明确目标。请补充 Step 编号/文件路径/功能名称(§1.6)。"
                echo "⛔ 停止推测！必须先澄清 — 不明确的目标导致方向错误(§1.6)。"
                echo "当前 RPE 实例: $FEATURES $SCOPE_FILE_STATE"
                [ -n "$GIT_DIFF_STAT" ] && echo "最近未提交修改: $GIT_DIFF_STAT"
                echo "建议: /lx-rpe status 查看进度 | 或指定具体文件路径"
            fi
        fi
    fi
fi

# ─── 多层 context window 提示策略 ────────────────────────
# 根据 context 使用率分 4 层注入，每层触发密度不同
# 同一轮只触发最高适用层（低层命中时不再注入高层）
# L0 (<30%) 每15轮: 全量规范刷新（预防性）
# L1 (30-50%) 每10轮: 摘要规范刷新
# L2 (>50% && >20轮) 每5轮: 核心规范锚定（已有复合条件）
# L3 (>80%) 每5轮: 6铁律 + /compact 建议
KNOWLEDGE_MIN_TURNS=$(hc_get "turn_counter.knowledge_inject_min_turns" "20")
INDEX_FILE="$STATE_DIR/token-tracking-index.json"
CTX_PCT=""
CTX_SOURCE=""
if [ $(( new_count % 5 )) -eq 0 ]; then
    # 优先使用 context_monitor.py（读 transcript 真实数据，落后 1 轮但准确）
    MONITOR_SCRIPT="$SCRIPT_DIR/../scripts/context_monitor.py"
    if [ -x "$MONITOR_SCRIPT" ]; then
        MONITOR_OUT=$(python3 "$MONITOR_SCRIPT" 2>/dev/null)
        CTX_PCT=$(echo "$MONITOR_OUT" | python3 -c "import sys,json; print(int(json.load(sys.stdin).get('percentage',0)))" 2>/dev/null)
        CTX_SOURCE=$(echo "$MONITOR_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('source',''))" 2>/dev/null)
    fi
    # 兜底：启发式计数器
    if [ -z "$CTX_PCT" ] || [ "$CTX_PCT" -eq 0 ] 2>/dev/null; then
        if [ -f "$INDEX_FILE" ]; then
            CTX_PCT=$(python3 -c "
import json
try:
    d = json.load(open('$INDEX_FILE'))
    usage = d.get('usage', 0)
    limit = d.get('limit', 200000)
    print(int(usage * 100 / limit)) if limit > 0 else print(0)
except:
    print(0)" 2>/dev/null)
            CTX_SOURCE="heuristic"
        fi
    fi
fi

INJECT_INDEX="$PROJECT_ROOT/.claude/index.md"
INJECT_KERNEL="$PROJECT_ROOT/.claude/kernel.md"
INJECT_ANTI="$PROJECT_ROOT/.claude/anti-patterns.md"

CTX_SOURCE_LABEL=""
if [ "$CTX_SOURCE" = "heuristic" ]; then
    CTX_SOURCE_LABEL=" [估算]"
elif [ -n "$CTX_SOURCE" ]; then
    CTX_SOURCE_LABEL=" [真实]"
fi

if [ -n "$CTX_PCT" ]; then
    # L3: 危机协议 — context > 80%
    if [ "$CTX_PCT" -ge 80 ] 2>/dev/null && [ $(( new_count % 5 )) -eq 0 ]; then
        echo ""
        echo "═══ [轮次 $new_count] 上下文危机 — context ${CTX_PCT}%${CTX_SOURCE_LABEL} ═══"
        echo "【仅 7 铁律】上下文使用率超过 80%，仅保留最低门禁规则："
        echo " 1. 禁止编造：技术断言必须引用 file:line"
        echo " 2. 用户裁定：验收/选型/冲突由用户决定，AI 不可自判"
        echo " 3. 证据门禁：说'完成'前必须有 VERIFIED 证据"
        echo " 4. Git 门禁：commit/push 必须先报告，等用户批准"
        echo " 5. 范围冻结：只改当前任务文件，发现的问题记 TODO"
        echo " 6. 隐私防线：禁止读取 .env/私钥"
        echo " 7. 断言真实：百分比/评分必须有行业标准来源"
        echo ""
        echo "💡 建议运行 /compact 释放上下文空间后继续。"
        echo "═══ 危机协议完成 ═══"

    # L2: 核心锚定 — context > 50% 且轮数 > 阈值
    elif [ "$CTX_PCT" -ge 50 ] 2>/dev/null && [ "$new_count" -gt "$KNOWLEDGE_MIN_TURNS" ]; then
        echo ""
        echo "═══ [轮次 $new_count] 规范漂移检测 — context ${CTX_PCT}% > 50% ═══"
        echo "【规范重新锚定】上下文使用率超出阈值，重新注入项目规范。"
        if [ -f "$INJECT_INDEX" ]; then
            echo ""
            grep -E '^\| \#' "$INJECT_INDEX" 2>/dev/null | head -15
            echo ""
            grep -E '^\|`[a-z]' "$INJECT_INDEX" 2>/dev/null | head -8
        fi
        echo ""
        echo "═══ 规范重新锚定完毕 ═══"

    # L1: 摘要刷新 — context 30-50%，每 10 轮预防性注入
    elif [ "$CTX_PCT" -ge 30 ] 2>/dev/null && [ $(( new_count % 10 )) -eq 0 ]; then
        echo ""
        echo "═══ [轮次 $new_count] 规范预防刷新 — context ${CTX_PCT}% ═══"
        echo "【上下文摘要】当前使用率中等，注入内核关键规则："
        if [ -f "$INJECT_KERNEL" ]; then
            echo "--- 架构铁律 ---"
            grep -E '^## |^-\s*\*\*' "$INJECT_KERNEL" 2>/dev/null | head -10
        fi
        echo ""
        echo "═══ 预防刷新完毕 ═══"

    # L0: 全量预防 — context < 30%，每 15 轮全量注入
    elif [ $(( new_count % 15 )) -eq 0 ] && [ "$new_count" -gt 5 ]; then
        echo ""
        echo "═══ [轮次 $new_count] 全量规范预防注入 — context ${CTX_PCT}% ═══"
        echo "【全量刷新】早期预防，确保规范始终锚定。"
        if [ -f "$INJECT_INDEX" ]; then
            grep -E '^\|#' "$INJECT_INDEX" 2>/dev/null | head -20
        fi
        echo ""
        echo "═══ 全量注入完毕 ═══"
    fi
fi

exit 0
