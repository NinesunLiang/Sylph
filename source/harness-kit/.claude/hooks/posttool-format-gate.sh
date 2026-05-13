#!/usr/bin/env bash
# posttool-format-gate.sh — PostToolUse:TaskUpdate — 以人为本输出格式门禁（哲学 #5 物化）
# Role: 检查任务输出是否符合"以人为本"原则：有方向感、结构化、认知负担低
# 哲学 #5：以人为本 — 心智负担最小化，交互人性化，操纵感+方向感强

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_output_format" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 模式检测: ghost/goal 模式下跳过
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" != "normal" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 解析 TaskUpdate 响应的 result 字段
if command -v jq &>/dev/null; then
    RESULT=$(echo "$INPUT" | jq -r '.tool_response.result // empty' 2>/dev/null)
else
    RESULT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_response', {}).get('result', ''))
except:
    pass" 2>/dev/null)
fi

[ -z "$RESULT" ] && { echo '{"continue": true}'; exit 0; }

# #5 质量检查：方向感指标
HAS_DIRECTION=false
HAS_STRUCTURE=false
HAS_SUMMARY=false

# 检查方向感：是否有下一步/建议/行动项
if echo "$RESULT" | grep -qiE '下一步|下一[步個]|建议|推荐|next|suggest|recommend|you can|you should|try|action|步骤|你可以'; then
    HAS_DIRECTION=true
fi

# 检查结构化：是否有标题/列表/编号（行首）
if echo "$RESULT" | grep -qE '^#{1,4}\s|^[-*]\s|^\d+\.\s'; then
    HAS_STRUCTURE=true
fi

# 检查摘要：是否有总结/结论/概览
if echo "$RESULT" | grep -qiE '总结|摘要|概括|综上所述|overview|summary|in short|to summarize|conclusion'; then
    HAS_SUMMARY=true
fi

# 构建附加上下文（软门禁：提醒 AI 但不阻断）
HINTS=""
[ "$HAS_DIRECTION" = false ] && HINTS="${HINTS}- 欠缺方向感：建议在回复中给出下一步/建议/行动项\n"
[ "$HAS_STRUCTURE" = false ] && HINTS="${HINTS}- 欠缺结构化：建议用标题/列表/编号使信息更易消化\n"
[ "$HAS_SUMMARY" = false ] && HINTS="${HINTS}- 欠缺摘要：长回复前提供一句话总结\n"

if [ -n "$HINTS" ]; then
    printf '{"continue":true,"hookSpecificOutput":{"additionalContext":"📋 #5 以人为本 — 输出格式反馈:\n%s"}}\n' "$HINTS"
    exit 0
fi

echo '{"continue": true}'
exit 0
