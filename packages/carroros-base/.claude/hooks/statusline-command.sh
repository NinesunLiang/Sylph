#!/usr/bin/env bash
set -u

ROOT="${CARROROS_ROOT:-$(pwd)}"
PYTHON="${PYTHON:-python3}"
SCRIPT="$ROOT/.claude/scripts/statusline.py"
FALLBACK="$ROOT/.claude/scripts/fallback_engine.py"

fallback_event() {
  local reason="$1"
  if command -v "$PYTHON" >/dev/null 2>&1 && [ -f "$FALLBACK" ]; then
    "$PYTHON" "$FALLBACK" cli_hook_failed low >/dev/null 2>&1 || true
  fi
  printf 'CarrorOS L1_BASE FALLBACK %s\n' "$reason" | cut -c 1-160
}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  printf 'CarrorOS L1_BASE FALLBACK python_missing\n'
  exit 0
fi

if [ ! -f "$SCRIPT" ]; then
  fallback_event "no_statusline_script"
  exit 0
fi

OUTPUT="$("$PYTHON" "$SCRIPT" 2>/dev/null)"
STATUS=$?

if [ "$STATUS" -ne 0 ] || [ -z "$OUTPUT" ]; then
  fallback_event "cli_hook_failed"
  exit 0
fi

printf '%s\n' "$OUTPUT" | head -n 1 | tr '\r\n' ' ' | cut -c 1-160
exit 0