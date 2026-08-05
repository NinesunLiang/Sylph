#!/usr/bin/env python3
"""
TDD: pretool-scorecard-gate.py — 自评审计门禁 (ADR-0013)

Covers:
1. Non-scorecard edits → pass through
2. Scorecard edit with evidence → pass
3. Scorecard edit without evidence → block/redirect
4. Scorecard read → pass
5. Malformed scorecard content → handled gracefully
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "pretool-scorecard-gate.py"

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

def run_hook(payload, env_extra=None):
    env = {}
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=15,
        cwd=str(ROOT),
    )
    return proc

def out(proc):
    try:
        return json.loads(proc.stdout)
    except Exception:
        return None

# ── T1: Non-scorecard file (Bash) → pass ──
proc = run_hook({"tool_name": "Bash", "tool_input": {"command": "python3 script.py"}})
check("T1 non-scorecard-bash", proc.returncode == 0, f"rc={proc.returncode}")

# ── T2: Non-scorecard file write (.py) → pass ──
proc = run_hook({"tool_name": "Write", "tool_input": {"file_path": "src/test.py", "content": "print('hello')"}})
check("T2 non-scorecard-write", proc.returncode == 0, f"rc={proc.returncode}")

# ── T3: Scorecard write WITHOUT evidence → block/redirect ──
proc = run_hook({"tool_name": "Write", "tool_input": {
    "file_path": "improve_plan/something/scorecard.md",
    "content": "## Scores\n| Item | Name | Before | External | Current | Verdict |\n|------|------|--------|---------|---------|--------|\n| C1 | 代码质量 | 10 | 7 | **8** | **6** |\n"
}})
result = out(proc) or {}
check("T3 scorecard-no-evidence",
      proc.returncode == 0
      and result.get("continue") is True
      and (result.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny",
      f"rc={proc.returncode} out={proc.stdout[:160] if proc.stdout else '(empty)'}")

# ── T4: Scorecard write WITH evidence → pass ──
proc = run_hook({"tool_name": "Write", "tool_input": {
    "file_path": "improve_plan/something/scorecard.md",
    "content": "## Scores\n| Item | Name | Before | External | Current | Verdict |\n|------|------|--------|---------|---------|--------|\n| C1 | 代码质量 | 10 | 7 | **8** | **6** | file:src/test.py:42\n"
}})
check("T4 scorecard-with-evidence", proc.returncode == 0, f"rc={proc.returncode}")

# ── T5: Scorecard Read → pass through always ──
proc = run_hook({"tool_name": "Read", "tool_input": {"file_path": "scorecard.md"}})
check("T5 scorecard-read", proc.returncode == 0, f"rc={proc.returncode}")

# ── T6: Scorecard with no-change scores (no improvement claim) → pass ──
proc = run_hook({"tool_name": "Write", "tool_input": {
    "file_path": "improve_plan/something/scorecard.md",
    "content": "## Scores\n| Item | Name | Before | External | Current | Verdict |\n|------|------|--------|---------|---------|--------|\n| C1 | 代码质量 | 10 | 7 | 6 | 6 |\n"
}})
check("T6 scorecard-no-improvement", proc.returncode == 0, f"rc={proc.returncode}")

print(f"\n{'='*40}\nResults: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
