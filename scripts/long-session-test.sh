#!/usr/bin/env bash
# long-session-test.sh — 20轮会话规则退化检测
# 用法: bash scripts/long-session-test.sh [轮数]
# 输出: 早期vs后期 flywheel blocked事件对比

set -euo pipefail
N="${1:-20}"
FW="$HOME/.claude/flywheel.log"
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== 长会话测试 ${N}轮 ==="
grep pretool_rules_inject "$PROJECT/.claude/harness.yaml" | head -1

FW_START=$(wc -l < "$FW")

for i in $(seq 1 "$N"); do
    cat "$PROJECT/VERSION.json" > /dev/null 2>&1 || true
    ls "$PROJECT/.claude/hooks/" > /dev/null 2>&1 || true
    echo "$i" > "$PROJECT/tmp/turn-$i.txt" 2>/dev/null || true
    printf "."
done
echo ""

FW_END=$(wc -l < "$FW")
NEW=$((FW_END - FW_START))
HALF=$((NEW / 2))

EARLY=$(tail -n "$NEW" "$FW" | head -n "$HALF" | grep -c "blocked" || echo 0)
LATE=$(tail -n "$NEW" "$FW" | tail -n "$HALF" | grep -c "blocked" || echo 0)

echo "飞轮新增: $NEW events"
echo "早期违规: $EARLY  后期违规: $LATE"

if [ "$LATE" -gt "$EARLY" ]; then
    echo "⚠️ 后期退化: +$((LATE - EARLY)) (SessionStart规则遗忘,需每轮锚定)"
else
    echo "✅ 无退化"
fi

rm -f "$PROJECT/tmp/turn-"*.txt 2>/dev/null || true
