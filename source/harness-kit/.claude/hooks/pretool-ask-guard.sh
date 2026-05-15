#!/usr/bin/env bash
# pretool-ask-guard.sh — PreToolUse:AskUserQuestion — 哲学先行门禁，拦截"多此一问"
# Role: 在 AI 问人之前检查哲学是否已覆盖，已覆盖则阻断提问，强制 AI 直接执行
# 哲学 #5(以人为本): 减少无效打断
# 哲学 #6(0信任): AI 必须证明自己查过哲学

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_ask_guard" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

# 提取 AskUserQuestion 的 questions 字段
QUESTIONS=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    qs = d.get('tool_input', {}).get('questions', [])
    texts = [q.get('question', '') for q in qs]
    print('|'.join(texts))
except:
    pass" 2>/dev/null)

[ -z "$QUESTIONS" ] && { echo '{"continue": true}'; exit 0; }

# ── 模式匹配：不需要问人的问题 ──
# 这些是"行动确认"而非"决策请求"——哲学已覆盖，AI 应直接执行
UNNECESSARY_PATTERNS=(
    # 中文：行动确认型 = AI 已经知道该做什么，在请求许可
    "需要我.*(吗|么)[？?]?"   # 需要我提交吗？需要我同步吗？
    "要我.*(吗|么)[？?]?"     # 要我开始吗？要我继续吗？
    "要不要"                   # 要不要跑 package-release？
    "是否可以"                 # 是否可以开始执行？
    "是否.*(继续|执行|开始)"    # 是否继续？是否执行？
    "我可以.*(吗|么)"          # 我可以开始修了吗？
    "你希望我"                 # 你希望我提交吗？
    "你想我"                   # 你想我继续吗？
    "我应该"                   # 我应该先做A还是先做B？
    "先.*还是"                 # 先修这个还是那个？
    # 英文
    "Should I "               # Should I commit?
    "Do you want me to"        # Do you want me to start?
    "Would you like me to"     # Would you like me to continue?
    "Can I "                  # Can I proceed?
    "Shall I "                # Shall I run X?
)

DETECTED=""
for pattern in "${UNNECESSARY_PATTERNS[@]}"; do
    if echo "$QUESTIONS" | grep -qiE "$pattern" 2>/dev/null; then
        DETECTED="$DETECTED|$pattern"
    fi
done

[ -z "$DETECTED" ] && { echo '{"continue": true}'; exit 0; }

# ── 阻断：告诉 AI 直接执行，不要问 ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 检测自主模式（goal/ghost 下不阻断，仅记录）
MODE=$(is_mode_active "$PROJECT_ROOT/.omc/state")
if [ "$MODE" != "normal" ]; then
    echo "[pretool-ask-guard] ${MODE} mode: 检测到多此一问，已记录（不阻断）" >&2
    echo "   匹配: $DETECTED" >&2
    echo '{"continue": true}'
    exit 0
fi

cat >&2 <<EOF

🚫 [哲学先行门禁] 检测到"多此一问"！

你的问题: "$(echo "$QUESTIONS" | head -c 200)"

铁律 #8（哲学先行）：问人前先过哲学 7 条。
哲学已覆盖此问题 → 直接执行，不要问。

匹配模式: $DETECTED

正确做法: 标注 [哲学先行: #N→执行] 后直接行动，结果附证据报告。
EOF

echo '{"continue": false, "reason": "铁律 #8 哲学先行：此问题哲学已覆盖，直接执行不打扰人。标注 [哲学先行: #N→action] 后行动。"}'
exit 0
