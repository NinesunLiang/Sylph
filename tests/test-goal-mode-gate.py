#!/usr/bin/env python3
"""Goal-mode gate contract tests.

The hook uses a JSON continuation protocol: the process returns 0 and the
payload carries either allow, deny, redirect, or hard-stop semantics.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "pretool-gate.py"
SIGNAL = ROOT / ".omc" / "state" / "tokens" / "autonomous.active"
MODE_FILE = ROOT / ".omc" / "state" / "tokens" / "lx-goal.json"
HARNESS_DIR = ROOT / "scripts" / "carroros-gates"
HARNESS_YAML = HARNESS_DIR / "harness.yaml"
PASS = 0
FAIL = 0


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def run_hook(command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=30,
        env={**os.environ, "CARROROS_GATE_MODE": "l2"},
    )


def parse(proc):
    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        return {}


def protocol(proc):
    result = parse(proc)
    return proc.returncode == 0 and isinstance(result.get("continue"), bool)


def denied(proc):
    result = parse(proc)
    specific = result.get("hookSpecificOutput") or {}
    return (protocol(proc)
            and result.get("continue") is True
            and specific.get("permissionDecision") == "deny")


HARNESS_DIR.mkdir(parents=True, exist_ok=True)
HARNESS_YAML.write_text("project:\n  gate_mode: l2\n", encoding="utf-8")
signal_backup = SIGNAL.read_bytes() if SIGNAL.exists() else None
mode_backup = MODE_FILE.read_bytes() if MODE_FILE.exists() else None

try:
    SIGNAL.unlink(missing_ok=True)
    MODE_FILE.unlink(missing_ok=True)
    r = run_hook("git status")
    ok("T1 interactive allow uses JSON continuation", protocol(r) and parse(r).get("continue") is True, r.stdout[:160])
    ok("T1 interactive allow has no deny decision", (parse(r).get("hookSpecificOutput") or {}).get("permissionDecision") != "deny", r.stdout[:160])

    now = datetime.now(timezone.utc)
    SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    SIGNAL.write_text(json.dumps({"activated": now.isoformat()}), encoding="utf-8")
    MODE_FILE.write_text(json.dumps({
        "active": True,
        "mode": "goal",
        "goal": "goal-mode-contract-test",
        "activated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }), encoding="utf-8")

    r = run_hook("git push --force origin main")
    ok("T2 goal high-risk deny uses JSON continuation", denied(r), r.stdout[:220])
    ok("T2 deny includes a permission reason", bool((parse(r).get("hookSpecificOutput") or {}).get("permissionDecisionReason")), r.stdout[:220])

    r = run_hook("bash -c 'SKIP_VERIFY")
    ok("T3 goal oracle path returns canonical JSON", protocol(r), r.stdout[:220])

    r = run_hook("git status")
    ok("T4 goal safe command remains allowed", protocol(r) and parse(r).get("continue") is True, r.stdout[:160])

    MODE_FILE.write_text(json.dumps({
        "active": True,
        "mode": "goal",
        "goal": "expired-goal-mode-contract-test",
        "activated_at": (now - timedelta(hours=7)).isoformat(),
        "expires_at": (now - timedelta(hours=1)).isoformat(),
    }), encoding="utf-8")
    r = run_hook("git status")
    ok("T5 expired goal still emits canonical JSON", protocol(r), r.stdout[:160])
finally:
    if signal_backup is None:
        SIGNAL.unlink(missing_ok=True)
    else:
        SIGNAL.parent.mkdir(parents=True, exist_ok=True)
        SIGNAL.write_bytes(signal_backup)
    if mode_backup is None:
        MODE_FILE.unlink(missing_ok=True)
    else:
        MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        MODE_FILE.write_bytes(mode_backup)
    HARNESS_YAML.unlink(missing_ok=True)

print(f"Results: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
