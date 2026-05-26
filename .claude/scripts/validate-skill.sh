#!/usr/bin/env bash
# validate-skill.sh — Skill 原子化合规性校验入口
# v2: 在 lx-validate-skill 被清理后(e75adf4)，改为调用轻量替代品 validate_skill_refs.py
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/hooks/harness_config.sh" 2>/dev/null || true

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATOR="$SCRIPT_DIR/validate_skill_refs.py"

if [ ! -f "$VALIDATOR" ]; then
  echo "❌ 校验脚本不存在: $VALIDATOR" >&2
  exit 1
fi

${PYTHON_BIN:-python3} "$VALIDATOR" "$@"
