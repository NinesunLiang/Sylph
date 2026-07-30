#!/usr/bin/env python3
"""
TDD RED: Hook Protocol Contract — PreToolUse continuation protocol (Step H1)

Exit codes:
  0 = All desired behaviors are already implemented (GREEN would start)
  1 = Contract assertions failed (RED phase: implementation gap confirmed)
  2 = Infrastructure error (test setup issue)
"""

import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── Path fixture ──
HOOKS_DIR = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
SCRIPTS_DIR = HOOKS_DIR.parent / "scripts"
ROOT = HOOKS_DIR.parents[1]

def _install_paths():
    for p in [str(HOOKS_DIR), str(SCRIPTS_DIR)]:
        if p not in sys.path:
            sys.path.insert(0, p)

# Install paths for importability
_install_paths()

# ── Test counters ──
INFRA_ERRORS = 0
CONTRACT_FAILURES = 0
PASSES = 0

def infra_err(msg):
    global INFRA_ERRORS
    INFRA_ERRORS += 1
    print(f"  ⚠️  INFRA: {msg}")

def check(name, cond, detail=""):
    """Assert desired contract behavior. cond=False means contract is not met."""
    global PASSES, CONTRACT_FAILURES
    if cond:
        PASSES += 1
        print(f"  ✅ {name}")
    else:
        CONTRACT_FAILURES += 1
        print(f"  ❌ {name}  (contract not met)")
        if detail:
            print(f"     {detail}")


# ════════════════════════════════════════════════════════════
# Goal mode monkeypatch — no real file manipulation
# ════════════════════════════════════════════════════════════

_helpers = None  # filled by _import_helpers()

def _import_helpers():
    """Lazy import pretool_gates.helpers with path fixture."""
    _install_paths()
    import importlib
    return importlib.import_module("pretool_gates.helpers")

def _ensure_helpers():
    global _helpers
    if _helpers is None:
        _helpers = _import_helpers()
    return _helpers

@contextlib.contextmanager
def _patched_goal_mode(val):
    """Monkeypatch _goal_mode without touching any files on disk."""
    mod = _ensure_helpers()
    orig = getattr(mod, "_goal_mode")
    setattr(mod, "_goal_mode", lambda: val)
    try:
        yield
    finally:
        setattr(mod, "_goal_mode", orig)


# ════════════════════════════════════════════════════════════
# R1 — _redirect() output: permissionDecision:deny, non-empty reason
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R1: _redirect() output contract")
print("=" * 60)

try:
    # Goal-mode OFF for standard redirect testing
    with _patched_goal_mode(False):
        helpers = _ensure_helpers()
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            helpers._redirect("test redirect reason", "test guidance text")
    raw = buf.getvalue()
    output = json.loads(raw)
    hs = output.get("hookSpecificOutput", {})

    check("R1a continue:true", output.get("continue") is True,
          f"got={output.get('continue')!r}")

    check("R1b hookEventName=PreToolUse", hs.get("hookEventName") == "PreToolUse",
          f"got={hs.get('hookEventName')!r}")

    check("R1c permissionDecision=deny", hs.get("permissionDecision") == "deny",
          f"got={hs.get('permissionDecision')!r}")

    pdr = hs.get("permissionDecisionReason")
    check("R1d permissionDecisionReason non-empty",
          isinstance(pdr, str) and len(pdr) > 0,
          f"got={pdr!r}")

    ac = hs.get("additionalContext")
    check("R1e additionalContext non-empty",
          isinstance(ac, str) and len(ac) > 0,
          f"got={'present' if ac else 'missing'}")

except Exception as e:
    infra_err(f"R1 import/setup: {e}")


# ════════════════════════════════════════════════════════════
# R3 — _block() non-high-risk: continue:true + permissionDecision
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R3: _block() non-high-risk (recoverable denial)")
print("=" * 60)

