#!/usr/bin/env python3
"""
Pretool Fallback Check — CarrorOS PreActionGate Fallback 检测

Purpose:
  Before each tool use, check if the active task is in fallback/blocked state.
  Removed stamp — every PreToolUse gets checked.
  Calls fallback_engine for detection, does not duplicate decision logic.
"""

from __future__ import annotations

from carroros_hooklib import active_token, hook_block, hook_continue

def main() -> int:
    token, token_path = active_token()
    if not token or not token_path:
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

    # Check session-level fallback
    session = token.get("session", {}) or {}
    if session.get("fallback"):
        fb = session["fallback"]
        reason = fb.get("reason", "unknown")
        return hook_continue(f"FallbackCheck: session_fallback reason={reason}")

    return hook_continue("FallbackCheck: ALLOW")

if __name__ == "__main__":
    raise SystemExit(main())
