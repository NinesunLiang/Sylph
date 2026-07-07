#!/usr/bin/env python3
"""
CarrorOS PreActionGate — 动作级前置安全门（3.md spec）

9 种动作 × 4 种裁决：
  action_types: read_file, write_file, delete_file, run_command, install_dependency,
                network_call, git_operation, database_operation, production_operation
  decisions: ALLOW, ASK_USER, BLOCK, ESCALATE
"""

from __future__ import annotations

import re

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
    task_dir_from_token,
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
    r"\bterraform\s+apply\b",
    r"\bterraform\s+destroy\b",
]

SENSITIVE_PATTERNS = [
    r"(^|/)\.env(\.|$|/)",
    r"(^|/)\.ssh(/|$)",
    r"(^|/)\.aws(/|$)",
    r"(^|/)\.gcp(/|$)",
    r"(^|/)\.azure(/|$)",
    r"id_rsa",
    r"id_ed25519",
    r"private[_-]?key",
    r"secret",
    r"credential",
    r"password",
    r"token",
    r"cookie",
]

WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
DELETE_TOOLS = {"edit", "write"}  # content deletion also covered
READ_TOOLS = {"read", "ls", "list", "globbing", "grep"}


def match_any(text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return pat
    return None


def is_sensitive(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(re.search(pat, normalized, re.IGNORECASE) for pat in SENSITIVE_PATTERNS)


def classify_tool(tool: str) -> str:
    """Map tool name to action_type from 3.md."""
    if tool in ("bash", "terminal"):
        return "run_command"
    if tool in ("edit", "write", "multiedit"):
        return "write_file"
    if tool == "notebookedit":
        return "write_file"
    if tool in ("read",):
        return "read_file"
    if tool in ("delete",):
        return "delete_file"
    return "unknown"


def main() -> int:
    payload = read_stdin_json()
    tool_name = extract_tool_name(payload).lower()
    command = extract_command(payload)
    edit_path = extract_path(payload)
    action_type = classify_tool(tool_name)

    # ── 1. Command safety check (run_command) ──
    if command and action_type == "run_command":
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

    # ── 2. File path safety check (write_file / read_file / delete_file) ──
    if edit_path and action_type in ("write_file", "read_file", "delete_file"):
        if is_sensitive(edit_path):
            if action_type == "read_file":
                decision = "BLOCK"
                reason = "sensitive_read_path"
            else:
                # Check if path is in scope
                token, _ = active_token()
                if token:
                    task = token.get("task", {}) or {}
                    scope = task.get("scope", []) or []
                    if scope and any(s.replace("\\", "/") in edit_path.replace("\\", "/") for s in scope):
                        decision = "ASK_USER"
                        reason = "sensitive_path_in_scope"
                    else:
                        decision = "BLOCK"
                        reason = "sensitive_path_scope_violation"
                else:
                    decision = "BLOCK"
                    reason = "sensitive_path_no_task"

            append_audit({
                "event_type": "preaction_decision",
                "actor": "hook:pretool-action-gate",
                "decision": decision,
                "reason": reason,
                "action_type": action_type,
                "path": sanitize_text(edit_path, 160),
            })
            return hook_block(f"PreActionGate: {decision} {reason} path={edit_path}")

    # ── 3. Write file scope check ──
    if edit_path and action_type == "write_file":
        token, _ = active_token()
        if token:
            task = token.get("task", {}) or {}
            scope = task.get("scope", []) or []
            if scope and not any(s.replace("\\", "/") in edit_path.replace("\\", "/") for s in scope):
                append_audit({
                    "event_type": "preaction_decision",
                    "actor": "hook:pretool-action-gate",
                    "decision": "ASK_USER",
                    "reason": "scope_out_write",
                    "action_type": action_type,
                    "path": sanitize_text(edit_path, 160),
                    "scope": scope[:10],
                })
                return hook_block(f"PreActionGate: ASK_USER scope_out_write path={edit_path}")

    # ── 4. Allow ──
    append_audit({
        "event_type": "preaction_decision",
        "actor": "hook:pretool-action-gate",
        "decision": "ALLOW",
        "reason": "scope_match_and_no_policy_hit",
        "action_type": action_type,
        "command_preview": sanitize_text(command, 160) if command else None,
        "path": sanitize_text(edit_path, 160) if edit_path else None,
    })
    return hook_continue("PreActionGate: ALLOW")


if __name__ == "__main__":
    raise SystemExit(main())