try:
    helpers = _ensure_helpers()
    with _patched_goal_mode(False):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            helpers._block("scope violation", "write within declared scope")
    raw2 = buf.getvalue()
    output2 = json.loads(raw2)
    hs2 = output2.get("hookSpecificOutput")

    check("R3a continue:true for recoverable",
          output2.get("continue") is True,
          f"got={output2.get('continue')!r}")

    has_hs = isinstance(hs2, dict)
    check("R3b hookSpecificOutput exists", has_hs,
          f"got={type(hs2).__name__ if hs2 is not None else 'None'}")

    if has_hs:
        check("R3c hookEventName=PreToolUse",
              hs2.get("hookEventName") == "PreToolUse",
              f"got={hs2.get('hookEventName')!r}")
        check("R3d permissionDecision=deny",
              hs2.get("permissionDecision") == "deny",
              f"got={hs2.get('permissionDecision')!r}")
        pdr2 = hs2.get("permissionDecisionReason")
        check("R3e permissionDecisionReason non-empty",
              isinstance(pdr2, str) and len(pdr2) > 0,
              f"got={pdr2!r}")
        ac2 = hs2.get("additionalContext")
        check("R3f additionalContext non-empty",
              isinstance(ac2, str) and len(ac2) > 0,
              f"got={'present' if ac2 else 'missing'}")
except Exception as e:
    infra_err(f"R3 setup: {e}")


# ════════════════════════════════════════════════════════════
# R4 — pretool-scorecard-gate: exit 0 + continue:true for ALL paths
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R4: pretool-scorecard-gate JSON output contract")
print("=" * 60)

SCORECARD_HOOK = HOOKS_DIR / "pretool-scorecard-gate.py"

