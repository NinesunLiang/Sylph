#!/usr/bin/env python3
from __future__ import annotations

from carroros_hooklib import (
    active_token,
    append_audit,
    extract_tool_name,
    hook_block,
    hook_continue,
    read_stdin_json,
    task_dir_from_token,
)

WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}

def main() -> int:
    payload = read_stdin_json()
    tool = extract_tool_name(payload).lower()

    # ─── 非写工具直接放行 ───
    if tool not in WRITE_TOOLS:
        return hook_continue("PlanGate: ALLOW non_write_tool")

    token, token_path = active_token()
    if not token:
        return hook_continue("PlanGate: ALLOW no_active_task")

    task = token.get("task", {}) or {}
    if task.get("status") in {"blocked", "waiting_user"}:
        append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-plan-gate",
            "decision": "BLOCK",
            "reason": f"task_status_{task.get('status')}",
            "task_id": task.get("id"),
        })
        return hook_block(f"PlanGate: BLOCK task_status={task.get('status')}")

    task_dir = task_dir_from_token(token, token_path)
    if not task_dir:
        return hook_block("PlanGate: BLOCK task_dir_missing")

    plan = task_dir / "plan.md"
    executor = task_dir / "executor.md"
    handoff = task_dir / "state" / "session-handoff.md"

    missing = [str(p) for p in (plan, executor, handoff) if not p.exists()]
    if missing:
        append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-plan-gate",
            "decision": "BLOCK",
            "reason": "task_files_missing",
            "missing": missing,
            "task_id": task.get("id"),
        })
        return hook_block(f"PlanGate: BLOCK task_files_missing missing={missing}")

    if not task.get("current_step"):
        return hook_block("PlanGate: BLOCK current_step_missing")

    return hook_continue("PlanGate: ALLOW")

if __name__ == "__main__":
    raise SystemExit(main())
