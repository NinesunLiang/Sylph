#!/usr/bin/env python3
"""
CarrorOS PreToolUse Oracle Gate Hook

Purpose:
  For L2_ENHANCE tasks, check if oracle review is needed before
  executing phase transitions (phase_end, final_acceptance, high-risk).

  Only triggers when:
  - Active task is L2_ENHANCE
  - Action is planning a phase transition or high-risk change
  - Oracle hasn't been run for this phase yet

Constraints:
  - Routing / guardrail only, does not create completion facts
  - Does not replace VerifyGate
  - L1_BASE tasks skip this hook entirely
"""

from __future__ import annotations

from carroros_hooklib import (
    active_token,
    append_audit,
    extract_command,
    hook_block,
    hook_continue,
    read_stdin_json,
)

# Keywords that may need Oracle review
ORACLE_TRIGGERS = [
    "oracle", "acceptance", "final", "archive", "phase_end",
    "merge", "release", "deploy", "production",
]

ORACLE_FORCE = [
    "aut", "payment", "migration", "permission",
]


def main() -> int:
    token, token_path = active_token()
    if not token:
        return hook_continue("OracleGate: ALLOW no_task")

    # Only L2_ENHANCE triggers Oracle
    level = token.get("session", {}).get("level", "L1_BASE")
    if level != "L2_ENHANCE":
        return hook_continue("OracleGate: ALLOW L1_BASE")

    task = token.get("task", {}) or {}
    current_step = task.get("current_step", "")

    # Check if Oracle already done for this phase
    oracle_done = token.get("session", {}).get("oracle_last_verdict")
    phase = task.get("phase", "execute")

    payload = read_stdin_json()
    command = extract_command(payload)

    trigger_hit = False
    if command:
        cmd_lower = command.lower()
        for kw in ORACLE_FORCE:
            if kw in cmd_lower:
                trigger_hit = True
                break
        if not trigger_hit:
            for kw in ORACLE_TRIGGERS:
                if kw in cmd_lower:
                    trigger_hit = True
                    break

    if not trigger_hit:
        return hook_continue("OracleGate: ALLOW no_oracle_trigger")

    append_audit({
        "event_type": "oracle_gate_trigger",
        "actor": "hook:pretool-oracle-gate",
        "decision": "REVIEW",
        "reason": "potential_oracle_trigger_detected",
        "current_step": current_step,
        "phase": phase,
    })

    return hook_continue(
        "OracleGate: REVIEW recommended",
        [
            f"OracleGate: Phase {phase} may need Oracle review. Run: python3 .claude/scripts/oracle_engine.py <review_pack_path>",
            "OracleGate: Oracle does not replace VerifyGate. Steps must be VERIFIED first.",
        ],
    )


if __name__ == "__main__":
    raise SystemExit(main())
