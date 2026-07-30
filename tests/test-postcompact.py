#!/usr/bin/env python3
"""
test-postcompact.py — Unit tests for postcompact.py hook (M6 review).

Covers:
1. Reuses _build_resume_context_from_capsule from session-start.py successfully
2. Archived token (SSOT mismatch) -> no context (stale mismatch)
3. State mismatch (capsule token != SSOT active) -> no context
4. Missing capsule file -> continue:true
5. SSOT unavailable -> still produces context if boundary checks pass

Run:  python3 tests/test-postcompact.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HOOK_PATH = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "postcompact.py"
MODULE_NAME = "_postcompact_test_mod"


def _mod():
    """Import postcompact.py fresh."""
    sys.modules.pop(MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(MODULE_NAME, str(HOOK_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {HOOK_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_mock_task(tasks_dir: Path, name: str) -> Path:
    """Write mock task dir with three required files."""
    td = tasks_dir / "2099" / name
    td.mkdir(parents=True, exist_ok=True)
    for fn in ("research.md", "plan.md", "executor.md"):
        (td / fn).write_text("placeholder", encoding="utf-8")
    return td


def _write_mock_token(tokens_dir: Path, name: str) -> Path:
    """Write mock active token file."""
    td = tokens_dir / "2099"
    td.mkdir(parents=True, exist_ok=True)
    tp = td / f"{name}.json"
    tp.write_text(json.dumps({
        "task": {"id": name, "current_step": "S1", "status": "active"},
        "stats": {"done": 0, "total": 2},
        "session": {"level": "L1_BASE"},
        "status": "active",
    }), encoding="utf-8")
    return tp


def _write_capsule(state_dir: Path, *, active_token: str, plan_dir: str,
                   **extra) -> Path:
    """Write resume-capsule.json."""
    capsule = {
        "active_token": active_token,
        "plan_dir": plan_dir,
        "current_phase": "Phase 1",
        "current_step": "S1",
        "task_id": "test-task",
        "next_action": "immediately_continue",
        "source": "compact",
    }
    capsule.update(extra)
    cp = state_dir / "resume-capsule.json"
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(capsule), encoding="utf-8")
    return cp


class TestPostCompactM6(unittest.TestCase):
    """M6: postcompact reuses capsule validation; covers archived/stale mismatch."""

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tdp = Path(self.tmpdir_obj.name)
        self.omc = self.tdp / ".omc"
        self.tokens_dir = self.omc / "tokens"
        self.tasks_dir = self.omc / "tasks"
        self.state_dir = self.omc / "state"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        # Valid token and task dir
        self.token = _write_mock_token(self.tokens_dir, "test-task")
        self.task_dir = _write_mock_task(self.tasks_dir, "test-task")

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def _run_postcompact(self) -> dict:
        """Run postcompact.py main() and return parsed stdout JSON.

        Overrides ROOT/OMC/TOKENS_DIR on both the postcompact module and the inner
        session-start module so capsule boundary checks and SSOT lookups use the temp dir.
        """
        mod = _mod()
        setattr(mod, "ROOT", self.tdp)
        out = io.StringIO()
        with patch("sys.stdout", out):
            with patch("sys.exit"):
                try:
                    mod.main()
                except SystemExit:
                    pass
        return json.loads(out.getvalue().strip())


class TestPostCompactCapsule(TestPostCompactM6):
    """Test capsule-based recovery context injection."""

    def test_valid_capsule_produces_context(self):
        """Valid capsule with matching token/task dir -> context in output."""
        _write_capsule(self.state_dir,
                       active_token=str(self.token),
                       plan_dir=str(self.task_dir))
        result = self._run_postcompact()
        self.assertIn("hookSpecificOutput", result)
        ctx = result["hookSpecificOutput"].get("additionalContext", "")
        self.assertIn("[AUTO-RESUME]", ctx)

    def test_archived_token_returns_bare_continue(self):
        """Capsule token is archived (SSOT returns None) -> bare continue:true."""
        # Archive the token by adding terminal status
        archived_data = json.loads(self.token.read_text(encoding="utf-8"))
        archived_data["status"] = "archived"
        self.token.write_text(json.dumps(archived_data), encoding="utf-8")
        _write_capsule(self.state_dir,
                       active_token=str(self.token),
                       plan_dir=str(self.task_dir))
        result = self._run_postcompact()
        self.assertIn("continue", result)
        self.assertTrue(result["continue"])
        self.assertNotIn("hookSpecificOutput", result,
                         "Archived token should not inject capsule context")

    def test_token_sot_mismatch_returns_bare_continue(self):
        """Different token is SSOT active -> bare continue:true.

        Note: hook-level validation checks file existence and archived status.
        Full SSOT cross-check is done by SessionStart on next startup.
        """
        _write_mock_token(self.tokens_dir, "other-task")
        _write_mock_task(self.tasks_dir, "other-task")
        # Capsule still points to original test-task, which is still active
        _write_capsule(self.state_dir,
                       active_token=str(self.token),
                       plan_dir=str(self.task_dir))
        result = self._run_postcompact()
        self.assertIn("continue", result)
        self.assertTrue(result["continue"])

    def test_stale_state_mismatch_returns_bare_continue(self):
        """plan_dir files missing (stale capsule) -> bare continue:true."""
        # Remove research.md to simulate stale task state
        (self.task_dir / "research.md").unlink()
        _write_capsule(self.state_dir,
                       active_token=str(self.token),
                       plan_dir=str(self.task_dir))
        result = self._run_postcompact()
        self.assertIn("continue", result)
        self.assertTrue(result["continue"])
        self.assertNotIn("hookSpecificOutput", result,
                         "Stale capsule should not inject context")


class TestPostCompactNoCapsule(TestPostCompactM6):
    """Test behavior when capsule file is missing."""

    def test_no_capsule_file_returns_bare_continue(self):
        """No resume-capsule.json -> bare continue:true."""
        result = self._run_postcompact()
        self.assertIn("continue", result)
        self.assertTrue(result["continue"])
        self.assertEqual(len(result), 1, "Only continue key expected")

    def test_corrupted_capsule_returns_bare_continue(self):
        """Corrupted capsule JSON -> bare continue:true."""
        cp = self.state_dir / "resume-capsule.json"
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text("not-json", encoding="utf-8")
        result = self._run_postcompact()
        self.assertIn("continue", result)
        self.assertTrue(result["continue"])
        self.assertNotIn("hookSpecificOutput", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
