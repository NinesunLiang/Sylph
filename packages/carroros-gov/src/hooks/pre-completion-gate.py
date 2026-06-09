#!/usr/bin/env python3
"""
pre-completion-gate.py — PreToolUse:TaskUpdate — 前置完成门禁，阻止无证据的 completed 调用
Role: 前置完成门禁，在 AI 调用 TaskUpdate(completed) 前阻止，减少浪费轮次
对应 pre-completion-gate.sh 的 Python 移植，保持完全相同的逻辑
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Import shared library
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness_lib import (
    hc_enabled,
    is_mode_active,
    flywheel_event,
    hc_emit_hook_json,
)

# ─── Path setup ───
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
TOKENS_DIR = STATE_DIR / "tokens"


def main():
    # ── Guard: check if pre_completion_gate is enabled ──
    if not hc_enabled("pre_completion_gate"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Read stdin JSON ──
    input_str = sys.stdin.read()
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        # Invalid JSON → fail-open
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Extract status field ──
    tool_input = input_data.get("tool_input", {}) or {}
    status = tool_input.get("status", "")

    # ── Non-completed status → pass through ──
    if status != "completed":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Autonomous / Ghost mode detection ──
    # Check these files (mirrors bash logic exactly):
    #   .omc/state/tokens/autonomous.active
    #   .omc/state/ghost-mode.active
    #   .omc/state/tokens/lx-ghost.json
    #   .omc/state/tokens/lx-goal.json
    autonomous_active = TOKENS_DIR / "autonomous.active"
    ghost_mode_active = STATE_DIR / "ghost-mode.active"
    lx_ghost = TOKENS_DIR / "lx-ghost.json"
    lx_goal = TOKENS_DIR / "lx-goal.json"

    if (autonomous_active.exists() or
        ghost_mode_active.exists() or
        lx_ghost.exists() or
        lx_goal.exists()):
        print("[pre-completion-gate] 自主模式: 允许 completed（门禁降级）", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Check evidence file ──
    # File: .omc/state/.completion-evidence-YYYYMMDD
    date_str = datetime.now().strftime("%Y%m%d")
    evidence_file = STATE_DIR / f".completion-evidence-{date_str}"
    blocked_file = STATE_DIR / "completion-blocked"

    evidence_ok = False
    if evidence_file.exists():
        try:
            age = time.time() - evidence_file.stat().st_mtime
            if age < 300:  # 5 minutes freshness
                evidence_ok = True
        except OSError:
            pass

    if not evidence_ok:
        # Log flywheel event
        flywheel_event("pre_completion_gate", "no_evidence", "P2")

        # Write completion-blocked file (DG-131: 触发后续 Edit/Write 最小范围阻断)
        try:
            blocked_file.parent.mkdir(parents=True, exist_ok=True)
            blocked_data = {
                "blocked_at": time.time(),
                "block_count": 0,
                "reason": "no_evidence",
            }
            blocked_file.write_text(
                json.dumps(blocked_data), encoding="utf-8"
            )
        except OSError:
            pass

        # Emit blocked response
        msg = (
            "⚠️ [pre-completion-gate] TaskUpdate(completed) BLOCKED: no VERIFIED evidence.\\n"
            "To unblock: (1) run a verification command (2) cite output with VERIFIED: tag (3) retry.\\n"
            "Edit/Write will be reminded for 2 turns (warning only, continue:true)."
        )
        print(json.dumps({
            "continue": False,
            "additionalContext": msg,
        }))
        sys.exit(2)

    # ── Evidence OK → clear completion-blocked state, allow ──
    try:
        blocked_file.unlink(missing_ok=True)
    except OSError:
        pass

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
