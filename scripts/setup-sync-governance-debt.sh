#!/bin/bash
# 治理债务修复: 7个skill版本同步
set -e
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
# Cross-platform Python resolution (DG-105)
[ -f ".claude/hooks/harness_config.sh" ] && source ".claude/hooks/harness_config.sh" 2>/dev/null || true
VER=$(${PYTHON_BIN:-python3} -c "import json;print(json.load(open('VERSION.json'))['version'])")
echo "Target version: $VER"

SKILLS="lx-dogfood lx-oma-split lx-oma-hier lx-oma-gov lx-oma-orch lx-stepwise lx-sync"

for skill in $SKILLS; do
    SKILL_MD="$PROJECT/.claude/skills/$skill/SKILL.md"
    SRC_MD="$PROJECT/source/lx-skills-v5/.claude/skills/$skill/SKILL.md"

    if [ -f "$SKILL_MD" ]; then
        # Replace old harness_version pattern with current version
        sed -i '' "s/harness_version: \".*\"/harness_version: \"$VER\"/" "$SKILL_MD" 2>/dev/null || \
        sed -i "s/harness_version: \".*\"/harness_version: \"$VER\"/" "$SKILL_MD"
        echo "  root: $skill → $VER"
    fi

    if [ -f "$SRC_MD" ]; then
        sed -i '' "s/harness_version: \".*\"/harness_version: \"$VER\"/" "$SRC_MD" 2>/dev/null || \
        sed -i "s/harness_version: \".*\"/harness_version: \"$VER\"/" "$SRC_MD"
        echo "  source: $skill → $VER"
    fi
done

echo "Done. Verify:"
for skill in $SKILLS; do
    grep "harness_version" "$PROJECT/.claude/skills/$skill/SKILL.md" 2>/dev/null
done
