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
    lx_ghost = TOKENS_DIR / "lx-ghost.json"
    goal_token = Path(os.environ.get("CARROROS_TOKEN_PATH", "")).expanduser()
    goal_active = False
    if goal_token.is_file():
        try:
            goal_active = json.loads(goal_token.read_text(encoding="utf-8")).get("mode") == "goal"
        except (OSError, json.JSONDecodeError):
            pass

    if lx_ghost.exists() or goal_active:
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

        # Emit REDIRECT response (was BLOCK, 2026-07-25)
        # PreToolUse 也不应硬阻断——改为 REDIRECT: 拦截+引导+AI 自行修正重试
        msg = (
            "🔄 [pre-completion-gate] TaskUpdate(completed) REDIRECTED: 未检测到验证证据。\\n"
            "💡 正确做法: (1) 先运行验证命令 (2) 用 VERIFIED: 标签引用输出 (3) 重试 completed。\\n"
            "Edit/Write 将收到提示(仅提醒,不阻断)。"
        )
        print(json.dumps({
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": msg,
            },
        }))
        sys.exit(0)

    # ── Evidence OK → clear completion-blocked state, allow ──
    try:
        blocked_file.unlink(missing_ok=True)
    except OSError:
        pass

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