def _run_scorecard(payload):
    return subprocess.run(
        [sys.executable, str(SCORECARD_HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=15,
        cwd=str(ROOT),
    )

def _parse_json(out):
    try:
        return json.loads(out)
    except Exception:
        return None

try:
    # T1: non-scorecard edit -> pass
    proc = _run_scorecard({"tool_name": "Write", "tool_input": {
        "file_path": "src/test.py", "content": "print('hi')"}})
    out = _parse_json(proc.stdout)
    check("R4a non-scorecard exit 0", proc.returncode == 0, f"rc={proc.returncode}")
    check("R4b non-scorecard continue:true",
          out is not None and out.get("continue") is True)

    # T2: scorecard WITHOUT evidence
    NO_EV_CONTENT = (
        "## Scores\n| Item | Name | Before | External | Current | Verdict |\n"
        "|------|------|--------|---------|---------|--------|\n"
        "| C1 | 代码质量 | 10 | 7 | **8** | **6** |\n"
    )
    proc2 = _run_scorecard({"tool_name": "Write", "tool_input": {
        "file_path": "scorecard.md",
        "content": NO_EV_CONTENT,
    }})
    out_v = _parse_json(proc2.stdout)

    check("R4c scorecard-violation exit 0", proc2.returncode == 0,
          f"rc={proc2.returncode}")

    if out_v:
        check("R4d scorecard-violation continue:true",
              out_v.get("continue") is True,
              f"got={out_v.get('continue')}")
        hs4 = out_v.get("hookSpecificOutput", {})
        check("R4e scorecard-violation permissionDecision=deny",
              hs4.get("permissionDecision") == "deny",
              f"got={hs4.get('permissionDecision')!r}")
        pdr4 = hs4.get("permissionDecisionReason")
        check("R4f scorecard-violation permissionDecisionReason non-empty",
              isinstance(pdr4, str) and len(pdr4) > 0,
              f"got={pdr4!r}")
        ac4 = hs4.get("additionalContext")
        check("R4g scorecard-violation additionalContext non-empty",
              isinstance(ac4, str) and len(ac4) > 0,
              f"got={'present' if ac4 else 'missing'}")
        check("R4h scorecard-violation hookEventName=PreToolUse",
              hs4.get("hookEventName") == "PreToolUse",
              f"got={hs4.get('hookEventName')!r}")

    # T3: scorecard WITH evidence -> pass
    WITH_EV_CONTENT = (
        "## Scores\n| Item | Name | Before | External | Current | Verdict |\n"
        "|------|------|--------|---------|---------|--------|\n"
        "| C1 | 代码质量 | 10 | 7 | **8** | **6** | file:src/test.py:42\n"
    )
    proc3 = _run_scorecard({"tool_name": "Write", "tool_input": {
        "file_path": "scorecard.md",
        "content": WITH_EV_CONTENT,
    }})
    check("R4i scorecard-with-evidence exit 0", proc3.returncode == 0,
          f"rc={proc3.returncode}")
except Exception as e:
    infra_err(f"R4 subprocess: {e}")


# ════════════════════════════════════════════════════════════
# R5 — Redirect streak: 3rd occurrence stays recoverable
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R5: Redirect streak threshold (>=4 for block, not >=3)")
print("=" * 60)

_tmpdir5 = None
try:
    helpers = _ensure_helpers()
    _tmpdir5 = tempfile.mkdtemp()
    _streak_file5 = Path(_tmpdir5) / "redirect-streak.json"

    # Strike 1-3: count < 4, all recoverable
    for strike in range(1, 4):
        cnt = helpers._increment_streak("test-gate|test-reason", _streak_file5)
        check(f"R5a strike {strike} returns count={strike}", cnt == strike,
              f"got={cnt}")
        check(f"R5b strike {strike} recoverable (count < 4)", cnt < 4,
              f"got={cnt}")

    # Strike 4: count = 4 => hard_stop threshold
    cnt4 = helpers._increment_streak("test-gate|test-reason", _streak_file5)
    check("R5c strike 4 returns count=4", cnt4 == 4, f"got={cnt4}")
    check("R5d strike 4 triggers hard_stop (count >= 4)", cnt4 >= 4,
          f"got={cnt4}")

    # Different key => independent count
    cnt_other = helpers._increment_streak("other-gate|other-reason", _streak_file5)
    check("R5e different key starts at 1", cnt_other == 1, f"got={cnt_other}")
finally:
    if _tmpdir5 is not None:
        import shutil
        shutil.rmtree(_tmpdir5, ignore_errors=True)


# ════════════════════════════════════════════════════════════
# R6 — Edit-scope streak: independent threshold fix
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R6: Edit-scope streak threshold (>=4 for block, not >=3)")
print("=" * 60)

_tmpdir6 = None
try:
    helpers = _ensure_helpers()
    _tmpdir6 = tempfile.mkdtemp()
    _streak_file6 = Path(_tmpdir6) / "redirect-streak.json"

    # Edit-scope independent streak
    for strike in range(1, 4):
        cnt = helpers._increment_streak("edit-scope", _streak_file6)
        check(f"R6a edit-scope strike {strike} returns count={strike}", cnt == strike,
              f"got={cnt}")
        check(f"R6b edit-scope strike {strike} recoverable (count < 4)", cnt < 4,
              f"got={cnt}")

    cnt4 = helpers._increment_streak("edit-scope", _streak_file6)
    check("R6c edit-scope strike 4 returns count=4", cnt4 == 4, f"got={cnt4}")

    # Ensure no double-count: main gate streak key != "edit-scope"
    cnt_main = helpers._increment_streak("edit-scope|out-of-scope/file.txt", _streak_file6)
    check("R6d main redirect key returns 1 (indep. from edit-scope key)",
          cnt_main == 1, f"got={cnt_main}")
    cnt_main2 = helpers._increment_streak("edit-scope|out-of-scope/file.txt", _streak_file6)
    check("R6e main redirect key increments independently",
          cnt_main2 == 2, f"got={cnt_main2}")
finally:
    if _tmpdir6 is not None:
        import shutil
        shutil.rmtree(_tmpdir6, ignore_errors=True)


# ════════════════════════════════════════════════════════════
# R7 — TTL and gate/reason signature isolation
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R7: TTL and gate/reason signature isolation")
print("=" * 60)

_tmpdir7 = None
try:
    helpers = _ensure_helpers()
    _tmpdir7 = tempfile.mkdtemp()
    _streak_file7 = Path(_tmpdir7) / "redirect-streak.json"

    # numeric-claim: 2 pre-existing
    helpers._increment_streak("numeric-claim", _streak_file7)
    helpers._increment_streak("numeric-claim", _streak_file7)
    # claim-source starts fresh
    cnt_cs = helpers._increment_streak("claim-source", _streak_file7)
    check("R7a claim-source starts at 1 (independent)", cnt_cs == 1, f"got={cnt_cs}")

    # numeric-claim preserves its own count
    cnt_nc = helpers._increment_streak("numeric-claim", _streak_file7)
    check("R7b numeric-claim preserves count", cnt_nc == 3, f"got={cnt_nc}")

    # TTL: expired entries dropped
    old = int(time.time()) - 86400
    _streak_file7.write_text(json.dumps({
        "expired-gate|old-reason": {"c": 99, "t": old},
        "fresh-gate": {"c": 2, "t": int(time.time())},
    }))
    cnt_new = helpers._increment_streak("new-key", _streak_file7)
    check("R7c new key starts at 1 (after cleaning expired)", cnt_new == 1,
          f"got={cnt_new}")
    streak_data = json.loads(_streak_file7.read_text(encoding="utf-8"))
    check("R7d TTL expired entry dropped",
          "expired-gate|old-reason" not in streak_data,
          f"found keys={list(streak_data.keys())}")
    check("R7e TTL active entry preserved",
          "fresh-gate" in streak_data,
          f"missing, keys={list(streak_data.keys())}")
finally:
    if _tmpdir7 is not None:
        import shutil
        shutil.rmtree(_tmpdir7, ignore_errors=True)


# ════════════════════════════════════════════════════════════
# E1 — orchestrator.py passes edit-scope (no governance false alarm)
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("E1: orchestrator.py passes edit-scope")
print("=" * 60)

try:
    _install_paths()
    import importlib
    checks = importlib.import_module("pretool_gates.checks")

    payload = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": ".claude/workflows/frontend-overnight/orchestrator.py",
            "new_string": "updated content",
        }
    }
    result = checks._check_edit_scope(payload)
    check("E1 orchestrator.py passes edit-scope", result is None,
          f"got={result!r}")
