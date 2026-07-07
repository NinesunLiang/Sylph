#!/usr/bin/env python3
from __future__ import annotations

import re

from carroros_hooklib import (
    append_audit,
    extract_command,
    hook_block,
    hook_continue,
    read_stdin_json,
    sanitize_text,
)

DANGEROUS_COMMANDS = [
    r"^rm\s+-rf\s+(/|\.|~|\*)",
    r"^rm\s+-r\s+(/|\.|~|\*)",
    r"^sudo\b",
    r"^chmod\s+777\b",
    r"^chown\b",
    r"^git\s+push\s+(-f|--force)",
    r"^dd\s+if=",
    r"^mkfs\.",
    r"^fdisk\b",
    r":\(\)\{\s*:\|:\s*&\s*\};:",
]

ASK_USER_COMMANDS = [
    r"\bcurl\b.*\|\s*(sh|bash)",
    r"\bwget\b.*\|\s*(sh|bash)",
    r"\bnpm\s+install\b",
    r"\bpip\s+install\b",
    r"\bbrew\s+install\b",
    r"\bcargo\s+install\b",
    r"\bdocker\s+run\b",
    r"\bkubectl\b",
]

def match_any(command: str, patterns: list[str]) -> str | None:
    cmd = command.strip()
    for pat in patterns:
        if re.search(pat, cmd, re.IGNORECASE):
            return pat
    return None

def main() -> int:
    payload = read_stdin_json()
    command = extract_command(payload)
    if not command:
        return hook_continue("PreActionGate: ALLOW no_command")

    hard = match_any(command, DANGEROUS_COMMANDS)
    if hard:
        append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-action-gate",
            "decision": "BLOCK",
            "reason": "dangerous_command",
            "pattern": hard,
            "command_preview": sanitize_text(command, 160),
        })
        return hook_block(f"PreActionGate: BLOCK dangerous_command pattern={hard}")

    ask = match_any(command, ASK_USER_COMMANDS)
    if ask:
        append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-action-gate",
            "decision": "ASK_USER",
            "reason": "approval_required_command",
            "pattern": ask,
            "command_preview": sanitize_text(command, 160),
        })
        return hook_block(f"PreActionGate: ASK_USER required before command pattern={ask}")

    append_audit({
        "event_type": "preaction_decision",
        "actor": "hook:pretool-action-gate",
        "decision": "ALLOW",
        "reason": "command_allowed",
        "command_preview": sanitize_text(command, 160),
    })
    return hook_continue("PreActionGate: ALLOW")

if __name__ == "__main__":
    raise SystemExit(main())