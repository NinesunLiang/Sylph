#!/usr/bin/env python3
"""Test privacy-gate.py — DLP gate for sensitive file paths and tokens.

Mock approach: inject a fake harness_lib into sys.modules before importing
privacy_gate, so all harness_lib calls are under test control.

Usage:
    python3 scripts/test-privacy-gate.py
"""

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# ── Mock harness_lib before privacy-gate is imported ──
_mock_harness = MagicMock()
_mock_harness.hc_enabled.return_value = True
_mock_harness.hc_emit_hook_json.return_value = json.dumps({"continue": False})
_mock_harness.hc_fail_closure.return_value = False
_mock_harness.hc_get.return_value = "2.0"
sys.modules["harness_lib"] = _mock_harness

# Import privacy-gate.py via importlib (hyphen in filename prevents normal import)
_PRIVACY_GATE_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent / ".claude" / "hooks" / "privacy-gate.py"
)
_spec = importlib.util.spec_from_file_location("privacy_gate", _PRIVACY_GATE_PATH)
privacy_gate = importlib.util.module_from_spec(_spec)
sys.modules["privacy_gate"] = privacy_gate
_spec.loader.exec_module(privacy_gate)

# ─── Unit: _check_file_path ─────────────────────────────────────────────


class TestCheckFilePath(unittest.TestCase):
    """_check_file_path must return True for sensitive paths, False otherwise."""

    def test_blocks_env(self):
        self.assertTrue(privacy_gate._check_file_path(".env"))

    def test_blocks_pem(self):
        self.assertTrue(privacy_gate._check_file_path("cert/key.pem"))

    def test_blocks_key_file(self):
        self.assertTrue(privacy_gate._check_file_path("secret.key"))

    def test_blocks_credentials_json(self):
        self.assertTrue(privacy_gate._check_file_path("credentials.json"))

    def test_blocks_credentials_yml(self):
        self.assertTrue(privacy_gate._check_file_path("aws/credentials.yml"))

    def test_blocks_kubeconfig(self):
        self.assertTrue(privacy_gate._check_file_path("~/.kube/config?kubeconfig"))

    def test_blocks_id_rsa(self):
        self.assertTrue(privacy_gate._check_file_path("~/.ssh/id_rsa"))

    def test_blocks_p12(self):
        self.assertTrue(privacy_gate._check_file_path("cert.p12"))

    def test_allows_normal_py(self):
        self.assertFalse(privacy_gate._check_file_path("src/main.py"))

    def test_allows_normal_md(self):
        self.assertFalse(privacy_gate._check_file_path("README.md"))

    def test_allows_empty(self):
        self.assertFalse(privacy_gate._check_file_path(""))

    def test_allows_none(self):
        self.assertFalse(privacy_gate._check_file_path(None))


# ─── Unit: _check_command_for_tokens ────────────────────────────────────


class TestCheckCommandForTokens(unittest.TestCase):
    """_check_command_for_tokens must detect sk- and ghp_ tokens."""

    def test_blocks_sk_token(self):
        cmd = (
            "curl https://api.openai.com -H "
            "'Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'"
        )
        self.assertTrue(privacy_gate._check_command_for_tokens(cmd))

    def test_blocks_sk_ant_token(self):
        cmd = "ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        self.assertTrue(privacy_gate._check_command_for_tokens(cmd))

    def test_blocks_ghp_token(self):
        cmd = "git push https://ghp_abcdefghijklmnopqrstuvwxyz0123456789@github.com/repo"
        self.assertTrue(privacy_gate._check_command_for_tokens(cmd))

    def test_blocks_bearer_inline(self):
        cmd = "curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNqP_9bBr0r0iR1VfGcnx0nWQ9_4e3x0vLhMk'"
        self.assertTrue(privacy_gate._check_command_for_tokens(cmd))

    def test_allows_ls(self):
        self.assertFalse(privacy_gate._check_command_for_tokens("ls -la"))

    def test_allows_git_status(self):
        self.assertFalse(privacy_gate._check_command_for_tokens("git status"))

    def test_allows_empty(self):
        self.assertFalse(privacy_gate._check_command_for_tokens(""))

    def test_allows_none(self):
        self.assertFalse(privacy_gate._check_command_for_tokens(None))


