#!/usr/bin/env bash
# doc-sync-check.sh — 文档-代码一致性验证
# 扫描 docs/ 下 .md 文件中 [已验证: path:line] 格式的引用
# 检查 path 是否指向存在的文件
#
# Usage:
#   bash .claude/scripts/doc-sync-check.sh
#   bash .claude/scripts/doc-sync-check.sh --verbose

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DOCS_DIR="$ROOT/docs"
ISSUES=0
VERBOSE=false

if [[ "${1:-}" == "--verbose" ]]; then
    VERBOSE=true
fi

while IFS=':' read -r file line_num rest; do
    # Extract file path from [已验证: path:line] or [已验证: path]
    FILE_REF=$(echo "$rest" | sed -n 's/.*\[已验证: *\([^: ]*\)[[:space:]]*\([^]]*\)\].*/\1/p')

    if [ -z "$FILE_REF" ]; then
        continue
    fi

    # Remove any trailing content after ] that might have been captured
    FILE_REF="${FILE_REF%]*}"

    # Handle paths relative to ROOT or absolute paths
    if [[ "$FILE_REF" == /* ]]; then
        TARGET="$FILE_REF"
    else
        TARGET="$ROOT/$FILE_REF"
    fi

    if [ ! -f "$TARGET" ]; then
        echo "❌ 断链: $FILE_REF (引用在: $file:$line_num)"
        ISSUES=$((ISSUES + 1))
    elif $VERBOSE; then
        echo "✓ $FILE_REF ($file:$line_num)"
    fi
done < <(grep -rn '\[已验证:' "$DOCS_DIR" --include="*.md" 2>/dev/null || true)

if [ "$ISSUES" -eq 0 ]; then
    echo ""
    echo "✅ doc-sync-check: 全部引用有效"
    exit 0
else
    echo ""
    echo "⚠️  doc-sync-check: $ISSUES 个问题"
    exit 1
fi
