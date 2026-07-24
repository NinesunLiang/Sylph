#!/usr/bin/env python3
"""Test: pretool-purify-gate.py — Three verification axes.

1. Only triggers on governance files (.claude/, .opencode/, .cursor/, AGENTS.md, CLAUDE.md, VERSION.json)
2. Does NOT block — always returns {"continue": true}
3. Returns {"continue": true} (no hookSpecificOutput) for non-governance files
"""

import importlib.util
import json
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Ensure hooks dir is on sys.path before loading module (needed for `from harness_lib import ...`)
_hooks_dir = str(Path(__file__).resolve().parent.parent / ".claude" / "hooks")
sys.path.insert(0, _hooks_dir)

# Load module under test (file has hyphens, so can't use regular import)
_hook_path = _hooks_dir + "/pretool-purify-gate.py"
_spec = importlib.util.spec_from_file_location("pretool_purify_gate", _hook_path)
pretool_purify_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pretool_purify_gate)

# Reusable mock for harness_lib functions
MOCK_ENABLED = True


def _mock_hc_enabled(name: str) -> bool:
    return MOCK_ENABLED


def _mock_flywheel_event(*args, **kwargs):
    pass  # no-op


def _run_gate(tool_input: dict) -> dict:
    """Feed a tool_input dict into the gate and return the parsed stdout."""
    input_data = json.dumps({"tool_input": tool_input})
    out = StringIO()
    err = StringIO()
    # Patch the local references in the module under test (not harness_lib),
    # because `from harness_lib import hc_enabled` binds a local name.
    with patch("sys.stdin", StringIO(input_data)), \
         patch("sys.stdout", out), \
         patch("sys.stderr", err), \
         patch.object(pretool_purify_gate, "hc_enabled", _mock_hc_enabled), \
         patch.object(pretool_purify_gate, "flywheel_event", _mock_flywheel_event):
        try:
            pretool_purify_gate.main()
        except SystemExit:
            pass
    return json.loads(out.getvalue())


class TestPretoolPurifyGate(unittest.TestCase):
    """Verification: pretool-purify-gate.py behavior."""

    # ── Governance file patterns — should produce hookSpecificOutput ──

    GOV_PATHS = [
        ".claude/hooks/pretool-purify-gate.py",
        ".claude/settings.json",
        ".claude/rules/bash-style.md",
        ".opencode/config.yaml",
        ".cursor/rules/my-rule.yaml",
        ".claude/AGENTS.md",
        "AGENTS.md",
        ".claude/CLAUDE.md",
        "CLAUDE.md",
        ".claude/VERSION.json",
        "VERSION.json",
    ]

    def test_governance_files_produce_hook_specific_output(self):
        """Verify #1: governance files get hookSpecificOutput with additionalContext."""
        for path in self.GOV_PATHS:
            with self.subTest(path=path):
                result = _run_gate({"file_path": path})
                self.assertIn("hookSpecificOutput", result,
                              f"Expected hookSpecificOutput for governance path: {path}")
                hso = result["hookSpecificOutput"]
                self.assertIn("additionalContext", hso,
                              f"Expected additionalContext in output for: {path}")
                ctx = hso["additionalContext"]
                self.assertIn(path, ctx,
                              f"additionalContext should reference the file path: {path}")
                self.assertIn("lx-purify", ctx,
                              "additionalContext should mention lx-purify")

    def test_governance_files_never_block(self):
        """Verify #2: governance files always return continue=true."""
        for path in self.GOV_PATHS:
            with self.subTest(path=path):
                result = _run_gate({"file_path": path})
                self.assertIs(result.get("continue"), True,
                              f"Governance path should not block: {path}")

    def test_governance_nested_in_project_dir(self):
        """Deeply nested governance path still triggers."""
        result = _run_gate({"file_path": "/home/user/my-project/.claude/hooks/some-hook.py"})
        self.assertIn("hookSpecificOutput", result,
                      "Deep .claude/ path should trigger")

    def test_governance_mixed_path_components(self):
        """Path with .claude as part of a directory segment name."""
        result = _run_gate({"file_path": "/home/user/.claude-foo/file.txt"})
        self.assertNotIn("hookSpecificOutput", result,
                         "'.claude-foo' should not match '.claude/' pattern")

    # ── Non-governance files — must have NO hookSpecificOutput ──

    NON_GOV_PATHS = [
        "src/main.py",
        "/home/user/project/src/utils.py",
        "docs/index.md",
        "Makefile",
        "package.json",
        ".gitignore",
        "tests/test_foo.py",
        "README.md",
        ".env",
        "/tmp/foo.json",
    ]

    def test_non_governance_files_have_no_hook_output(self):
        """Verify #3: non-governance files get only {'continue': true}."""
        for path in self.NON_GOV_PATHS:
            with self.subTest(path=path):
                result = _run_gate({"file_path": path})
                self.assertEqual(result, {"continue": True},
                                 f"Non-governance path should return bare continue: {path}")

    def test_non_governance_always_continue(self):
        """Verify #3: non-governance is never blocked."""
        for path in self.NON_GOV_PATHS:
            with self.subTest(path=path):
                result = _run_gate({"file_path": path})
                self.assertIs(result.get("continue"), True,
                              f"Non-governance path must have continue=true: {path}")

    # ── Edge cases ──

    def test_missing_file_path_key(self):
        """No file_path key → continue without hookSpecificOutput."""
        result = _run_gate({})
        self.assertEqual(result, {"continue": True},
                         "Missing file_path should return bare continue")

    def test_empty_file_path(self):
        """Empty string file_path → continue without hookSpecificOutput."""
        result = _run_gate({"file_path": ""})
        self.assertEqual(result, {"continue": True},
                         "Empty file_path should return bare continue")

    def test_none_file_path(self):
        """None file_path (null in JSON) → continue without hookSpecificOutput."""
        result = _run_gate({"file_path": None})
        self.assertEqual(result, {"continue": True},
                         "None file_path should return bare continue")

    def test_gate_disabled_no_hook_output(self):
        """When gate is disabled (hc_enabled=False), no hookSpecificOutput emitted."""
        global MOCK_ENABLED
        original = MOCK_ENABLED
        MOCK_ENABLED = False
        try:
            result = _run_gate({"file_path": ".claude/hooks/foo.py"})
            self.assertEqual(result, {"continue": True},
                             "Disabled gate should return bare continue even for governance path")
        finally:
            MOCK_ENABLED = original

    def test_malformed_json_input(self):
        """Malformed JSON → exit with bare continue."""
        out = StringIO()
        err = StringIO()
        with patch("sys.stdin", StringIO("this is not json")), \
             patch("sys.stdout", out), \
             patch("sys.stderr", err), \
             patch.object(pretool_purify_gate, "hc_enabled", _mock_hc_enabled), \
             patch.object(pretool_purify_gate, "flywheel_event", _mock_flywheel_event):
            try:
                pretool_purify_gate.main()
            except SystemExit:
                pass
        result = json.loads(out.getvalue())
        self.assertEqual(result, {"continue": True},
                         "Malformed json should return bare continue")

    def test_tool_input_is_none(self):
        """tool_input key exists but is null → continue without hookSpecificOutput."""
        result = _run_gate(None)
        self.assertEqual(result, {"continue": True},
                         "None tool_input should return bare continue")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPretoolPurifyGate)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