# ─── Integration: main() e2e via stdin piping ───────────────────────────


class TestMainFlow(unittest.TestCase):
    """Feed JSON payloads through stdin, capture exit code and stdout."""

    def setUp(self):
        _mock_harness.reset_mock()
        _mock_harness.hc_enabled.return_value = True
        _mock_harness.hc_emit_hook_json.return_value = json.dumps({"continue": False})
        _mock_harness.hc_fail_closure.return_value = False

    def _run_main(self, stdin_json: str) -> tuple:
        """Return (stdout_text, exit_code)."""
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        sys.stdin = io.StringIO(stdin_json)
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        exit_code = 0
        try:
            privacy_gate.main()
        except SystemExit as e:
            exit_code = e.code if e.code is not None else 0

        out = sys.stdout.getvalue()
        sys.stdin = old_stdin
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        return out.strip(), exit_code

    # ── blocked cases (exit 2) ──

    def test_block_token_in_bash(self):
        payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {
                "command": "curl -H 'Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' https://api.example.com"
            },
        })
        out, code = self._run_main(payload)
        self.assertEqual(code, 2, "Token in bash command must exit 2")

    def test_block_ghp_token_in_bash(self):
        payload = json.dumps({
            "tool": "Bash",
            "args": {
                "command": "git push https://ghp_abcdefghijklmnopqrstuvwxyz0123456789@github.com/repo"
            },
        })
        out, code = self._run_main(payload)
        self.assertEqual(code, 2, "ghp_ token in bash command must exit 2")

    def test_block_sensitive_file_path(self):
        payload = json.dumps({
            "tool_name": "read",
            "tool_input": {"file_path": ".env"},
        })
        out, code = self._run_main(payload)
        self.assertEqual(code, 2, "Sensitive file path (.env) must exit 2")

    def test_block_sensitive_pem(self):
        payload = json.dumps({
            "tool_name": "read",
            "tool_input": {"file_path": "/etc/ssl/private/key.pem"},
        })
        out, code = self._run_main(payload)
        self.assertEqual(code, 2, "Sensitive file path (.pem) must exit 2")

    def test_block_sensitive_kubeconfig(self):
        # Pattern-based: _check_file_path uses `pattern` as fallback for grep
        payload = json.dumps({
            "tool_name": "Grep",
            "tool_input": {"pattern": "kubeconfig"},
        })
        out, code = self._run_main(payload)
        self.assertEqual(code, 2, "Sensitive grep pattern (kubeconfig) must exit 2")

    def test_block_credentials_yml(self):
        payload = json.dumps({
            "tool_name": "read",
            "tool_input": {"filePath": "config/credentials.yml"},
        })
        out, code = self._run_main(payload)
        self.assertEqual(code, 2, "Sensitive file (credentials.yml) must exit 2")

    # ── allowed cases (exit 0, continue: true) ──

    def test_allow_ls(self):
        payload = json.dumps({
            "tool_name": "bash",
            "tool_input": {"command": "ls -la"},
        })
        out, code = self._run_main(payload)
        self.assertIn('"continue": true', out)
        self.assertEqual(code, 0, "Normal command (ls) must exit 0")

    def test_allow_git_status(self):
        payload = json.dumps({
            "tool_name": "bash",
            "tool_input": {"command": "git status"},
        })
        out, code = self._run_main(payload)
        self.assertIn('"continue": true', out)
        self.assertEqual(code, 0, "Normal command (git status) must exit 0")

    def test_allow_read_source_file(self):
        payload = json.dumps({
            "tool_name": "read",
            "tool_input": {"file_path": "src/main.py"},
        })
        out, code = self._run_main(payload)
        self.assertIn('"continue": true', out)
        self.assertEqual(code, 0, "Normal file read must exit 0")

    def test_allow_non_json_stdin(self):
        """Non-JSON input should be silently allowed."""
        out, code = self._run_main("not json at all\n")
        self.assertIn('"continue": true', out)
        self.assertEqual(code, 0, "Non-JSON stdin must exit 0")


if __name__ == "__main__":
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestCheckFilePath))
    suite.addTests(loader.loadTestsFromTestCase(TestCheckCommandForTokens))
    suite.addTests(loader.loadTestsFromTestCase(TestMainFlow))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
