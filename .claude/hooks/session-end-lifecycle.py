#!/usr/bin/env python3
"""SessionEnd/Stop seal + handoff reconcile."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.lifecycle_ssot import (  # noqa: E402
    load_handoff,
    read_stdin_json,
    seal_session_end,
    stderr,
    stdout_json,
)


def main() -> int:
    try:
        hook_input = read_stdin_json()
        session_id = hook_input.get("session_id") or hook_input.get("sessionId") or ""
        basis = f"session_end:{session_id}:{hook_input.get('hook_event_name') or 'Stop'}"
        event_id = "se-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
        reason = (
            hook_input.get("hook_event_name")
            or hook_input.get("hookEventName")
            or "Stop"
        )
        lc = seal_session_end(event_id, reason=str(reason), hook_input=hook_input)
        hb = load_handoff()
        stdout_json(
            {
                "ok": True,
                "event": "SessionEnd",
                "sealed": lc.get("end", {}).get("sealed"),
                "mode": lc.get("mode"),
                "handoff_written": hb.get("written"),
                "handoff_claimed": hb.get("claimed"),
            }
        )
        return 0
    except Exception as exc:
        stderr(f"SESSION_END_FAIL:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
