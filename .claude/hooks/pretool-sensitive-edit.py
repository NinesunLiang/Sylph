#!/usr/bin/env python3
from __future__ import annotations

from carroros_hooklib import (
    append_audit,
    extract_path,
    extract_tool_name,
    hook_block,
    hook_continue,
    is_sensitive_path,
    read_stdin_json,
)

WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
READ_TOOLS = {"read"}

def main() -> int:
    payload = read_stdin_json()
    tool = extract_tool_name(payload).lower()
    path = extract_path(payload)

    if not path:
        return hook_continue("SensitiveEdit: ALLOW no_path")

    if is_sensitive_path(path):
        decision = "BLOCK"
        append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-sensitive-edit",
            "decision": decision,
            "reason": "sensitive_path",
            "tool": tool,
            "path": path,
        })
        return hook_block(f"SensitiveEdit: BLOCK sensitive_path path={path}")

    return hook_continue("SensitiveEdit: ALLOW")

if __name__ == "__main__":
    raise SystemExit(main())