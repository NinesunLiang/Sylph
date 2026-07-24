#!/usr/bin/env python3
"""Test suite for session-end-lifecycle hook.

Verifies that seal_session_end (from lifecycle_ssot):
1. Sets mode to "idle"
2. Clears goal_id and ghost_id to None
3. Sets end.sealed to True
4. Delegates correctly (the hook main() imports and calls seal_session_end)
5. Is idempotent on replay of the same event_id
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# --- path setup -----------------------------------------------------------
HOOK_DIR = Path(__file__).resolve().parents[3] / ".claude" / "hooks"
sys.path.insert(0, str(HOOK_DIR))

from lib.lifecycle_ssot import (  # noqa: E402
    LIFECYCLE_PATH,
    _utc,
    default_lifecycle,
    load_lifecycle,
    seal_session_end,
)

TEST_ROOT = Path(tempfile.mkdtemp(prefix="test-session-end-"))
TEST_OMC = TEST_ROOT / ".omc"
TEST_STATE = TEST_OMC / "state"
# point lifecycle_ssot at the temp dir
os.environ["CLAUDE_PROJECT_DIR"] = str(TEST_ROOT)


def _write_lifecycle(data: dict) -> None:
    TEST_STATE.mkdir(parents=True, exist_ok=True)
    LIFECYCLE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_lifecycle() -> dict:
    return json.loads(LIFECYCLE_PATH.read_text(encoding="utf-8"))


def _make_hook_input(session_id: str = "test-sess") -> dict:
    return {
        "session_id": session_id,
        "hook_event_name": "Stop",
        "cwd": str(TEST_ROOT),
    }


# ---------------------------------------------------------------------------
#  Helper: patch _utc so timestamps are deterministic in assertions
# ---------------------------------------------------------------------------
_TEST_NOW = "2026-07-24T12:00:00Z"


def _patch_utc():
    import lib.lifecycle_ssot as ssot_mod
    ssot_mod._utc = lambda: _TEST_NOW


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------
def _reset() -> None:
    """Clean slate: remove state dir so next load returns default lifecycle."""
    if TEST_STATE.exists():
        import shutil
        shutil.rmtree(TEST_STATE)


def test_seals_session_end_sets_mode_idle() -> None:
    """1. seal_session_end sets mode to 'idle'."""
    _reset()
    lc = seal_session_end("evt-1", reason="Stop", hook_input=_make_hook_input())
    assert lc["mode"] == "idle", f"Expected idle, got {lc['mode']}"
    print("PASS: test_seals_session_end_sets_mode_idle")


def test_clears_goal_id() -> None:
    """2. goal_id is set to None after seal."""
    _reset()
    lc = seal_session_end("evt-2", reason="Stop", hook_input=_make_hook_input())
    assert lc.get("goal_id") is None, f"Expected None goal_id, got {lc.get('goal_id')}"
    print("PASS: test_clears_goal_id")


def test_clears_ghost_id() -> None:
    """3. ghost_id is set to None after seal."""
    _reset()
    lc = seal_session_end("evt-3", reason="Stop", hook_input=_make_hook_input())
    assert lc.get("ghost_id") is None, f"Expected None ghost_id, got {lc.get('ghost_id')}"
    print("PASS: test_clears_ghost_id")


def test_sets_end_sealed_true() -> None:
    """4. end.sealed is set to True after seal."""
    _reset()
    lc = seal_session_end("evt-4", reason="Stop", hook_input=_make_hook_input())
    sealed = lc.get("end", {}).get("sealed")
    assert sealed is True, f"Expected sealed=True, got {sealed}"
    print("PASS: test_sets_end_sealed_true")


def test_idempotent_same_event_id() -> None:
    """5. Calling seal_session_end twice with same event_id returns early (idempotent)."""
    _reset()
    lc1 = seal_session_end("evt-dup", reason="Stop", hook_input=_make_hook_input())
    end_at_1 = lc1.get("end", {}).get("last_session_end_at")

    # Small sleep so timestamp would differ if not idempotent
    import time as _time
    _time.sleep(0.01)

    lc2 = seal_session_end("evt-dup", reason="Stop", hook_input=_make_hook_input())
    end_at_2 = lc2.get("end", {}).get("last_session_end_at")

    assert end_at_1 == end_at_2, (
        f"Idempotent guard failed: timestamp changed {end_at_1} -> {end_at_2}"
    )
    print("PASS: test_idempotent_same_event_id")


def test_resets_from_goal_mode_to_idle() -> None:
    """6. Even when lifecycle was in goal mode, seal resets to idle."""
    _reset()
    lc = default_lifecycle()
    lc["mode"] = "goal"
    lc["goal_id"] = "goal-abc-123"
    _write_lifecycle(lc)

    sealed = seal_session_end("evt-goal", reason="Stop", hook_input=_make_hook_input())
    assert sealed["mode"] == "idle", f"Expected idle, got {sealed['mode']}"
    assert sealed.get("goal_id") is None, "goal_id should be None after seal"
    assert sealed.get("ghost_id") is None, "ghost_id should be None after seal"
    assert sealed["end"]["sealed"] is True, "should be sealed"
    print("PASS: test_resets_from_goal_mode_to_idle")


def test_resets_from_ghost_mode_to_idle() -> None:
    """7. Even when lifecycle was in ghost mode, seal resets to idle."""
    _reset()
    lc = default_lifecycle()
    lc["mode"] = "ghost"
    lc["ghost_id"] = "ghost-xyz-456"
    _write_lifecycle(lc)

    sealed = seal_session_end("evt-ghost", reason="Stop", hook_input=_make_hook_input())
    assert sealed["mode"] == "idle", f"Expected idle, got {sealed['mode']}"
    assert sealed.get("goal_id") is None
    assert sealed.get("ghost_id") is None
    assert sealed["end"]["sealed"] is True
    print("PASS: test_resets_from_ghost_mode_to_idle")


def test_no_event_id_still_seals() -> None:
    """8. seal_session_end works even without an event_id."""
    _reset()
    lc = seal_session_end(None, reason="ForceStop", hook_input=_make_hook_input())
    assert lc["mode"] == "idle"
    assert lc["end"]["sealed"] is True
    print("PASS: test_no_event_id_still_seals")


def test_hook_main_delegates_to_seal_session_end() -> None:
    """9. The hook's main() function correctly delegates to lifecycle_ssot.seal_session_end.

    Load via importlib (hook filename has hyphens), simulate stdin JSON,
    and verify the output JSON matches expected sealed/idle state.
    """
    _reset()
    import importlib.util
    hook_path = HOOK_DIR / "session-end-lifecycle.py"
    spec = importlib.util.spec_from_file_location("session_end_lifecycle", str(hook_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load hook module from {hook_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Simulate stdin for the hook's read_stdin_json() call
    hook_input = _make_hook_input("hook-sess-1")
    import io
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    sys.stdin = io.StringIO(json.dumps(hook_input))
    out_buf = io.StringIO()
    sys.stdout = out_buf

    try:
        ret = mod.main()
        assert ret == 0, f"main() returned {ret}, expected 0"

        output = json.loads(out_buf.getvalue().strip())
        assert output.get("ok") is True
        assert output.get("sealed") is True
        assert output.get("mode") == "idle"

        # Verify the lifecycle file directly
        disk_lc = _read_lifecycle()
        assert disk_lc["mode"] == "idle"
        assert disk_lc["goal_id"] is None
        assert disk_lc["ghost_id"] is None
        assert disk_lc["end"]["sealed"] is True
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout

    print("PASS: test_hook_main_delegates_to_seal_session_end")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------
def main() -> int:
    _patch_utc()
    tests = [
        test_seals_session_end_sets_mode_idle,
        test_clears_goal_id,
        test_clears_ghost_id,
        test_sets_end_sealed_true,
        test_idempotent_same_event_id,
        test_resets_from_goal_mode_to_idle,
        test_resets_from_ghost_mode_to_idle,
        test_no_event_id_still_seals,
        test_hook_main_delegates_to_seal_session_end,
    ]
    failures = 0
    for t in tests:
        try:
            t()
        except Exception as exc:
            print(f"FAIL: {t.__name__} -- {exc}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            failures += 1

    total = len(tests)
    passed = total - failures
    print(f"\nResults: {passed}/{total} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
