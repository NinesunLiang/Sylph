#!/usr/bin/env bash
# pre-ask-guard.sh — PreToolUse:AskUserQuestion — 问人前强制过决策链四层评估
# Role: 拦截 AskUserQuestion，检查决策链是否已有答案。能自主决策则阻断提问，降低人类心智负担。
#
# 决策链（自上而下）：
#   Philosophy (7条) → Iron Rules (8条) → Existing Practices (claude-next.md)
#   → Behavior Patterns (behavior-patterns.md) → AI 自判
# 以上全部穷尽仍不确定 → 才允许问人

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "pre_ask_guard" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"

# 提取所有问题文本
QUESTIONS=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    qs = d.get('tool_input', {}).get('questions', [])
    for q in qs:
        print(q.get('question', ''))
except: pass" 2>/dev/null)

[ -z "$QUESTIONS" ] && { echo '{"continue": true}'; exit 0; }

# ─── 自主模式: 一律阻断 ──────────────────────────────────────
# 哲学 #6 (0信任): 自主模式下 AI 不得问人。无法决策的走 blocked-human。
MODE=$(is_mode_active "$PROJECT_ROOT/.omc/state" 2>/dev/null || echo "normal")
if [ "$MODE" != "normal" ]; then
    printf '%b\n' "🛑 [pre-ask-guard] 自主模式(${MODE})活跃 — 所有问题禁止问人" >&2
    printf '%b\n' "   问题数: ${TOTAL_COUNT} → 请走决策链裁决: 哲学(7条) → 铁律(8条) → 现状 → Oracle → AI自判" >&2
    printf '%b\n' "   无法确定 → 记录: lx-${MODE} blocked-human \"问题\" \"AI推荐\" \"依据\" → 人在退出报告中审阅" >&2
    flywheel_event "pre_ask_guard" "blocked_autonomous_mode" "P1" "mode=$MODE questions=${TOTAL_COUNT}" || true
    printf '{"continue":false,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[pre-ask-guard] 自主模式(%s)活跃，禁止问人。所有问题走决策链: 哲学(7条) → 铁律(8条) → 现状 → Oracle → AI自判。无法确定的记录 lx-%s blocked-human 人在退出报告中审阅。"}}\n' "$MODE" "$MODE"
    exit 2
fi

# ─── 决策链文件 ──────────────────────────────────────────────
PHILOSOPHY_MD="$PROJECT_ROOT/AGENTS.md"
IRON_RULES="$PROJECT_ROOT/AGENTS.md"
EXISTING_PRACTICES="$PROJECT_ROOT/.claude/claude-next.md"
BEHAVIOR_PATTERNS="$PROJECT_ROOT/.claude/behavior-patterns.md"
ANTI_PATTERNS="$PROJECT_ROOT/.claude/anti-patterns.md"
KERNEL_MD="$PROJECT_ROOT/.claude/kernel.md"

# ─── 逐问题检查 ──────────────────────────────────────────────
RESOLVABLE_COUNT=0
TOTAL_COUNT=0
HINTS=""

while IFS= read -r question; do
    [ -z "$question" ] && continue
    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    # 提取关键词（取前 5 个有意义的词，排除停用词）
    KEYWORDS=$(echo "$question" | ${PYTHON_BIN:-python3} -c "
import sys, re
q = sys.stdin.read().strip()
# Extract meaningful keywords (Chinese: 2+ chars, English: 3+ chars)
words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', q)
# Remove stop words
stop = {'what','how','when','where','which','should','could','would','the','and','for','this','that','with','from','your','have','been','请','是否','需要','应该','可以','什么','如何','怎么','为什么','还是','或者','这个','那个','已经','可能','还是说','我想','想知道','如果'}
words = [w for w in words if w.lower() not in stop]
print('|'.join(words[:5]))
" 2>/dev/null)

    [ -z "$KEYWORDS" ] && continue

    # 搜索决策链文件（从 Philosophy 层开始）
    MATCHED_LAYER=""
    MATCHED_LINE=""

    for layer_file in "$PHILOSOPHY_MD" "$KERNEL_MD" "$ANTI_PATTERNS" "$EXISTING_PRACTICES" "$BEHAVIOR_PATTERNS"; do
        [ ! -f "$layer_file" ] && continue
        IFS='|' read -ra KW_ARRAY <<< "$KEYWORDS"
        for kw in "${KW_ARRAY[@]}"; do
            [ ${#kw} -lt 2 ] && continue
            # grep for keyword in decision file, skip comments/headings
            match=$(grep -in "$kw" "$layer_file" 2>/dev/null | grep -v '^[[:space:]]*#' | grep -v '^[[:space:]]*> ' | head -1)
            if [ -n "$match" ]; then
                MATCHED_LAYER=$(basename "$layer_file")
                MATCHED_LINE="$match"
                break 2
            fi
        done
    done

    if [ -n "$MATCHED_LAYER" ]; then
        RESOLVABLE_COUNT=$((RESOLVABLE_COUNT + 1))
        LAYER_NAME=""
        case "$MATCHED_LAYER" in
            AGENTS.md) LAYER_NAME="哲学/铁律层" ;;
            kernel.md) LAYER_NAME="铁律/执行内核层" ;;
            anti-patterns.md) LAYER_NAME="反模式层" ;;
            claude-next.md) LAYER_NAME="项目惯例层" ;;
            behavior-patterns.md) LAYER_NAME="行为模式层" ;;
            *) LAYER_NAME="$MATCHED_LAYER" ;;
        esac
        HINTS="$HINTS\n🟢 「${question:0:60}...」→ ${LAYER_NAME} 已有覆盖: ${MATCHED_LINE%%:*}:${MATCHED_LINE#*:}"
    else
        HINTS="$HINTS\n🔴 「${question:0:60}...」→ 决策链无覆盖，需人类裁决"
    fi
done <<< "$QUESTIONS"

# ─── 判定 ──────────────────────────────────────────────────
if [ "$RESOLVABLE_COUNT" -eq "$TOTAL_COUNT" ] && [ "$TOTAL_COUNT" -gt 0 ]; then
    # 全部可自主决策 → 阻断提问，输出决策依据
    printf '%b\n' "🧠 [pre-ask-guard] 决策链已覆盖全部 ${TOTAL_COUNT} 个问题 — 无需问人${HINTS}" >&2
    flywheel_event "pre_ask_guard" "blocked_all_resolvable" "P1" || true
    # 阻断：输出决策链引用，AI 应标注 [哲学先行: #N→action] 后直接执行
    printf '{"continue":false,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[pre-ask-guard] 全部 %d 个问题决策链已有答案。请标注 [哲学先行: #N→action] 后直接执行，不必问人。%s"}}\n' "$TOTAL_COUNT" "$(printf '%b' "$HINTS" | ${PYTHON_BIN:-python3} -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)"
    exit 2
elif [ "$RESOLVABLE_COUNT" -gt 0 ]; then
    # 部分可自主 → 软提示，不阻断
    printf '%b\n' "💡 [pre-ask-guard] ${RESOLVABLE_COUNT}/${TOTAL_COUNT} 个问题决策链可覆盖${HINTS}" >&2
    flywheel_event "pre_ask_guard" "partial_hint" "P2" || true
    echo '{"continue": true}'
    exit 0
else
    # 全部不确定 → 放行，这是真正需要人类的问题
    flywheel_event "pre_ask_guard" "passed_genuine" "P2" || true
    echo '{"continue": true}'
    exit 0
fi
