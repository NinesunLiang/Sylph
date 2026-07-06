#!/usr/bin/env bash
# statusline-command.sh — CarrorOS Claude Code Statusline Hook
# 9.md §7
set -u

ROOT="${CARROROS_ROOT:-$(pwd)}"
PYTHON="${PYTHON:-python3}"
SCRIPT="$ROOT/.claude/scripts/statusline.py"
FALLBACK="$ROOT/.claude/scripts/fallback_engine.py"

if [ ! -f "$SCRIPT" ]; then
  echo "CarrorOS L1_BASE FALLBACK no_statusline_script"
  exit 0
fi

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "CarrorOS L1_BASE FALLBACK python_missing"
  exit 0
fi

OUTPUT="$("$PYTHON" "$SCRIPT" 2>/dev/null)"
STATUS=$?

if [ "$STATUS" -ne 0 ] || [ -z "$OUTPUT" ]; then
  if [ -f "$FALLBACK" ]; then
    "$PYTHON" "$FALLBACK" cli_hook_failed low >/dev/null 2>&1 || true
  fi
  echo "CarrorOS L1_BASE FALLBACK cli_hook_failed"
  exit 0
fi

printf '%s\n' "$OUTPUT" | head -n 1 | cut -c 1-160
exit 0
