#!/usr/bin/env python3
"""
test-pre-completion-gate.py — Tests for pre-completion-gate.py

Verifies:
1. Blocks TaskUpdate(completed) when no evidence files exist
2. Allows TaskUpdate when evidence exists (fresh < 5 min)
3. Allows TaskUpdate for non-completed status
4. Allows TaskUpdate when pre_completion_gate is disabled
5. Allows TaskUpdate in autonomous/ghost/goal mode
6. Blocks TaskUpdate when evidence is stale (> 5 min)
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


# Inject a fake harness_lib module so the hook can import it.
# This must happen before importing the hook module.
_fake_harness = mock.MagicMock()
_fake_harness.hc_enabled.return_value = True  # default on
_fake_harness.is_mode_active.return_value = False
_fake_harness.flywheel_event = mock.MagicMock()
_fake_harness.hc_emit_hook_json = mock.MagicMock()
sys.modules["harness_lib"] = _fake_harness


class TestPreCompletionGate(unittest.TestCase):
    """Test the pre-completion-gate hook logic in-process with mocked deps."""

    def setUp(self):
        # Set up a temp directory acting as .omc/state
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        self._state_dir = self._root / ".omc" / "state"
        self._tokens_dir = self._state_dir / "tokens"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._tokens_dir.mkdir(parents=True, exist_ok=True)

        # Reset harness_lib mock's default state for each test
        _fake_harness.reset_mock()
        _fake_harness.hc_enabled.return_value = True

        # Capture sys.exit calls and printed output
        self._exit_code = [0]
        self._stdout_lines = []
        self._stderr_lines = []

    def tearDown(self):
        self._tmpdir.cleanup()

    # ── Helpers ──────────────────────────────────────────────

    def _stdin_json(self, status: str = "completed") -> str:
        return json.dumps({
            "tool_input": {"status": status},
            "tool_name": "TaskUpdate",
        })

    def _run_hook(self, stdin_data: str,
                  hc_enabled: bool = True) -> dict:
        """
        Load pre-completion-gate.py as a fresh module with mocked deps
        and run main().  STATE_DIR and TOKENS_DIR are redirected to
        self._state_dir / self._tokens_dir.

        Returns {"stdout": dict | None, "stderr": str, "exit_code": int}.
        """
        import importlib.util

        hook_path = (Path(__file__).resolve().parent.parent /
                     ".claude" / "hooks" / "pre-completion-gate.py")
        if not hook_path.exists():
            self.fail(f"hook not found: {hook_path}")

        # Configure harness_lib mock
        _fake_harness.hc_enabled.return_value = hc_enabled

        # Capture print
        def fake_print(*args, file=None, **kwargs):
            text = " ".join(str(a) for a in args)
            if file is sys.stderr:
                self._stderr_lines.append(text)
            else:
                self._stdout_lines.append(text)

        def fake_exit(code=0):
            self._exit_code[0] = code
            raise SystemExit(code)

        # Load the hook source, compile it with overrides to STATE_DIR etc.
        source = hook_path.read_text(encoding="utf-8")

        # Rewrite STATE_DIR, TOKENS_DIR, PROJECT_ROOT at the source level
        # before compilation – the module-level assignments use Path(__file__)
        # so they compute real paths.  We inject our overrides at module
        # level by appending a re-assignment to the source.
        override_code = (
            "\n"
            "# --- test override ---\n"
            f"STATE_DIR = Path(r'{self._state_dir}')\n"
            f"TOKENS_DIR = Path(r'{self._tokens_dir}')\n"
            f"PROJECT_ROOT = Path(r'{self._root}')\n"
            "# --- end override ---\n"
        )

        # We need a unique module name per test to avoid caching
        mod_name = f"pre_completion_gate_{id(self)}"
        spec = importlib.util.spec_from_file_location(mod_name, hook_path)
        mod = importlib.util.module_from_spec(spec)

        with (
            mock.patch("builtins.print", fake_print),
            mock.patch("sys.exit", fake_exit),
            mock.patch("sys.stdin.read", return_value=stdin_data),
        ):
            code = compile(source + override_code, str(hook_path), "exec")
            exec(code, mod.__dict__)
            # Re-patch module globals (override_code already did this at
            # source level, so STATE_DIR/TOKENS_DIR/PROJECT_ROOT are correct)
            try:
                mod.main()
            except SystemExit:
                pass

        # Parse stdout JSON (last line)
        json_outputs = []
        for line in self._stdout_lines:
            try:
                json_outputs.append(json.loads(line))
            except json.JSONDecodeError:
                pass

        stdout_result = json_outputs[-1] if json_outputs else None
        stderr_result = "\n".join(self._stderr_lines).strip()
        exit_code = self._exit_code[0]

        return {
            "stdout": stdout_result,
            "stderr": stderr_result,
            "exit_code": exit_code,
        }

    # ══════════════════════════════════════════════════════════
    # Tests
    # ══════════════════════════════════════════════════════════

    # ── Verification 1: blocks when no evidence ──

    def test_blocks_when_no_evidence(self):
        """Blocks TaskUpdate(completed) when no evidence files exist."""
        result = self._run_hook(stdin_data=self._stdin_json("completed"))
        stdout = result["stdout"]
        self.assertIsNotNone(stdout)
        self.assertFalse(stdout.get("continue", True),
                         "Should block (continue=False) when no evidence")
        self.assertEqual(result["exit_code"], 2)

    # ── Verification 2: allows when fresh evidence exists ──

    def test_allows_when_fresh_evidence_exists(self):
        """Allows TaskUpdate when evidence exists (< 5 min old)."""
        date_str = time.strftime("%Y%m%d")
        ev_file = self._state_dir / f".completion-evidence-{date_str}"
        ev_file.write_text("verified: all tests passed", encoding="utf-8")

        result = self._run_hook(stdin_data=self._stdin_json("completed"))
        stdout = result["stdout"]
        self.assertIsNotNone(stdout)
        self.assertTrue(stdout.get("continue", False),
                        "Should allow when fresh evidence exists")

    # ── Verification 3: non-completed status passes through ──

    def test_allows_non_completed_status(self):
        """Allows TaskUpdate for non-completed status."""
        for s in ("pending", "in_progress", "deleted"):
            with self.subTest(status=s):
                result = self._run_hook(stdin_data=self._stdin_json(s))
                self.assertTrue(result["stdout"].get("continue", False),
                                f"Should pass through for status={s}")
                self.assertEqual(result["exit_code"], 0)

    # ── Verification 4: disabled gate passes through ──

    def test_allows_when_disabled(self):
        """Allows when pre_completion_gate is disabled."""
        result = self._run_hook(stdin_data=self._stdin_json("completed"),
                                hc_enabled=False)
        self.assertTrue(result["stdout"].get("continue", False),
                        "Should pass through when gate is disabled")
        self.assertEqual(result["exit_code"], 0)

    # ── Verification 5: autonomous / ghost / goal mode ──

    def _token_mode_bypasses(self, token_name, token_content):
        """Place a token file, run gate, assert it allows completed."""
        token_path = self._tokens_dir / token_name
        token_path.write_text(token_content, encoding="utf-8")

        result = self._run_hook(stdin_data=self._stdin_json("completed"))
        stdout = result["stdout"]
        self.assertIsNotNone(stdout)
        self.assertTrue(stdout.get("continue", False),
                        f"Should allow in {token_name} mode")
        self.assertEqual(result["exit_code"], 0)
        # stderr should carry the log message
        self.assertIn("自主模式", result["stderr"],
                      f"Should log autonomous-mode message for {token_name}")

    def test_allows_autonomous_mode(self):
        """Allows in autonomous mode (autonomous.active token)."""
        self._token_mode_bypasses("autonomous.active", "active")

    def test_allows_ghost_mode(self):
        """Allows in ghost mode (lx-ghost.json token)."""
        self._token_mode_bypasses("lx-ghost.json",
                                  json.dumps({"mode": "ghost"}))

    def test_allows_goal_mode(self):
        """Allows in goal mode (lx-goal.json token)."""
        self._token_mode_bypasses("lx-goal.json",
                                  json.dumps({"mode": "goal"}))

    # ── Verification 6: stale evidence is blocked ──

    def test_blocks_when_evidence_stale(self):
        """Blocks when evidence file is older than 5 minutes."""
        date_str = time.strftime("%Y%m%d")
        ev_file = self._state_dir / f".completion-evidence-{date_str}"
        ev_file.write_text("old evidence", encoding="utf-8")
        old_time = time.time() - 600  # 10 min ago
        os.utime(str(ev_file), (old_time, old_time))

        result = self._run_hook(stdin_data=self._stdin_json("completed"))
        stdout = result["stdout"]
        self.assertIsNotNone(stdout)
        self.assertFalse(stdout.get("continue", True),
                         "Should block when evidence is stale")
        self.assertEqual(result["exit_code"], 2)

    # ── Edge Cases ──

    def test_autonomous_overrides_stale_evidence(self):
        """Autonomous mode passes even if stale evidence exists."""
        date_str = time.strftime("%Y%m%d")
        ev_file = self._state_dir / f".completion-evidence-{date_str}"
        ev_file.write_text("stale", encoding="utf-8")
        old_time = time.time() - 600
        os.utime(str(ev_file), (old_time, old_time))

        token_path = self._tokens_dir / "autonomous.active"
        token_path.write_text("active", encoding="utf-8")

        result = self._run_hook(stdin_data=self._stdin_json("completed"))
        self.assertTrue(result["stdout"].get("continue", False),
                        "Autonomous mode should override stale evidence")

    def test_allowing_clears_blocked_file(self):
        """Allowing removes the completion-blocked file if it exists."""
        date_str = time.strftime("%Y%m%d")
        ev_file = self._state_dir / f".completion-evidence-{date_str}"
        ev_file.write_text("verified", encoding="utf-8")

        blocked_file = self._state_dir / "completion-blocked"
        blocked_file.write_text(
            json.dumps({"blocked_at": time.time(), "reason": "no_evidence"}),
            encoding="utf-8",
        )

        result = self._run_hook(stdin_data=self._stdin_json("completed"))
        self.assertTrue(result["stdout"].get("continue", False))
        self.assertFalse(blocked_file.exists(),
                         "completion-blocked should be removed on allow")

    def test_malformed_stdin_fails_open(self):
        """Fail-open on malformed stdin JSON."""
        result = self._run_hook(stdin_data="not valid json {{{")
        self.assertTrue(result["stdout"].get("continue", True),
                        "Should fail-open on bad JSON")
        self.assertEqual(result["exit_code"], 0)

    def test_null_tool_input_fails_open(self):
        """Fail-open when tool_input is null."""
        result = self._run_hook(
            stdin_data=json.dumps({"tool_input": None}),
        )
        self.assertTrue(result["stdout"].get("continue", True))
        self.assertEqual(result["exit_code"], 0)

    def test_blocked_file_created_on_block(self):
        """Blocking writes the completion-blocked file into state."""
        blocked_file = self._state_dir / "completion-blocked"
        self.assertFalse(blocked_file.exists(),
                         "Precondition: blocked file should not exist yet")

        result = self._run_hook(stdin_data=self._stdin_json("completed"))
        self.assertFalse(result["stdout"].get("continue", True))
        self.assertTrue(blocked_file.exists(),
                        "completion-blocked file should be created on block")
        content = json.loads(blocked_file.read_text(encoding="utf-8"))
        self.assertEqual(content.get("reason"), "no_evidence")
        self.assertIn("blocked_at", content)


if __name__ == "__main__":
    unittest.main()
