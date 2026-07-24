#!/usr/bin/env python3
"""
test-pretool-write-lock.py — Unit tests for pretool-write-lock.py

Tests:
1. Allows normal writes when no lock conflict
2. Fail-open on lock manager errors
3. Non-write tool passthrough
4. hc_enabled=False skip
5. Ghost/Goal mode downgrade
6. JSON stdin with tool_name / tool / args.filePath / file_path
7. Regex fallback for malformed JSON
8. Missing file_path passthrough
9. Lock manager non-zero exit fail-open

Run: pytest scripts/test-pretool-write-lock.py -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

# ── project root helpers ──
SCRIPT_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SCRIPT_DIR
HOOK_PATH = PROJECT_ROOT / ".claude" / "hooks" / "pretool-write-lock.py"

# Load the hook module via importlib so we can patch its direct bindings.
import importlib.util

HOOK_MODULE_PATH = str(PROJECT_ROOT / ".claude" / "hooks" / "pretool-write-lock.py")
_hook_spec = importlib.util.spec_from_file_location("_pwl_hook", HOOK_MODULE_PATH)
pwl = importlib.util.module_from_spec(_hook_spec)
sys.modules["_pwl_hook"] = pwl
# Insert hooks dir so harness_lib/harness_core resolve
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "hooks"))
_hook_spec.loader.exec_module(pwl)


class TestPretoolWriteLock(unittest.TestCase):
    """Main test suite for pretool-write-lock.py."""

    def setUp(self):
        """Per-test setup: patch the hook's direct bindings."""
        # The hook does `from harness_lib import hc_enabled, ...` at module
        # level, so pwl.hc_enabled etc. are direct references.  We must
        # patch those bindings directly, not the source modules.
        self.hc_enabled_patch = mock.patch.object(pwl, "hc_enabled", return_value=True)
        self.mock_hc_enabled = self.hc_enabled_patch.start()

        self.flywheel_patch = mock.patch.object(pwl, "flywheel_event")
        self.mock_flywheel = self.flywheel_patch.start()

        self.output_continue_patch = mock.patch.object(pwl, "output_continue")
        self.mock_output_continue = self.output_continue_patch.start()

        self.is_mode_active_patch = mock.patch.object(pwl, "is_mode_active", return_value="normal")
        self.mock_is_mode_active = self.is_mode_active_patch.start()

        # subprocess.run — also a module-level name that pwl holds
        self.subprocess_run_patch = mock.patch.object(pwl.subprocess, "run")
        self.mock_subprocess_run = self.subprocess_run_patch.start()
        self._mock_subprocess_success()

    def tearDown(self):
        self.hc_enabled_patch.stop()
        self.flywheel_patch.stop()
        self.output_continue_patch.stop()
        self.is_mode_active_patch.stop()
        self.subprocess_run_patch.stop()

    # ── helpers ──

    def _mock_subprocess_success(self):
        completed = mock.MagicMock()
        completed.returncode = 0
        completed.stdout = ""
        completed.stderr = ""
        self.mock_subprocess_run.return_value = completed

    def _mock_subprocess_failure(self, returncode=1):
        completed = mock.MagicMock()
        completed.returncode = returncode
        completed.stdout = ""
        completed.stderr = "lock error"
        self.mock_subprocess_run.return_value = completed

    def _mock_subprocess_exception(self):
        self.mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd=["python3", "oma_lock_manager.py", "acquire", "/tmp/test.py", "test"],
            timeout=30,
        )

    def _run_main_with_stdin(self, stdin_data):
        with mock.patch.object(pwl, "sys") as mock_sys:
            mock_sys.stdin.read.return_value = stdin_data
            pwl.main()

    def _assert_continue_called(self):
        self.mock_output_continue.assert_called_once()

    def _assert_continue_not_called(self):
        self.mock_output_continue.assert_not_called()

    def _assert_flywheel_error(self):
        calls = self.mock_flywheel.call_args_list
        error_calls = [c for c in calls if len(c[0]) > 1 and c[0][1] == "error"]
        self.assertGreaterEqual(
            len(error_calls), 1,
            "Expected at least one flywheel error event",
        )

    # ── Tests ──

    def test_normal_write_allowed(self):
        """1. Normal write operation proceeds when no lock conflict."""
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_write.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_called_once()

    def test_lock_manager_error_fail_open(self):
        """2a. Lock manager non-zero exit -> fail-open (continue)."""
        self._mock_subprocess_failure(returncode=1)
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_fail.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self._assert_flywheel_error()

    def test_lock_manager_exception_fail_open(self):
        """2b. Lock manager exception -> fail-open (continue)."""
        self._mock_subprocess_exception()
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_exc.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self._assert_flywheel_error()

    def test_non_write_tool_passthrough(self):
        """3. Non-write tools (Read, Bash, etc.) pass through without lock."""
        for tool in ["Read", "Bash", "WebFetch", "LSP"]:
            self.mock_output_continue.reset_mock()
            self.mock_subprocess_run.reset_mock()
            stdin_data = json.dumps({
                "tool_name": tool,
                "args": {"filePath": "/tmp/test.py"},
            })
            self._run_main_with_stdin(stdin_data)
            self._assert_continue_called()
            self.mock_subprocess_run.assert_not_called()

    def test_hc_disabled_skips(self):
        """4. hc_enabled=False skips the hook entirely."""
        self.mock_hc_enabled.return_value = False
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_disabled.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_not_called()

    def test_ghost_mode_downgrade(self):
        """5a. Ghost mode downgrades: logs and continues without lock."""
        self.mock_is_mode_active.return_value = "ghost"
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_ghost.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_not_called()

    def test_goal_mode_downgrade(self):
        """5b. Goal mode downgrades: logs and continues without lock."""
        self.mock_is_mode_active.return_value = "goal"
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_goal.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_not_called()

    def test_tool_input_file_path(self):
        """6. Accepts file_path inside tool_input dict."""
        stdin_data = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/test_tool_input.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_called_once()

    def test_tool_key_json_stdin(self):
        """6b. Accepts 'tool' key instead of 'tool_name'."""
        stdin_data = json.dumps({
            "tool": "write",
            "args": {"filePath": "/tmp/test_tool_key.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()

    def _run_main_with_stdin_and_json_fail(self, stdin_data):
        """Run main() where json.loads raises JSONDecodeError, but pwl.json.JSONDecodeError stays real."""
        orig_loads = pwl.json.loads
        def _fail(*_a, **_kw):
            raise json.JSONDecodeError("mock fail", "doc", 0)
        pwl.json.loads = _fail
        try:
            with mock.patch.object(pwl, "sys") as mock_sys:
                mock_sys.stdin.read.return_value = stdin_data
                pwl.main()
        finally:
            pwl.json.loads = orig_loads

    def test_regex_tool_name_fallback(self):
        """7a. Regex fallback extracts tool_name when JSON parse fails."""
        stdin_data = json.dumps({
            "tool_name": "Edit",
            "args": {"filePath": "/tmp/test_regex.py"},
        })
        self._run_main_with_stdin_and_json_fail(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_called_once()

    def test_regex_file_path_fallback(self):
        """7b. Regex fallback extracts filePath when JSON dict missing it."""
        stdin_data = '{"tool_name": "Write", "args": {}, "filePath": "/tmp/test_regex_fp.py"}'
        self._run_main_with_stdin_and_json_fail(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_called_once()

    def test_regex_file_path_underscore_fallback(self):
        """7c. Regex fallback extracts file_path (underscore)."""
        stdin_data = '{"tool_name": "Write", "args": {}, "file_path": "/tmp/test_regex_under.py"}'
        self._run_main_with_stdin_and_json_fail(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_called_once()

    def test_missing_file_path_passthrough(self):
        """8. Missing file_path -> passthrough (continue without lock call)."""
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_not_called()

    def test_empty_stdin_graceful(self):
        """8b. Empty stdin -> graceful passthrough."""
        self._run_main_with_stdin("")
        self._assert_continue_called()
        self.mock_subprocess_run.assert_not_called()

    def test_junk_stdin_graceful(self):
        """8c. Junk stdin (not JSON, no regex match) -> graceful passthrough."""
        self._run_main_with_stdin("not json at all and no tool name here")
        self._assert_continue_called()
        self.mock_subprocess_run.assert_not_called()

    def test_write_tool_variant_replace(self):
        """6d. 'replace' and 'str_replace' also trigger lock."""
        for tool in ["replace", "str_replace"]:
            self.mock_output_continue.reset_mock()
            self.mock_subprocess_run.reset_mock()
            stdin_data = json.dumps({
                "tool_name": tool,
                "args": {"filePath": "/tmp/test_replace.py"},
            })
            self._run_main_with_stdin(stdin_data)
            self._assert_continue_called()
            self.mock_subprocess_run.assert_called_once()

    def test_edit_tool_triggers_lock(self):
        """6e. 'edit' tool triggers lock."""
        stdin_data = json.dumps({
            "tool_name": "edit",
            "args": {"filePath": "/tmp/test_edit.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_called_once()

    def test_lock_manager_called_with_correct_args(self):
        """Check lock manager is called with correct subprocess args."""
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_correct_args.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self.mock_subprocess_run.assert_called_once()
        args, kwargs = self.mock_subprocess_run.call_args
        cmd = args[0]
        cmd_str = " ".join(str(part) for part in cmd)
        self.assertIn("oma_lock_manager.py", cmd_str)
        self.assertIn("acquire", cmd_str)
        self.assertIn("/tmp/test_correct_args.py", cmd_str)
        self.assertEqual(kwargs.get("timeout"), 30)
        self.assertTrue(kwargs.get("capture_output"))

    def test_mode_file_not_found_still_normal(self):
        """Mode detection with missing token files returns normal."""
        self.mock_is_mode_active.return_value = "normal"
        stdin_data = json.dumps({
            "tool_name": "Write",
            "args": {"filePath": "/tmp/test_mode_default.py"},
        })
        self._run_main_with_stdin(stdin_data)
        self._assert_continue_called()
        self.mock_subprocess_run.assert_called_once()


class TestPretoolWriteLockIntegration(unittest.TestCase):
    """Integration-style tests that run the hook as a subprocess."""

    HOOK_SCRIPT = str(PROJECT_ROOT / ".claude" / "hooks" / "pretool-write-lock.py")

    def test_hook_imports_load_cleanly(self):
        """Verify the hook module dependencies can be imported without error."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.claude/hooks'); "
             "from harness_core import output_continue, flywheel_event, hc_enabled; "
             "print('OK')"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=10,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("OK", result.stdout)

    def test_hook_syntax_valid(self):
        """Verify hook script compiles without SyntaxError."""
        result = subprocess.run(
            [sys.executable, "-c",
             f"import py_compile; py_compile.compile({self.HOOK_SCRIPT!r}, doraise=True); print('OK')"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
