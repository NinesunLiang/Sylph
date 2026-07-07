#!/usr/bin/env python3
from __future__ import annotations

from carroros_hooklib import OMC, active_token, hook_block, hook_continue

STAMP_FILE = OMC / "state" / ".fallback-check-done"

def main() -> int:
    # ─── stamp 检查：第一步后永久跳过 ───
    if STAMP_FILE.exists():
        return hook_continue("FallbackCheck: SKIP already_done")

    token, token_path = active_token()
    if not token:
        return hook_continue("FallbackCheck: NO_TASK")

    task = token.get("task", {}) or {}
    status = task.get("status") or token.get("status") or "active"

    if status == "blocked":
        reason = task.get("blocked") or task.get("reason") or "blocked"
        return hook_block(f"FallbackCheck: BLOCK task_blocked reason={reason}")

    if status == "waiting_user":
        fallback = task.get("fallback", {}) or {}
        reason = fallback.get("reason") or task.get("reason") or "requires_user"
        return hook_block(f"FallbackCheck: ASK_USER reason={reason}")

    fallback = task.get("fallback", {}) or {}
    if fallback.get("unresolved"):
        return hook_block(f"FallbackCheck: BLOCK unresolved_fallback reason={fallback.get('reason', 'unknown')}")

    # ─── 写 stamp ───
    STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAMP_FILE.write_text("1")

    return hook_continue("FallbackCheck: ALLOW")

if __name__ == "__main__":
    raise SystemExit(main())
