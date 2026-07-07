#!/usr/bin/env python3
"""
CarrorOS SessionStart Hook

Purpose:
  On new session start, check for active task and inject resume context.

  Registered at SessionStart lifecycle event (fires once per session).
  Does NOT use stamp gating — SessionStart is already one-shot.

Constraints:
  - Routing / observation / guardrail only
  - Does not create completion facts
  - Does not replace VerifyGate / Oracle / Fallback / Archive
"""

from __future__ import annotations

import json

from carroros_hooklib import (
    active_token,
    hook_continue,
    run_script,
    task_dir_from_token,
)

CONTEXT_ENGINE = "context_engine.py"


def main() -> int:
    # ─── 1. Check if there's an active task ───
    token, token_path = active_token()
    if not token or not token_path:
        return hook_continue("SessionStart: NO_TASK")

    task_dir = task_dir_from_token(token, token_path)
    if not task_dir:
        return hook_continue("SessionStart: TASK_NO_DIR")

    # ─── 2. Run resume-check via context engine ───
    code, out, err = run_script(
        CONTEXT_ENGINE,
        ["resume-check", "--token", str(token_path), "--task", str(task_dir)],
        timeout=10,
    )

    try:
        data = json.loads(out) if out else {}
    except json.JSONDecodeError:
        return hook_continue("SessionStart: resume_invalid_output")

    if data.get("decision") != "RESUME_OK":
        reason = data.get("reason", "resume_failed")
        return hook_continue(f"SessionStart: resume_blocked_{reason}")

    # ─── 3. Inject state ───
    code2, state, _ = run_script(
        CONTEXT_ENGINE,
        ["state-injection", "--token", str(token_path)],
        timeout=10,
    )

    if code2 != 0 or not state:
        return hook_continue("SessionStart: RESUME_OK")

    return hook_continue(
        "SessionStart: RESUME_OK",
        [
            state[:1000],
            "Reminder: session-handoff/state-injection is not evidence. Do not mark any step complete without VerifyGate.",
        ],
    )


if __name__ == "__main__":
    raise SystemExit(main())