except Exception as e:
    infra_err(f"E1 import/check: {e}")


# ════════════════════════════════════════════════════════════
# E2 — No invalid permissionDecision values in hook source
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("E2: permissionDecision only allow/deny/ask in source")
print("=" * 60)

LEGAL = {"allow", "deny", "ask"}
violations = 0
for hook_file in [
    "pretool-gate.py",
    "carroros-night-deny.py",
    "pretool-scorecard-gate.py",
    "pretool_gates/helpers.py",
    "pretool_gates/checks.py",
]:
    fpath = HOOKS_DIR / hook_file
    if not fpath.exists():
        continue
    text = fpath.read_text(encoding="utf-8")
    for m in re.finditer(r'"permissionDecision"\s*:\s*"([^"]+)"', text):
        val = m.group(1)
        if val not in LEGAL:
            check(f"E2 invalid permissionDecision={val!r} in {hook_file}",
                  False, f"invalid value found")
            violations += 1

if violations == 0:
    check("E2 no invalid permissionDecision values", True,
          "(no values found == no violations)")


# ════════════════════════════════════════════════════════════
# R8 — High-risk interactive _block: AskUserQuestion structure
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R8: High-risk _block produces AskUserQuestion structure")
print("=" * 60)

try:
    helpers = _ensure_helpers()
    # Goal-mode OFF -> interactive mode
    with _patched_goal_mode(False):
        with contextlib.redirect_stdout(io.StringIO()) as buf, \
             contextlib.redirect_stderr(io.StringIO()):
            helpers._block("destructive operation: rm -rf /data",
                           "use safe method")

    raw_high = buf.getvalue()
    output_high = json.loads(raw_high) if raw_high.strip() else {}
    hs_high = output_high.get("hookSpecificOutput")

    # With goal_mode=False, _block high-risk goes through GateKeeper
    # which returns ASK_USER (not SKIP). The non-skip path outputs:
    #   {"continue": false, "message": full_msg}
    # Desired: continue:true + hookSpecificOutput with AskUserQuestion

    check("R8a high-risk continue:true for interactive",
          output_high.get("continue") is True,
          f"got={output_high.get('continue')!r}")

    check("R8b high-risk has hookSpecificOutput",
          isinstance(hs_high, dict),
          f"got={type(hs_high).__name__ if hs_high is not None else 'None'}")

    if isinstance(hs_high, dict):
        ac_high = str(hs_high.get("additionalContext", ""))
        check("R8c high-risk additionalContext has options/choices",
              "选项" in ac_high or "options" in ac_high.lower(),
              f"got={ac_high[:120]!r}")
        check("R8d high-risk additionalContext has recommendation",
              "推荐" in ac_high or "recommend" in ac_high.lower(),
              f"got={ac_high[:120]!r}")
        check("R8e high-risk additionalContext has AskUserQuestion instruction",
              "AskUserQuestion" in ac_high,
              f"got={ac_high[:120]!r}")
