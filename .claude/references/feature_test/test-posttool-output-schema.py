#!/usr/bin/env python3
"""
test-posttool-output-schema.py — 单元测试 for posttool-output-schema.py

Tests:
1. Detects known schemas (verdict, gate_result, block_output, oracle_verdict, meta_oracle)
2. Warns on schema mismatch
3. Never blocks (always returns {"continue": true})
4. Edge cases (empty, non-JSON, malformed)

Usage:
    python3 scripts/test-posttool-output-schema.py
    # All tests:  python3 scripts/test-posttool-output-schema.py -v
"""

import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "posttool-output-schema.py"

PASS = 0
FAIL = 0
SKIP = 0

_red = "\033[91m"
_green = "\033[92m"
_yellow = "\033[93m"
_cyan = "\033[96m"
_reset = "\033[0m"


def _blue(msg: str) -> str:
    return f"\033[94m{msg}{_reset}"


def run_hook(payload: dict) -> dict:
    """Run the hook script with a payload on stdin, return parsed JSON output."""
    payload_str = json.dumps(payload, ensure_ascii=False)
    proc = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload_str,
        capture_output=True,
        text=True,
        timeout=15,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    out = json.loads(stdout) if stdout else {}
    out["_stderr"] = stderr
    return out


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        status = f"{_green}PASS{_reset}"
    else:
        FAIL += 1
        status = f"{_red}FAIL{_reset}"
    parts = [f"[{status}] {name}"]
    if detail:
        parts.append(f"  {detail}")
    print("\n".join(parts))


def section(title: str) -> None:
    print(f"\n{_cyan}=== {title} ==={_reset}")


# ──────────────────────────────────────────────
# Helper: construct PostToolUse-style payloads
# ──────────────────────────────────────────────

def ptuse_payload(result_val, tool_name: str = "test_tool") -> dict:
    """Wrap a result value in a canonical PostToolUse payload envelope."""
    return {
        "tool_use": {
            "tool_name": tool_name,
            "result": result_val,
        }
    }


# ─────────────────────────────
# 1. Known schema: verdict
# ─────────────────────────────

section("1. Verdict schema")

# 1a. Valid atomic verdict (all fields present)
out = run_hook(ptuse_payload({"verdict": "pass", "score": 1.0}))
check("1a. valid verdict pass", out["continue"] is True and out["_stderr"] == "")

# 1b. Valid verdict with blocked
out = run_hook(ptuse_payload({"verdict": "blocked", "score": 0}))
check("1b. valid verdict blocked", out["continue"] is True and out["_stderr"] == "")

# 1c. Valid Oracle-style verdict
out = run_hook(ptuse_payload({"verdict": "ACCEPT", "risk": "low", "score": 0.95, "reasons": ["ok"]}))
check("1c. valid oracle ACCEPT", out["continue"] is True and out["_stderr"] == "")

# 1d. Oracle REJECT with all fields
out = run_hook(ptuse_payload({"verdict": "REJECT", "risk": "high", "score": 0.2, "reasons": ["bad pattern"]}))
check("1d. valid oracle REJECT", out["continue"] is True and out["_stderr"] == "")

# 1e. Unknown verdict value — should warn but NOT block
out = run_hook(ptuse_payload({"verdict": "definitely_maybe", "score": 0.5}))
check("1e. unknown verdict warns", "unknown verdict" in out["_stderr"], detail=out["_stderr"])

# 1f. Score missing — should warn
out = run_hook(ptuse_payload({"verdict": "pass"}))
check("1f. missing score warns", "missing 'score'" in out["_stderr"], detail=out["_stderr"])

# 1g. Never blocks
check("1g. verdict never blocks", out["continue"] is True)

# 1h. Oracle missing "risk"
out = run_hook(ptuse_payload({"verdict": "ACCEPT", "score": 0.5, "reasons": ["ok"]}))
check("1h. oracle missing risk", "missing 'risk'" in out["_stderr"], detail=out["_stderr"])

# 1i. Oracle missing "reasons"
out = run_hook(ptuse_payload({"verdict": "ADVISORY", "risk": "medium", "score": 0.6}))
check("1i. oracle missing reasons", "missing or malformed 'reasons'" in out["_stderr"], detail=out["_stderr"])

# 1j. ESCALATE with correct fields
out = run_hook(ptuse_payload({"verdict": "ESCALATE", "risk": "high", "score": 0.0, "reasons": ["needs human"]}))
check("1j. oracle ESCALATE passes", out["continue"] is True and out["_stderr"] == "")

# 1k. ADVISORY passes clean
out = run_hook(ptuse_payload({"verdict": "ADVISORY", "risk": "low", "score": 0.75, "reasons": ["minor"]}))
check("1k. oracle ADVISORY passes", out["continue"] is True and out["_stderr"] == "")


# ─────────────────────────────
# 2. Known schema: gate_result
# ─────────────────────────────

section("2. Gate result schema")

# 2a. Valid gate result (all fields)
out = run_hook(ptuse_payload({"gate_name": "quality", "passed": True, "blockers": []}))
check("2a. valid gate_result", out["continue"] is True and out["_stderr"] == "")

