#!/bin/bash
# pretool-rule-anchor.sh — PreToolUse:Edit|Write — 长对话防漂移，高轮次时注入锚定规则
# Role: 长对话防漂移，高轮次时注入锚定规则

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_rule_anchor" || exit 0

# 复用 harness_config.sh 已计算好的 PROJECT_ROOT（与其他所有 hook 一致）
PROJECT_ROOT="$(hc_project_root)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
TURNS_FILE="$STATE_DIR/session-turns.json"

# 读取配置
ANCHOR_THRESHOLD=$(hc_get "rule_anchor.turn_threshold" "15")
ANCHOR_INTERVAL=$(hc_get "rule_anchor.interval" "5")

# 读取当前轮次
current_turn=0
if [ -f "$TURNS_FILE" ]; then
    if command -v jq &>/dev/null; then
        current_turn=$(jq -r '.count // 0' "$TURNS_FILE" 2>/dev/null || echo 0)
    else
        current_turn=$(grep -o '"count"[[:space:]]*:[[:space:]]*[0-9]*' "$TURNS_FILE" 2>/dev/null | sed 's/.*:[[:space:]]*//' | head -1)
        [ -z "$current_turn" ] && current_turn=0
    fi
fi
if ! [[ "$current_turn" =~ ^[0-9]+$ ]]; then
    current_turn=0
fi

# 轮次未超阈值 → 静默放行
if [ "$current_turn" -lt "$ANCHOR_THRESHOLD" ]; then
    exit 0
fi

# 超过阈值，但不是每轮都提醒，按 ANCHOR_INTERVAL 间隔触发
# 在 [THRESHOLD, THRESHOLD+INTERVAL, THRESHOLD+2*INTERVAL, ...] 各轮提醒
offset=$(( current_turn - ANCHOR_THRESHOLD ))
if [ "$ANCHOR_INTERVAL" -gt 0 ] && [ $(( offset % ANCHOR_INTERVAL )) -ne 0 ]; then
    exit 0
fi

# ─── 检测漂移信号词（顺手/另外/同时也改了/顺便）──────────────────
LAST_PROMPT="$STATE_DIR/.last-user-prompt"
DRIFT_DETECTED=false
DRIFT_WORD=""
if [ -f "$LAST_PROMPT" ]; then
    for word in "顺手" "顺便" "另外也" "同时也" "顺带" "捎带"; do
        if grep -qF "$word" "$LAST_PROMPT" 2>/dev/null; then
            DRIFT_DETECTED=true
            DRIFT_WORD="$word"
            break
        fi
    done
fi

# ─── 组装提醒内容 ──────────────────────────────────────────────
if [ "$DRIFT_DETECTED" = true ]; then
    CONTEXT="⚠️ [第${current_turn}轮·漂移预警] 检测到范围扩展词「${DRIFT_WORD}」。范围冻结规则：只改当前任务文件，额外发现的问题记 TODO，不顺手修。铁律复习：①断言需引用file:line ②完成前需VERIFIED证据 ③git操作需用户批准 ④范围冻结 ⑤最多3轮修复"
else
    CONTEXT="📌 [第${current_turn}轮·规则锚定] 长会话规则提醒（每${ANCHOR_INTERVAL}轮触发）：①禁止编造(需file:line) ②完成前需VERIFIED证据 ③git写操作需用户批准 ④只改当前任务范围 ⑤同一问题最多修3轮→BLOCKED ⑥禁用'应该是/可能/通常'"
fi

# 输出 JSON（Claude Code hook 标准格式）
printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "%s"}}\n' \
    "$(echo "$CONTEXT" | sed 's/"/\\\"/g')"
