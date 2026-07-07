#!/usr/bin/env python3
"""
CarrorOS PreToolUse VerifyGate Hook

Purpose:
  Intercept write operations to plan.md that attempt to mark steps [x]
  without a corresponding VerifyGate VERIFIED decision in audit.

  This is the enforcement arm: VerifyGate engine decides,
  this hook enforces at PreToolUse time.

Constraints:
  - Routing / guardrail only, does not create completion facts
  - Does not replace VerifyGate engine
"""

from __future__ import annotations

import json
import re

from carroros_hooklib import (
    active_token,
    append_audit,
    extract_path,
    extract_tool_name,
    hook_block,
    hook_continue,
    read_stdin_json,
    ROOT,
)

WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
PLAN_FILE_PATTERNS = ["plan.md", "plan"]


def is_plan_write(path: str) -> bool:
    """Check if the write targets a plan.md file."""
    normalized = path.replace("\\", "/")
    return any(normalized.endswith(p) for p in PLAN_FILE_PATTERNS)


def has_new_checkmark(content: str) -> bool:
    """Check if content contains newly marked [x] steps."""
    return bool(re.search(r"\[x\]", content, re.IGNORECASE))


def check_verifygate_audit(step_id: str | None = None) -> list[dict]:
    """Read audit to find recent VerifyGate VERIFIED decisions."""
    audit_dir = ROOT / ".omc" / "audit"
    if not audit_dir.exists():
        return []

    results: list[dict] = []
    for audit_file in sorted(audit_dir.glob("*.jsonl")):
        with audit_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event_type") == "verify_decision" and event.get("decision") == "VERIFIED":
                    if step_id is None or event.get("step") == step_id:
                        results.append(event)
    return results


def main() -> int:
    payload = read_stdin_json()
    tool = extract_tool_name(payload).lower()

    # Only intercept write tools
    if tool not in WRITE_TOOLS:
        return hook_continue("VerifyGate: ALLOW non_write_tool")

    edit_path = extract_path(payload)
    if not edit_path or not is_plan_write(edit_path):
        return hook_continue("VerifyGate: ALLOW non_plan_write")

    # Get pending writes (tool_input content)
    tool_input = payload.get("tool_input", {}) or {}
    content = str(tool_input.get("content", "") or tool_input.get("new_string", "") or "")

    # Check if content marks steps done
    has_new_dones = has_new_checkmark(content)
    if not has_new_dones:
        return hook_continue("VerifyGate: ALLOW no_step_marking")

    # Check active token
    token, token_path = active_token()
    if not token:
        return hook_continue("VerifyGate: ALLOW no_active_task")

    task = token.get("task", {}) or {}
    current_step = task.get("current_step")

    # Check if VerifyGate has VERIFIED this step
    verified_audits = check_verifygate_audit(current_step)
    if not verified_audits:
        append_audit({
            "event_type": "verifygate_preaction_block",
            "actor": "hook:pretool-verify-gate",
            "decision": "BLOCK",
            "reason": "step_not_verified",
            "path": edit_path,
            "current_step": current_step,
        })
        return hook_block(
            f"VerifyGate: BLOCK step {current_step} not VERIFIED. "
            "Run 'python3 .claude/scripts/verify_gate.py --step <step> --plan <path> --executor <path>' first."
        )

    append_audit({
        "event_type": "verifygate_preaction_allow",
        "actor": "hook:pretool-verify-gate",
        "decision": "ALLOW",
        "reason": "step_verified_in_audit",
        "path": edit_path,
        "current_step": current_step,
    })
    return hook_continue(f"VerifyGate: ALLOW step {current_step} VERIFIED in audit")


if __name__ == "__main__":
    raise SystemExit(main())
