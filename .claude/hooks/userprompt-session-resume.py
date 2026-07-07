#!/usr/bin/env python3
from __future__ import annotations

import json

from carroros_hooklib import active_token, hook_block, hook_continue, run_script, task_dir_from_token, OMC

STAMP_FILE = OMC / "state" / ".session-resume-done"

def main() -> int:
    # ─── stamp 检查：首次后永久跳过 ───
    if STAMP_FILE.exists():
        return hook_continue("Resume: SKIP already_done")

    token, token_path = active_token()
    if not token or not token_path:
        return hook_continue("Resume: NO_TASK")

    task_dir = task_dir_from_token(token, token_path)
    if not task_dir:
        return hook_block("Resume: BLOCK task_dir_missing")

    code, out, err = run_script(
        "context_engine.py",
        ["resume-check", "--token", str(token_path), "--task", str(task_dir)],
        timeout=10,
    )

    if code == 127:
        return hook_block("Resume: BLOCK context_engine_missing")

    try:
        data = json.loads(out) if out else {}
    except json.JSONDecodeError:
        return hook_block("Resume: BLOCK invalid_context_engine_output")

    if data.get("decision") != "RESUME_OK":
        return hook_block(f"Resume: BLOCK {data.get('reason', 'resume_failed')}")

    code2, state, _ = run_script(
        "context_engine.py",
        ["state-injection", "--token", str(token_path)],
        timeout=10,
    )

    # ─── 写 stamp：无论 resume 结果如何，只跑一次 ───
    STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAMP_FILE.write_text("1")

    if code2 != 0 or not state:
        return hook_continue("Resume: RESUME_OK state_injection_unavailable")

    return hook_continue(
        "Resume: RESUME_OK",
        [
            state[:1000],
            "Reminder: session-handoff/state-injection is not evidence. Do not mark any step complete without VerifyGate.",
        ],
    )

if __name__ == "__main__":
    raise SystemExit(main())
