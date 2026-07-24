#!/usr/bin/env python3
"""
test-meta-oracle.py — Verification tests for .claude/scripts/meta_oracle.py

Validates:
1. _latest_task_id() returns str | None (function exists)
2. score_task() returns a dict with expected keys
3. TOKENS_DIR path exists
4. GATE_WEIGHTS are defined
"""

import os
import sys
import json
import types
from pathlib import Path

# ── Add project root and script dir to sys.path ──
HERE = Path(__file__).resolve().parent.parent
REPO_ROOT = HERE
SCRIPT_DIR = REPO_ROOT / ".claude" / "scripts"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT))

# ── Import target module ──
# Use importlib to avoid .pyc conflicts in .claude/scripts/
import importlib.util

spec = importlib.util.spec_from_file_location(
    "meta_oracle", str(SCRIPT_DIR / "meta_oracle.py")
)
mo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mo)


def _check(condition: bool, msg: str) -> None:
    """Simple assertion with label."""
    if not condition:
        print(f"  FAIL: {msg}", flush=True)
        sys.exit(1)
    print(f"  PASS: {msg}", flush=True)


def test_latest_task_id_exists_and_returns_str_or_none():
    """Verify _latest_task_id() is a callable function returning str | None."""
    assert hasattr(mo, "_latest_task_id"), "_latest_task_id not found in module"
    assert isinstance(mo._latest_task_id, types.FunctionType), "_latest_task_id is not a function"

    result = mo._latest_task_id()
    assert result is None or isinstance(result, str), (
        f"_latest_task_id() returned {type(result).__name__}, expected str | None"
    )
    return_type = type(result).__name__ if result is not None else "None"
    _check(True, f"_latest_task_id() returns {return_type}")


def test_score_task_returns_dict_with_expected_keys():
    """Verify score_task() exists and returns a dict with required keys."""
    assert hasattr(mo, "score_task"), "score_task not found in module"
    assert isinstance(mo.score_task, types.FunctionType), "score_task is not a function"

    # Ensure output directory exists for the dummy task, then clean up
    dummy_id = "__test_dummy_meta_oracle_check__"
    out_dir = mo.META_VERDICTS_DIR / dummy_id
    out_dir.mkdir(parents=True, exist_ok=True)

    result = mo.score_task(dummy_id)

    # Clean up dummy output
    import shutil
    shutil.rmtree(out_dir, ignore_errors=True)

    assert isinstance(result, dict), f"score_task returned {type(result).__name__}, expected dict"

    required_keys = {"task_id", "timestamp", "final_score", "verdict", "gates"}
    missing = required_keys - set(result.keys())
    assert not missing, f"score_task() result missing keys: {missing}"
    _check(True, f"score_task() returns dict with all required keys ({', '.join(sorted(required_keys))})")

    # Verify verdict is one of the expected values
    assert result["verdict"] in ("ACCEPT", "ADVISORY", "REJECT"), (
        f"Unexpected verdict: {result['verdict']}"
    )
    _check(True, f"verdict '{result['verdict']}' is valid")

    # Verify gates dict has G1-G4 entries
    for gid in ("G1", "G2", "G3", "G4"):
        assert gid in result["gates"], f"Missing gate {gid} in result"
        assert "score" in result["gates"][gid], f"Missing score in gate {gid}"
        assert "pass" in result["gates"][gid], f"Missing pass in gate {gid}"
        assert "reasons" in result["gates"][gid], f"Missing reasons in gate {gid}"
    _check(True, "gates contains G1-G4 with score/pass/reasons")

    # Verify final_score is a number
    assert isinstance(result["final_score"], (int, float)), (
        f"final_score is {type(result['final_score']).__name__}, expected int/float"
    )
    _check(True, f"final_score={result['final_score']} is numeric")


def test_tokens_dir_exists():
    """Verify TOKENS_DIR path attribute exists on disk."""
    assert hasattr(mo, "TOKENS_DIR"), "TOKENS_DIR not found in module"
    tokens_dir = mo.TOKENS_DIR
    path = Path(tokens_dir) if isinstance(tokens_dir, str) else tokens_dir
    assert path.exists(), f"TOKENS_DIR path does not exist: {path}"
    _check(True, f"TOKENS_DIR exists: {path}")


def test_gate_weights_defined():
    """Verify GATE_WEIGHTS is a dict with G1-G4 entries summing to ~1.0."""
    assert hasattr(mo, "GATE_WEIGHTS"), "GATE_WEIGHTS not found in module"
    weights = mo.GATE_WEIGHTS
    assert isinstance(weights, dict), f"GATE_WEIGHTS is {type(weights).__name__}, expected dict"

    for gid in ("G1", "G2", "G3", "G4"):
        assert gid in weights, f"Missing weight for {gid}"
        assert isinstance(weights[gid], (int, float)), (
            f"GATE_WEIGHTS[{gid}] is {type(weights[gid]).__name__}, expected number"
        )
    total = sum(weights.values())
    assert 0.99 <= total <= 1.01, f"GATE_WEIGHTS sum = {total}, expected ~1.0"
    _check(True, f"GATE_WEIGHTS defined with G1-G4 (sum={total})")


def main() -> int:
    print("meta_oracle.py verification tests", flush=True)
    print("=" * 40, flush=True)

    test_latest_task_id_exists_and_returns_str_or_none()
    test_score_task_returns_dict_with_expected_keys()
    test_tokens_dir_exists()
    test_gate_weights_defined()

    print("=" * 40, flush=True)
    print("All tests passed.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
