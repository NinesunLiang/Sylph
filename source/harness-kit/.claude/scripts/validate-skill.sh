#!/usr/bin/env bash
# validate-skill.sh — Skill 原子化合规性校验入口
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# 委托给 lx-validate-skill/scripts/validate_skill.py 执行
# 保留为独立脚本以兼容 lx-validate-skill/SKILL.md 中的引用
#
# Usage:
#   bash .claude/scripts/validate-skill.sh          # 校验所有 skill
#   bash .claude/scripts/validate-skill.sh lx-{name} # 校验单个 skill

set -euo pipefail

SKILLS_DIR=".claude/skills"
VALIDATOR="$SKILLS_DIR/lx-validate-skill/scripts/validate_skill.py"

if [ ! -f "$VALIDATOR" ]; then
  echo "❌ 校验脚本不存在: $VALIDATOR"
  echo "请确保 lx-validate-skill 已正确安装"
  exit 1
fi

if [ $# -eq 0 ]; then
  for skill_dir in "$SKILLS_DIR"/lx-*/; do
    skill_name=$(basename "$skill_dir")
    set +e
    ${PYTHON_BIN:-python3} "$VALIDATOR" --skill "$skill_name" --skills-dir "$SKILLS_DIR"
    set -e
    echo "---"
  done
else
  ${PYTHON_BIN:-python3} "$VALIDATOR" --skill "$1" --skills-dir "$SKILLS_DIR"
fi