# 2b. Multiple blockers (include score to avoid verdict-schema warning)
out = run_hook(ptuse_payload({"gate_name": "lint", "passed": False, "blockers": ["err1", "err2"], "verdict": "blocked", "score": 0.0}))
check("2b. gate_result with blockers", out["continue"] is True and out["_stderr"] == "")

# 2c. Missing gate_name
out = run_hook(ptuse_payload({"passed": True, "blockers": []}))
check("2c. missing gate_name warns", "missing 'gate_name'" in out["_stderr"], detail=out["_stderr"])

# 2d. Missing passed
out = run_hook(ptuse_payload({"gate_name": "test"}))
check("2d. missing passed warns", "missing 'passed'" in out["_stderr"], detail=out["_stderr"])

# 2e. Unknown verdict value
out = run_hook(ptuse_payload({"gate_name": "x", "passed": True, "verdict": "super_bad"}))
check("2e. unknown gate verdict warns", "unknown verdict" in out["_stderr"], detail=out["_stderr"])

# 2f. Never blocks
check("2f. gate_result never blocks", out["continue"] is True)

# 2g. passed=False with verdict=warn
out = run_hook(ptuse_payload({"gate_name": "style", "passed": False, "verdict": "warn"}))
check("2g. gate_result verdict=warn ok", out["continue"] is True and "unknown" not in out["_stderr"])

# 2h. No gate-related fields — clean
out = run_hook(ptuse_payload({"random_field": 42}))
check("2h. no gate fields no warning", out["_stderr"] == "")

# 2i. Non-string verdict flagged (hook flags unknown values even non-string)
out = run_hook(ptuse_payload({"gate_name": "test", "passed": True, "verdict": 123}))
check("2i. non-string verdict flagged", "unknown verdict" in out["_stderr"], detail=out["_stderr"])


# ─────────────────────────────
# 3. Known schema: block_output
# ─────────────────────────────

section("3. Block output schema")

# 3a. continue=false with block_type and reason — clean
out = run_hook(ptuse_payload({"continue": False, "block_type": "security", "reason": "unsafe"}))
check("3a. valid block_output", out["continue"] is True and out["_stderr"] == "")

# 3b. continue=true no warning
out = run_hook(ptuse_payload({"continue": True}))
check("3b. continue=true clean", out["_stderr"] == "")

# 3c. continue=false missing block_type
out = run_hook(ptuse_payload({"continue": False, "reason": "because"}))
check("3c. missing block_type warns", "missing 'block_type'" in out["_stderr"], detail=out["_stderr"])

# 3d. continue=false missing reason
out = run_hook(ptuse_payload({"continue": False, "block_type": "gate"}))
check("3d. missing reason warns", "missing 'reason'" in out["_stderr"], detail=out["_stderr"])

# 3e. Never blocks
check("3e. block_output never blocks", out["continue"] is True)


# ─────────────────────────────
# 4. Known schema: meta_oracle
# ─────────────────────────────

section("4. Meta-Oracle schema")

# 4a. Valid meta-oracle with all four gates
out = run_hook(ptuse_payload({
    "final_score": 0.85,
    "gates": {"G1": {}, "G2": {}, "G3": {}, "G4": {}},
}))
check("4a. valid meta_oracle", out["continue"] is True and out["_stderr"] == "")

# 4b. Missing gates (no gates key at all)
out = run_hook(ptuse_payload({"final_score": 0.9}))
check("4b. missing gates warns", "malformed 'gates'" in out["_stderr"] or "missing" in out["_stderr"], detail=out["_stderr"])

# 4c. Missing final_score
out = run_hook(ptuse_payload({"gates": {"G1": {}, "G2": {}, "G3": {}, "G4": {}}}))
check("4c. missing final_score warns", "missing 'final_score'" in out["_stderr"], detail=out["_stderr"])

# 4d. Gates not a dict
out = run_hook(ptuse_payload({"final_score": 0.0, "gates": [1, 2, 3]}))
check("4d. gates not dict warns", "malformed 'gates'" in out["_stderr"], detail=out["_stderr"])

# 4e. Missing one gate (G3 missing)
out = run_hook(ptuse_payload({
    "final_score": 0.5,
    "gates": {"G1": {}, "G2": {}, "G4": {}},
}))
check("4e. partial gates warns", "missing gates" in out["_stderr"], detail=out["_stderr"])

# 4f. Empty gates
out = run_hook(ptuse_payload({
    "final_score": 0.0,
    "gates": {},
}))
check("4f. empty gates warns", "missing gates" in out["_stderr"], detail=out["_stderr"])

# 4g. Never blocks
check("4g. meta_oracle never blocks", out["continue"] is True)


# ─────────────────────────────
# 5. Edge cases
# ─────────────────────────────

section("5. Edge cases")

# 5a. Empty JSON object
out = run_hook({})
check("5a. empty object", out["continue"] is True and out["_stderr"] == "")

# 5b. Non-JSON stdin (hook gracefully handles decode error)
with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    f.write("this is not json\n")
    tmp = f.name