except Exception as e:
    infra_err(f"R8 execution: {e}")


# ════════════════════════════════════════════════════════════
# R9 — Goal unattended mode: blocked-human/skip-risk
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("R9: Goal unattended mode produces blocked-human/skip-risk")
print("=" * 60)

try:
    helpers = _ensure_helpers()
    # Force unattended mode in-memory; never read or mutate the session marker files.
    with _patched_goal_mode(True):
        with contextlib.redirect_stdout(io.StringIO()) as buf, \
             contextlib.redirect_stderr(io.StringIO()):
            helpers._block("destructive: rm production data", "do not destroy")

    raw_goal = buf.getvalue()
    output_goal = json.loads(raw_goal) if raw_goal.strip() else {}
    hs_goal = output_goal.get("hookSpecificOutput")

    check("R9a goal continue:true",
          output_goal.get("continue") is True,
          f"got={output_goal.get('continue')!r}")

    if isinstance(hs_goal, dict):
        ac_goal = str(hs_goal.get("additionalContext", ""))
        check("R9b goal has blocked-human or skip-risk",
              "blocked-human" in ac_goal or "skip-risk" in ac_goal,
              f"got={ac_goal[:120]!r}")
        check("R9c goal has continue-other-work instruction",
              "continue other work" in ac_goal.lower(),
              f"got={ac_goal[:120]!r}")
        check("R9d goal has permissionDecision=deny",
              hs_goal.get("permissionDecision") == "deny",
              f"got={hs_goal.get('permissionDecision')!r}")
    else:
        check("R9b goal blocked-human (no hs)", False)
        check("R9c goal continue-other-work (no hs)", False)
        check("R9d goal permissionDecision (no hs)", False)

except Exception as e:
    infra_err(f"R9 execution: {e}")


# ════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Pass: {PASSES}")
print(f"  Contract failures (RED): {CONTRACT_FAILURES}")
print(f"  Infra errors: {INFRA_ERRORS}")
print(f"  Total: {PASSES + CONTRACT_FAILURES + INFRA_ERRORS}")

if INFRA_ERRORS > 0:
    print(f"\n  INFRASTRUCTURE ISSUES — some tests did not run.")
    sys.exit(2)

if CONTRACT_FAILURES > 0:
    print(f"\n  RED phase: {CONTRACT_FAILURES} contract assertions failed.")
    print(f"  This IS expected — production code needs GREEN implementation.")
    sys.exit(1)

print(f"\n  All desired behaviors already implemented. GREEN phase reached.")
sys.exit(0)
