#!/usr/bin/env bash
# claim-lint.sh — 扫描营销文档中的高风险关键词
# Schema: AC-10.7
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MARKETING_DIR="$PROJECT_ROOT/docs/marketing"

# 高风险关键词列表
KEYWORDS=(
    "行业独创"
    "首创"
    "独创"
    "唯一"
    "没有对手"
    "绝对"
    "终极"
    "100%"
    "完全可见"
    "自评分"
    "毫无疑问"
    "本质区别"
    "无可争议"
    "军工级"
    "满分"
    "保险价值"
)

EXIT_CODE=0
FILES=("$MARKETING_DIR"/*.md)

for file in "${FILES[@]}"; do
    [ -f "$file" ] || continue
    for keyword in "${KEYWORDS[@]}"; do
        if grep -n "$keyword" "$file" 2>/dev/null; then
            EXIT_CODE=1
        fi
    done
done

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "✅ claim-lint: 全部 $MARKETING_DIR/*.md 无高风险关键词命中"
else
    echo "⚠️ claim-lint: 高风险关键词命中，建议替换为中性表述"
fi
exit $EXIT_CODE
