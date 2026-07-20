#!/usr/bin/env bash
# Stop: keep stop-flywheel, then session-end seal (fail-closed).
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT"

INPUT="$(cat || true)"

printf '%s' "$INPUT" | python3 ".claude/hooks/stop-flywheel.py"
fly_rc=$?
if [[ "$fly_rc" -ne 0 ]]; then
  echo "STOP_WRAPPER_FAIL:stop-flywheel.rc=$fly_rc" >&2
  exit "$fly_rc"
fi

printf '%s' "$INPUT" | python3 ".claude/hooks/session-end-lifecycle.py"
end_rc=$?
if [[ "$end_rc" -ne 0 ]]; then
  echo "STOP_WRAPPER_FAIL:session-end.rc=$end_rc" >&2
  exit "$end_rc"
fi

exit 0
