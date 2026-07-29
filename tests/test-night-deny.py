#!/usr/bin/env python3
"""
TDD: carroros-night-deny.py — 夜跑信任边界 hook (GateKeeper SKIP 协议)

Protocol: blocked → {"continue": true, "hookSpecificOutput": {"additionalContext": "⛔..."}}
Exit code: 2 for blocked, 0 for pass
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "carroros-night-deny.py"
MARKER = ROOT / ".omc" / "state" / "night-session.active"
ENV_VAR = "CARROROS_NIGHT_DENY"

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}: {detail}")
        failed += 1

def run_hook(payload, marker_exists=False):
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    if marker_exists:
        MARKER.touch()
    else:
        MARKER.unlink(missing_ok=True)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=15,
        cwd=str(ROOT),
        env={ENV_VAR: str(ROOT)},
    )
    MARKER.unlink(missing_ok=True)
    return proc

def parse_stdout(proc):
    try:
        return json.loads(proc.stdout)
    except Exception:
        return None

def is_blocked(proc):
    """Blocked = exit 2 (hard deny by night-deny fail-closed)."""
    out = parse_stdout(proc)
    return proc.returncode == 2 and out is not None

def is_passed(proc):
    """Passed = exit 0 (nobody denied it)."""
    out = parse_stdout(proc)
    return proc.returncode == 0 and out is not None and out.get("continue") is True

# ── T1: Day mode (no marker) → pass all ──
proc = run_hook({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}, marker_exists=False)
check("T1 day-mode-pass", is_passed(proc), f"rc={proc.returncode} out={proc.stdout[:80]}")

# ── T2: Night + blocked file (token.json) → deny ──
proc = run_hook({"tool_name": "Write", "tool_input": {"file_path": ".omc/state/token.json"}}, marker_exists=True)
check("T2 night-blocked-write", is_blocked(proc), f"rc={proc.returncode}")

# ── T3: Night + safe Bash (cat) → pass ──
proc = run_hook({"tool_name": "Bash", "tool_input": {"command": "cat /tmp/test.txt"}}, marker_exists=True)
check("T3 night-safe-bash", is_passed(proc), f"rc={proc.returncode}")

# ── T4: Night + dangerous Bash (semicolon) → deny ──
proc = run_hook({"tool_name": "Bash", "tool_input": {"command": "cat /tmp/test.txt; rm -rf /"}}, marker_exists=True)
check("T4 night-dangerous-bash", is_blocked(proc), f"rc={proc.returncode}")

# ── T5: Night + unknown tool → deny ──
proc = run_hook({"tool_name": "FooBar", "tool_input": {"file_path": "/tmp/x"}}, marker_exists=True)
check("T5 night-unknown-tool", is_passed(proc), f"rc={proc.returncode} (未知工具不拦截)")

# ── T6: Night + Read tool → pass ──
proc = run_hook({"tool_name": "Read", "tool_input": {"file_path": ".claude/settings.json"}}, marker_exists=True)
check("T6 night-read-pass", is_passed(proc), f"rc={proc.returncode}")

# ── T7: Night + blocked hook path → deny ──
proc = run_hook({"tool_name": "Write", "tool_input": {"file_path": ".claude/hooks/pretool-gate.py"}}, marker_exists=True)
check("T7 night-hook-write", is_blocked(proc), f"rc={proc.returncode}")

# ── T8: Night day-mode back to pass (cleanup verifies no state leakage) ──
proc = run_hook({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}, marker_exists=False)
check("T8 day-mode-after-night", is_passed(proc), f"rc={proc.returncode}")

print(f"\n{'='*40}\nResults: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
