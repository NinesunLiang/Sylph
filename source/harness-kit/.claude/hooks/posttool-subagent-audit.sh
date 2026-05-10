#!/usr/bin/env bash
# posttool-subagent-audit.sh — PostToolUse:Task — 子 agent 执行后审计 content 用量，超限告警
# Role: 子 agent 执行后审计 content 用量，超限告警

source "$(dirname "$0")/harness_config.sh"
hc_enabled "subagent_audit" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
    AGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)
    CONTENT_LEN=$(echo "$INPUT" | jq -r '.tool_response.content // empty' 2>/dev/null | wc -c | tr -d ' ')
else
    TOOL_NAME=""
    AGENT_TYPE=""
    CONTENT_LEN="0"
fi

# 只处理 Task 工具
if [ "$TOOL_NAME" != "Task" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 判断是否为危险类型
DANGEROUS_TYPES=$(hc_get "subagent_guard.dangerous_types" "executor designer scientist")
IS_DANGEROUS=false
set -f
for dtype in $DANGEROUS_TYPES; do
    case "$AGENT_TYPE" in
        *${dtype}*) IS_DANGEROUS=true; break ;;
    esac
done
set +f

# 安全 agent 不统计
if [ "$IS_DANGEROUS" = false ]; then
    echo '{"continue": true}'
    exit 0
fi

# 记录到 subagent-usage.jsonl 供后续分析
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
USAGE_LOG="$STATE_DIR/subagent-usage.jsonl"
mkdir -p "$STATE_DIR"

# 简单启发：CONTENT_LEN 显著偏大（>50KB）视为高消耗
HIGH_USAGE_THRESHOLD=$(hc_get "subagent_guard.high_usage_threshold_bytes" "51200")
IS_HIGH=false
if [ "$CONTENT_LEN" -gt "$HIGH_USAGE_THRESHOLD" ] 2>/dev/null; then
    IS_HIGH=true
fi

TS=$(date +%s)
printf '{"ts":%s,"agent":"%s","content_bytes":%s,"high_usage":%s}\n' \
    "$TS" "$AGENT_TYPE" "$CONTENT_LEN" "$IS_HIGH" >> "$USAGE_LOG"

# 日志轮转（>512KB 切档）
if [ -f "$USAGE_LOG" ]; then
    SIZE=$(wc -c < "$USAGE_LOG" | tr -d ' ')
    if [ "$SIZE" -gt 524288 ] 2>/dev/null; then
        mv "$USAGE_LOG" "${USAGE_LOG}.1"
        touch "$USAGE_LOG"
    fi
fi

# 高用量 → 写 flywheel P0 事件，下次 SessionStart 告警
if [ "$IS_HIGH" = true ]; then
    FLYWHEEL_BUF="$HOME/.claude/flywheel-buffer.jsonl"
    mkdir -p "$(dirname "$FLYWHEEL_BUF")"
    printf '{"ts":%s,"event":"subagent_high_usage","level":"P0","project":"%s","agent":"%s","content_bytes":%s}\n' \
        "$TS" "$(basename "$PROJECT_ROOT")" "$AGENT_TYPE" "$CONTENT_LEN" >> "$FLYWHEEL_BUF"

    MSG=$(printf '[Subagent Audit] %s 返回 %d 字节（>%d 高用量阈值）。已记入 flywheel P0 事件，下次 SessionStart 会告警。如需调整阈值改 harness.yaml subagent_guard.high_usage_threshold_bytes' "$AGENT_TYPE" "$CONTENT_LEN" "$HIGH_USAGE_THRESHOLD")
    printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$MSG"
    exit 0
fi

echo '{"continue": true}'
exit 0
