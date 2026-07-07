#!/usr/bin/env python3
from __future__ import annotations

from carroros_hooklib import (
    active_token,
    append_audit,
    extract_command,
    extract_path,
    extract_tool_name,
    hook_block,
    hook_continue,
    read_stdin_json,
    sanitize_text,
)

WRITE_AUDIT_TOOLS = {"edit", "write", "multiedit", "notebookedit", "bash", "terminal"}

def main() -> int:
    payload = read_stdin_json()
    tool = extract_tool_name(payload)

    # ─── 只对写工具有实质变更的步骤审计 ───
    if tool.lower() not in WRITE_AUDIT_TOOLS:
        return hook_continue("PostToolAudit: SKIP non_write_tool")

    command = extract_command(payload)
    path = extract_path(payload)

    token, _ = active_token()
    task = token.get("task", {}) if token else {}

    result = payload.get("result") or payload.get("tool_result") or ""
    result_text = sanitize_text(result, 200)

    ok = append_audit({
        "event_type": "tool_executed",
        "actor": "hook:posttool-audit",
        "task_id": task.get("id"),
        "level": (token.get("session", {}) or {}).get("level") if token else None,
        "current_step": task.get("current_step"),
        "tool": tool,
        "path": path or None,
        "command_preview": sanitize_text(command, 160) if command else None,
        "result_length": len(str(result)),
        "result_preview": result_text,
        "note": "tool_executed_is_not_verify_evidence",
    })

    if not ok:
        return hook_block("PostToolAudit: BLOCK audit_write_failed")

    return hook_continue("PostToolAudit: OK")

if __name__ == "__main__":
    raise SystemExit(main())
