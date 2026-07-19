#!/usr/bin/env python3
"""PreCompact: fail-closed SSOT flush."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.lifecycle_ssot import (  # noqa: E402
    read_stdin_json,
    stderr,
    stdout_json,
    write_precompact_snapshot,
)


def main() -> int:
    try:
        hook_input = read_stdin_json()
        session_id = hook_input.get("session_id") or hook_input.get("sessionId") or ""
        basis = (
            f"precompact:{session_id}:"
            f"{hook_input.get('transcript_path') or hook_input.get('transcriptPath') or ''}"
        )
        event_id = "pc-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
        path, digest, hb = write_precompact_snapshot(hook_input, event_id=event_id)
        stdout_json(
            {
                "ok": True,
                "event": "PreCompact",
                "snapshot": str(path),
                "sha256": digest,
                "handoff_written": hb.get("written"),
                "handoff_claimed": hb.get("claimed"),
                "reconciled": hb.get("reconciled"),
            }
        )
        return 0
    except Exception as exc:
        stderr(f"PRECOMPACT_FAIL:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