proc = subprocess.run(
    [sys.executable, str(HOOK_PATH)],
    stdin=open(tmp, "r"),
    capture_output=True,
    text=True,
    timeout=15,
)
os.unlink(tmp)
out = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
check("5b. non-JSON input", out.get("continue") is True, detail=proc.stdout[:200])

# 5c. Result is a string (JSON-encoded inner)
inner = json.dumps({"verdict": "pass", "score": 1.0})
out = run_hook(ptuse_payload(inner))
check("5c. string result decoded", out["continue"] is True and out["_stderr"] == "")

# 5d. Nested result under "output" key
out = run_hook({"output": {"verdict": "warn", "score": 0.5}})
check("5d. output key parsed", out["continue"] is True)

# 5e. Nested result under "text" key
out = run_hook({"text": {"verdict": "blocked", "score": 0.0}})
check("5e. text key parsed", out["continue"] is True)

# 5f. Result is a list of dicts (batch items)
out = run_hook(ptuse_payload([
    {"verdict": "pass", "score": 1.0},
    {"gate_name": "lint", "passed": True},
]))
check("5f. list payload", out["continue"] is True and out["_stderr"] == "")

# 5g. Mixed valid/invalid in dict payload (hook unwraps dict results)
out = run_hook({"result": {"verdict": "unknown_verdict_value"}})
check("5g. fallback result warns", "unknown verdict" in out["_stderr"], detail=out["_stderr"])
check("5g. fallback never blocks", out["continue"] is True)

# 5h. Empty list
out = run_hook(ptuse_payload([]))
check("5h. empty list", out["continue"] is True and out["_stderr"] == "")

# 5i. None/null result
out = run_hook(ptuse_payload(None))
check("5i. null result", out["continue"] is True and out["_stderr"] == "")

# 5j. Missing tool_use entirely (bare payload fallback)
out = run_hook({"result": {"verdict": "pass", "score": 1.0}})
check("5j. bare result fallback", out["continue"] is True and out["_stderr"] == "")

# 5k. String result from "result" key that decodes to dict
out = run_hook({"result": '{"verdict": "blocked", "score": 0.0}'})
check("5k. string result fallback", out["continue"] is True and out["_stderr"] == "")


# ─────────────────────────────
# 6. Mixed / multiple schemas
# ─────────────────────────────

section("6. Mixed / overlapping schemas")

# 6a. Both verdict + gate_result fields
out = run_hook(ptuse_payload({
    "verdict": "pass",
    "score": 0.95,
    "gate_name": "build",
    "passed": True,
}))
check("6a. verdict+gate mixed", out["continue"] is True and out["_stderr"] == "")

# 6b. Both block_output + verdict, one bad
out = run_hook(ptuse_payload({
    "continue": False,
    "reason": "blocked by gate",
    "verdict": "invalid_verdict_here",
    "score": 0.0,
}))
check("6b. mixed with bad verdict", "unknown verdict" in out["_stderr"], detail=out["_stderr"])
check("6b. never blocks", out["continue"] is True)

# 6c. Overlapping oracle + meta oracle
out = run_hook(ptuse_payload({
    "verdict": "ACCEPT",
    "risk": "low",
    "score": 0.9,
    "reasons": ["good"],
    "final_score": 0.9,
    "gates": {"G1": {}, "G2": {}, "G3": {}, "G4": {}},
}))
check("6c. oracle+meta overlap", out["continue"] is True and out["_stderr"] == "")


# ─────────────────────────────
# 7. Never blocks — structural guarantee
# ─────────────────────────────

section("7. Never-blocks guarantee")

_all_results = []

# 7a. Random wild payloads
for wild in [
    {},
    {"continue": False},
    {"verdict": "garbage"},
    {"gate_name": "test", "passed": False},
    {"final_score": -1, "gates": {}},
    {"continue": False, "block_type": "x"},
    {"verdict": "ACCEPT", "score": 0.5},
    {"result": {"verdict": "bad"}},
    {"tool_use": {"result": None}},
]:
    out = run_hook(wild)
    check(f"7a. never blocks: {str(wild)[:60]}", out.get("continue") is True, detail=out.get("_stderr", "")[:120])
    _all_results.append(out)

# 7b. hookSpecificOutput only set when warnings present
any_hso = any(r.get("hookSpecificOutput") for r in _all_results)
some_warn = any(r.get("_stderr", "") for r in _all_results)
check("7b. hookSpecificOutput matches warnings", any_hso == some_warn)

# 7c. continue is always a boolean True
for r in _all_results:
    check("7c. continue is bool True", r.get("continue") is True)


# ─────────────────────────────
# Summary
# ─────────────────────────────

print(f"\n{'='*50}")
total = PASS + FAIL + SKIP
print(f"Results: {_green}{PASS} passed{_reset} | {_red}{FAIL} failed{_reset} | {_yellow}{SKIP} skipped{_reset} | {_blue}{total} total{_reset}")
if FAIL:
    print(f"{_red}FAILURES DETECTED{_reset}")
    sys.exit(1)
else:
    print(f"{_green}ALL TESTS PASSED{_reset}")
