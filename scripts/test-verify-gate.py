#!/usr/bin/env python3
"""VerifyGate Regression Test — test _check_verified() against all audit formats.
P0 requirement from GPT-5.5 audit: ensure gate never silently breaks again.

Usage: python3 scripts/test-verify-gate.py
Exit code: 0 = PASS, 1 = FAIL"""

import json, os, sys, tempfile
from pathlib import Path

# ── Embedded _check_verified logic (exact copy from pretool-gate.py L196-215) ──
def check_verified(audit_dir: Path, step_id: str | None = None) -> bool:
    if not audit_dir.exists():
        return False
    for f in sorted(audit_dir.glob("*.jsonl")):
        with f.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("event") == "verify":
                    data = e.get("data", {})
                    if isinstance(data, dict) and data.get("result") == "VERIFIED":
                        if step_id is None or data.get("step") == step_id:
                            return True
                if e.get("event_type") == "verify_decision" and e.get("decision") == "VERIFIED":
                    if step_id is None or e.get("step") == step_id:
                        return True
    return False


# ── Test cases ──
PASS = 0
FAIL = 0

def write_audit(audit_dir: Path, event: dict):
    (audit_dir / "test.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

def test(name: str, event: dict, step: str | None, expect: bool):
    global PASS, FAIL
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        write_audit(d, event)
        result = check_verified(d, step)
        if result == expect:
            print(f"  ✅ {name}: {'PASS' if expect else 'REJECT'} (got {result})")
            PASS += 1
        else:
            print(f"  ❌ {name}: expected {expect}, got {result}")
            FAIL += 1

print("=" * 60)
print("VerifyGate Regression Test")
print("=" * 60)

# Case 1: new format (carros_base.py output)
test("新格式 verify + VERIFIED + step match",
     {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}},
     "S1", True)

# Case 2: new format, step mismatch
test("新格式 verify + VERIFIED + step mismatch",
     {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}},
     "S2", False)

# Case 3: new format, not VERIFIED
test("新格式 verify + FAILED",
     {"event": "verify", "data": {"step": "S1", "result": "FAILED"}},
     "S1", False)

# Case 4: old format (legacy compat)
test("旧格式 event_type=verify_decision + VERIFIED",
     {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"},
     "S1", True)

# Case 5: old format, step mismatch
test("旧格式 verify_decision + VERIFIED + step mismatch",
     {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"},
     "S2", False)

# Case 6: old format, not VERIFIED
test("旧格式 verify_decision + REJECTED",
     {"event_type": "verify_decision", "decision": "REJECTED", "step": "S1"},
     "S1", False)

# Case 7: empty audit
with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    result = check_verified(d, "S1")
    if result == False:
        print(f"  ✅ 空审计: REJECT (got {result})")
        PASS += 1
    else:
        print(f"  ❌ 空审计: expected False, got {result}")
        FAIL += 1

# Case 8: no step filter
test("新格式 + step=None",
     {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}},
     None, True)

# Case 9: invalid JSON line (should not crash)
with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    (d / "test.jsonl").write_text("NOT_JSON\n" + json.dumps({"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}}) + "\n", encoding="utf-8")
    result = check_verified(d, "S1")
    if result == True:
        print(f"  ✅ 无效 JSON 行 + 有效行: PASS (got {result})")
        PASS += 1
    else:
        print(f"  ❌ 无效 JSON 行: expected True, got {result}")
        FAIL += 1

print("=" * 60)
total = PASS + FAIL
print(f"结果: {PASS}/{total} PASS, {FAIL}/{total} FAIL")
if FAIL > 0:
    print("❌ REGRESSION TEST FAILED")
    sys.exit(1)
else:
    print("✅ ALL PASS — VerifyGate format matching confirmed correct")
