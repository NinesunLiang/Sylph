#!/usr/bin/env python3
"""SubagentStop → handoff SSOT item (idempotent)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.lifecycle_ssot import (  # noqa: E402
    on_subagent_stop,
    read_stdin_json,
    stderr,
    stdout_json,
)


def main() -> int:
    try:
        hook_input = read_stdin_json()
        agent = (
            hook_input.get("agent_id")
            or hook_input.get("agentId")
            or hook_input.get("subagent_id")
            or "unknown"
        )
        session_id = hook_input.get("session_id") or hook_input.get("sessionId") or ""
        basis = f"subagent_stop:{session_id}:{agent}:{hook_input.get('hook_event_name')}"
        event_id = "ss-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
        hb = on_subagent_stop(event_id, hook_input)
        stdout_json(
            {
                "ok": True,
                "event": "SubagentStop",
                "handoff_written": hb.get("written"),
                "handoff_claimed": hb.get("claimed"),
            }
        )
        return 0
    except Exception as exc:
        stderr(f"SUBAGENT_STOP_FAIL:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
