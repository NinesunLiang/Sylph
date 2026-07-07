#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from carroros_hooklib import (
    active_token,
    append_audit,
    extract_path,
    extract_tool_name,
    hook_block,
    hook_continue,
    read_stdin_json,
    task_dir_from_token,
)

WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}

def parse_scope(plan_text: str) -> list[str]:
    in_scope = False
    files: list[str] = []
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("## scope") or stripped.lower().startswith("## scope freeze"):
            in_scope = True
            continue
        if in_scope and stripped.startswith("## "):
            break
        if in_scope:
            m = re.match(r"[-*]\s+`?([^`\s]+)`?", stripped)
            if m:
                files.append(m.group(1).replace("\\", "/"))
    return files

def in_scope(path: str, scope: list[str]) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    for item in scope:
        s = item.replace("\\", "/").lstrip("./")
        if p == s or p.endswith("/" + s) or p.startswith(s.rstrip("/") + "/"):
            return True
    return False

def main() -> int:
    payload = read_stdin_json()
    tool = extract_tool_name(payload).lower()
    if tool and tool not in WRITE_TOOLS:
        return hook_continue("EditScope: ALLOW non_write_tool")

    edit_path = extract_path(payload)
    if not edit_path:
        return hook_continue("EditScope: ALLOW no_path")

    token, token_path = active_token()
    if not token:
        return hook_continue("EditScope: ALLOW no_active_token")

    task_dir = task_dir_from_token(token, token_path)
    if not task_dir:
        return hook_block("EditScope: BLOCK task_dir_missing; cannot verify scope")

    plan_path = task_dir / "plan.md"
    if not plan_path.exists():
        return hook_block("EditScope: BLOCK plan_missing; cannot verify scope")

    scope = parse_scope(plan_path.read_text(encoding="utf-8"))
    if not scope:
        return hook_block("EditScope: BLOCK scope_missing; plan must declare Scope")

    if not in_scope(edit_path, scope):
        append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-edit-scope",
            "decision": "BLOCK",
            "reason": "scope_violation",
            "path": edit_path,
            "scope": scope[:50],
        })
        return hook_block(f"EditScope: BLOCK scope_violation path={edit_path}")

    return hook_continue("EditScope: ALLOW")

if __name__ == "__main__":
    raise SystemExit(main())