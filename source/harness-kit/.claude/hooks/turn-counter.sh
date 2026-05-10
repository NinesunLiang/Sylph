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
tee "$FUZZY_CHECK" > /dev/null

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
    echo "═══ [轮次 $new_count] Todo 队列同步 + 铁律提醒 ═══"

    # ─── 铁律摘要（防漂移核心）─────────────────────────────────────
    echo ""
    echo "【铁律提醒·第 ${new_count} 轮·始终生效】"
    echo " 1. 禁止编造：技术断言必须引用 file:line，找不到→说'需要验证'"
    echo " 2. 证据门禁：说'完成'前必须有 VERIFIED 证据（L1/L2），否则不得声明"
    echo " 3. Git 门禁：commit/push 必须先报告，等用户明确批准后才能执行"
    echo " 4. 范围冻结：只改当前任务文件，顺手发现的问题记 TODO 不修"
    echo " 5. 修复上限：同一问题最多修 3 轮，第 3 轮失败→BLOCKED 等用户指令"
    echo " 6. 禁用词：禁止用'应该是/可能/通常'做技术断言，必须标置信度"
    echo ""

    # ─── Todo 队列 ────────────────────────────────────────────────
    if [ -f "$TODO_FILE" ]; then
        echo "[当前 Todo 队列（max ${TODO_MAX}，FIFO，[x]=完成 [·]=进行中 [ ]=待处理）]"
        cat "$TODO_FILE"
    else
        echo "[Todo 队列未初始化，请创建 ${TODO_FILE}]"
        echo "格式：每行一条，形如："
        echo " - [ ] $(date +%Y-%m-%dT%H:%M) 待处理事项描述"
        echo " - [·] $(date +%Y-%m-%dT%H:%M) 进行中事项描述"
        echo " - [x] $(date +%Y-%m-%dT%H:%M) 已完成事项描述"
    fi

    LATEST_EXEC=$(find "$PROJECT_ROOT/$DOC_ROOT" -name "$EXEC_DOC" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
    if [ -n "$LATEST_EXEC" ]; then
        FEATURE=$(echo "$LATEST_EXEC" | sed "s|.*/${DOC_ROOT}/||;s|/${EXEC_DOC}||")
        ACTIVE_STEP=$(grep -E "^##.*🔄|^## Step.*进行中|^##.*in.progress" "$LATEST_EXEC" 2>/dev/null | head -1)
        [ -n "$ACTIVE_STEP" ] && echo "[当前范围] feature=$FEATURE $ACTIVE_STEP"
    fi

    echo ""
    echo "⚡ 请检查并更新 ${TODO_FILE}：已完成的 [·]→[x]，待处理的 [ ]→[·]。"
    echo " 使用 Edit 工具修改文件后继续工作。"
    echo "═══ 规则重新锚定完毕，继续当前任务 ═══"
fi

if [ -f "$FUZZY_CHECK" ]; then
    PROMPT=$(cat "$FUZZY_CHECK" 2>/dev/null)
    HAS_EXPLICIT_TARGET=false
    EXPLICIT_REGEX=$(hc_get "fuzzy_detection.explicit_target_regex" 'Step\s*[0-9]+|rpe/[a-zA-Z_]+|\.go$|\.md$|handler|logic|model|executor')
    if echo "$PROMPT" | grep -qE "$EXPLICIT_REGEX"; then
        HAS_EXPLICIT_TARGET=true
    fi

    if [ "$HAS_EXPLICIT_TARGET" = false ]; then
        FUZZY_VERBS=$(hc_get "fuzzy_detection.fuzzy_verbs" "继续 优化 修复 改进 完善 处理一下 看一下 搞一下")
        HAS_FUZZY_VERB=false
        FUZZY_VERB=""
        for verb in $FUZZY_VERBS; do
            if echo "$PROMPT" | grep -qF "$verb"; then
                HAS_FUZZY_VERB=true
                FUZZY_VERB="$verb"
                break
            fi
        done

        if [ "$HAS_FUZZY_VERB" = true ]; then
            LATEST_EXEC_CHECK=$(find "$PROJECT_ROOT/$DOC_ROOT" -name "$EXEC_DOC" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
            INCOMPLETE_COUNT=0
            if [ -n "$LATEST_EXEC_CHECK" ]; then
                INCOMPLETE_COUNT=$(grep -cE '🔄|⏳|进行中|in.progress' "$LATEST_EXEC_CHECK" 2>/dev/null || echo 0)
            fi
            if [ "$INCOMPLETE_COUNT" -gt 1 ]; then
                echo "⚠️ 模糊指令检测: 指令含模糊动词'$FUZZY_VERB'但无明确目标，且有 $INCOMPLETE_COUNT 个活跃 Step。"
                echo "可能意图: A.修复阻塞Step B.继续开发进行中Step C.代码优化。请指定具体目标(§1.6)。"
            else
                echo "⚠️ 模糊指令检测: 指令含模糊动词'$FUZZY_VERB'但无明确目标。请补充 Step 编号/文件路径/功能名称(§1.6)。"
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
if [ -f "$INDEX_FILE" ] && [ $(( new_count % 5 )) -eq 0 ]; then
    CTX_PCT=$(python3 -c "
import json
try:
    d = json.load(open('$INDEX_FILE'))
    usage = d.get('usage', 0)
    limit = d.get('limit', 200000)
    print(int(usage * 100 / limit)) if limit > 0 else print(0)
except:
    print(0)" 2>/dev/null)
fi

INJECT_INDEX="$PROJECT_ROOT/.claude/index.md"
INJECT_KERNEL="$PROJECT_ROOT/.claude/kernel.md"
INJECT_ANTI="$PROJECT_ROOT/.claude/anti-patterns.md"

if [ -n "$CTX_PCT" ]; then
    # L3: 危机协议 — context > 80%
    if [ "$CTX_PCT" -ge 80 ] 2>/dev/null && [ $(( new_count % 5 )) -eq 0 ]; then
        echo ""
        echo "═══ [轮次 $new_count] 上下文危机 — context ${CTX_PCT}% ═══"
        echo "【仅 6 铁律】上下文使用率超过 80%，仅保留最低门禁规则："
        echo " 1. 禁止编造：技术断言必须引用 file:line"
        echo " 2. 证据门禁：说'完成'前必须有 VERIFIED 证据"
        echo " 3. Git 门禁：commit/push 必须先报告，等用户批准"
        echo " 4. 范围冻结：只改当前任务文件，发现的问题记 TODO"
        echo " 5. 修复上限：同一问题最多修 3 轮"
        echo " 6. 禁用词：禁止用'应该是/可能/通常'做技术断言"
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
