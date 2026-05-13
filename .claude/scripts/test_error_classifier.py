#!/usr/bin/env python3
"""
test_error_classifier.py -- Unit tests for error_classifier.py

Coverage:
  1. classify_error: Go errors (compile, undefined, unused import)
  2. classify_error: TypeScript/JavaScript errors
  3. classify_error: Python errors (runtime, missing module)
  4. classify_error: Rust errors
  5. classify_error: Make errors
  6. classify_error: Permission denied and OOM
  7. classify_error: Unknown/fallback
  8. classify_error: Multiple error types in single output
  9. classify_by_command: All command categories
  10. generate_signature: Deterministic hashing
  11. generate_signature: Different inputs produce different hashes
  12. Edge cases: Empty output, empty command
  13. Edge cases: Only whitespace output
  14. Edge cases: Case insensitivity for permission/OOM
  15. SYMPTOM_MAP completeness (all types have symptoms)
"""

import unittest
import json
import hashlib
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import error_classifier


class TestClassifyError(unittest.TestCase):
    """Tests for classify_error() -- multi-language error classifier."""

    def test_go_compile_error(self):
        """Go compile error with file:line:col format."""
        result = error_classifier.classify_error(
            "go build", 2,
            "# foo/bar\n./main.go:42:2: undefined: baz\n"
        )
        self.assertTrue(any(r["type"] == "go_compile" for r in result))
        go_errs = [r for r in result if r["type"] == "go_compile"]
        self.assertEqual(len(go_errs), 1)
        self.assertEqual(go_errs[0]["file"], "./main.go")
        self.assertEqual(go_errs[0]["line"], "42")

    def test_go_undefined(self):
        """Go undefined identifier detection."""
        result = error_classifier.classify_error("go build", 2, "undefined: SomeFunc")
        self.assertTrue(any(r["type"] == "go_undefined" for r in result))

    def test_go_undefined_alt_phrase(self):
        """Go undeclared name (alternate wording)."""
        result = error_classifier.classify_error("go build", 2, "undeclared name: x")
        self.assertTrue(any(r["type"] == "go_undefined" for r in result))

    def test_go_unused_import(self):
        """Go unused import detection."""
        result = error_classifier.classify_error("go build", 1, 'imported and not used: "fmt"')
        self.assertTrue(any(r["type"] == "go_unused_import" for r in result))

    def test_typescript_error(self):
        """TypeScript error with TS code."""
        result = error_classifier.classify_error("npx tsc", 2, "src/app.ts:5:3 - error TS2322: Type X is not assignable")
        self.assertTrue(any(r["type"] == "typescript" for r in result))
        ts_errs = [r for r in result if r["type"] == "typescript"]
        self.assertEqual(ts_errs[0]["code"], "TS2322")

    def test_missing_module(self):
        """Module not found for JS/TS."""
        result = error_classifier.classify_error("npm start", 1, "Error: Cannot find module 'lodash'")
        self.assertTrue(any(r["type"] == "missing_module" for r in result))

    def test_missing_module_alt(self):
        """Alternative phrasing for module not found."""
        result = error_classifier.classify_error("node app.js", 1, "module not found: express")
        self.assertTrue(any(r["type"] == "missing_module" for r in result))

    def test_python_runtime_error(self):
        """Python runtime error (ValueError)."""
        result = error_classifier.classify_error("python script.py", 1, "ValueError: invalid literal for int()")
        self.assertTrue(any(r["type"] == "python_error" for r in result))
        py_errs = [r for r in result if r["type"] == "python_error"]
        self.assertEqual(py_errs[0]["error_type"], "ValueError")

    def test_python_import_error(self):
        """Python ImportError."""
        result = error_classifier.classify_error("python app.py", 1, "ImportError: No module named requests")
        self.assertTrue(any(r["type"] == "python_error" for r in result))

    def test_python_missing_module(self):
        """Python missing module (no module named)."""
        result = error_classifier.classify_error("python app.py", 1, "No module named 'numpy'")
        self.assertTrue(any(r["type"] == "python_missing_module" for r in result))

    def test_rust_compile_error(self):
        """Rust compile error with error code."""
        result = error_classifier.classify_error("cargo build", 101, "error[E0308]: mismatched types")
        self.assertTrue(any(r["type"] == "rust_compile" for r in result))
        rs_errs = [r for r in result if r["type"] == "rust_compile"]
        self.assertEqual(rs_errs[0]["code"], "E0308")

    def test_make_error(self):
        """Make build failure."""
        result = error_classifier.classify_error("make", 2, "make: *** [all] Error 2")
        self.assertTrue(any(r["type"] == "make_error" for r in result))

    def test_permission_denied(self):
        """Permission denied error."""
        result = error_classifier.classify_error("./script.sh", 126, "permission denied: ./output.log")
        self.assertTrue(any(r["type"] == "permission" for r in result))

    def test_oom_error(self):
        """Out of memory error."""
        result = error_classifier.classify_error("node build.js", 137, "out of memory: killed process")
        self.assertTrue(any(r["type"] == "oom" for r in result))

    def test_oom_abbreviation(self):
        """OOM abbreviation detection."""
        result = error_classifier.classify_error("go test", 1, "OOM killer terminated process")
        self.assertTrue(any(r["type"] == "oom" for r in result))

    def test_unknown_fallback(self):
        """Unknown error fallback when nothing matches."""
        result = error_classifier.classify_error("custom-tool", 1, "Something went wrong but no pattern matches")
        self.assertTrue(any(r["type"] == "unknown" for r in result))
        self.assertEqual(result[-1]["symptom"], "unclassified")

    def test_empty_output(self):
        """Empty output results in unknown fallback."""
        result = error_classifier.classify_error("run.sh", 1, "")
        self.assertTrue(any(r["type"] == "unknown" for r in result))

    def test_whitespace_output(self):
        """Whitespace-only output results in unknown fallback."""
        result = error_classifier.classify_error("run.sh", 1, "   \n  \t  ")
        self.assertTrue(any(r["type"] == "unknown" for r in result))

    def test_multiple_errors_in_one_output(self):
        """Multiple error types in a single output string."""
        output = (
            "./main.go:10:2: undefined: x\n"
            "No module named 'y'\n"
            "permission denied\n"
        )
        result = error_classifier.classify_error("go run", 1, output)
        types_found = {r["type"] for r in result}
        self.assertIn("go_compile", types_found)
        self.assertIn("python_missing_module", types_found)
        self.assertIn("permission", types_found)

    def test_error_message_truncated(self):
        """Error messages are truncated to 200 characters."""
        long_msg = "a" * 500
        output = f"./main.go:1:1: {long_msg}"
        result = error_classifier.classify_error("go build", 1, output)
        go_errs = [r for r in result if r["type"] == "go_compile"]
        self.assertLessEqual(len(go_errs[0]["message"]), 200)

    def test_suggestions_always_present(self):
        """Every error result has a suggestions list."""
        cases = [
            ("go build", 2, "./x.go:1:1: error"),
            ("npm test", 1, "error TS2322: type"),
            ("python app.py", 1, "ValueError: bad"),
            ("make", 2, "make: error"),
            ("./a.sh", 126, "permission denied"),
            ("cmd", 1, "out of memory"),
        ]
        for cmd, code, out in cases:
            with self.subTest(cmd=cmd):
                result = error_classifier.classify_error(cmd, code, out)
                for r in result:
                    self.assertIn("suggestions", r)
                    self.assertIsInstance(r["suggestions"], list)
                    self.assertGreater(len(r["suggestions"]), 0)

    def test_exit_code_in_unknown_message(self):
        """Unknown error includes exit code in message."""
        result = error_classifier.classify_error("weird-tool", 42, "gibberish")
        self.assertIn("42", result[-1]["message"])

    def test_upper_case_permission(self):
        """Case insensitive permission denied."""
        result = error_classifier.classify_error("cmd", 126, "PERMISSION DENIED")
        self.assertTrue(any(r["type"] == "permission" for r in result))


class TestClassifyByCommand(unittest.TestCase):
    """Tests for classify_by_command()."""

    def test_build_commands(self):
        """Build-related commands are classified as 'build'."""
        for cmd in ["go build ./...", "npm run build", "cargo build", "tsc --noEmit"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "build")

    def test_test_commands(self):
        """Test-related commands are classified as 'test'."""
        for cmd in ["go test ./...", "npm test", "pytest tests/", "jest --coverage"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "test")

    def test_git_commands(self):
        """Git commands are classified as 'git'."""
        for cmd in ["git diff", "git status", "git commit -m 'fix'"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "git")

    def test_dependency_commands(self):
        """Dependency install commands."""
        for cmd in ["npm install", "go get -u", "pip install flask"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "dependency")

    def test_lint_commands(self):
        """Lint commands."""
        for cmd in ["eslint src/", "golangci-lint run", "lint --fix"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "lint")

    def test_docker_commands(self):
        """Docker commands."""
        for cmd in ["docker build", "docker compose up"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "docker")

    def test_network_commands(self):
        """Network commands."""
        for cmd in ["curl https://example.com", "wget -O file.zip"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "network")

    def test_file_ops_commands(self):
        """File operation commands."""
        for cmd in ["find . -name '*.go'", "grep -r 'foo'", "sed -i 's/a/b/'"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "file_ops")

    def test_runtime_fallback(self):
        """Unknown commands fall back to 'runtime'."""
        for cmd in ["echo hello", "ls -la", "cat README.md", "./custom-script.py"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(error_classifier.classify_by_command(cmd), "runtime")

    def test_empty_command(self):
        """Empty command returns 'runtime'."""
        self.assertEqual(error_classifier.classify_by_command(""), "runtime")


class TestGenerateSignature(unittest.TestCase):
    """Tests for generate_signature()."""

    def test_deterministic(self):
        """Same inputs produce same signature."""
        sig1 = error_classifier.generate_signature("go build", "2", "go_compile")
        sig2 = error_classifier.generate_signature("go build", "2", "go_compile")
        self.assertEqual(sig1, sig2)

    def test_different_inputs_different(self):
        """Different inputs produce different signatures."""
        sig1 = error_classifier.generate_signature("go build", "2", "go_compile")
        sig2 = error_classifier.generate_signature("npm test", "1", "typescript")
        self.assertNotEqual(sig1, sig2)

    def test_exit_code_matters(self):
        """Different exit codes produce different signatures."""
        sig1 = error_classifier.generate_signature("go build", "1", "go_compile")
        sig2 = error_classifier.generate_signature("go build", "2", "go_compile")
        self.assertNotEqual(sig1, sig2)

    def test_signature_length(self):
        """Signature is exactly 16 hex characters."""
        sig = error_classifier.generate_signature("cmd", "1", "type")
        self.assertEqual(len(sig), 16)
        int(sig, 16)  # should not raise

    def test_numeric_exit_code(self):
        """Numeric exit codes are accepted."""
        sig = error_classifier.generate_signature("go build", 2, "go_compile")
        self.assertEqual(len(sig), 16)
        int(sig, 16)

    def test_empty_cmd_signature(self):
        """Empty command still produces valid signature."""
        sig = error_classifier.generate_signature("", "0", "unknown")
        self.assertEqual(len(sig), 16)


class TestSymptomMapCompleteness(unittest.TestCase):
    """Tests for SYMPTOM_MAP completeness."""

    def test_all_known_types_in_symptom_map(self):
        """All types that classify_error can return must exist in SYMPTOM_MAP."""
        known_types = {
            "go_compile", "go_undefined", "go_unused_import",
            "typescript", "missing_module",
            "python_error", "python_missing_module",
            "rust_compile", "make_error",
            "permission", "oom", "unknown",
        }
        for t in known_types:
            with self.subTest(type=t):
                self.assertIn(t, error_classifier.SYMPTOM_MAP,
                              f"Type '{t}' missing from SYMPTOM_MAP")

    def test_all_symptom_map_values_valid(self):
        """All SYMPTOM_MAP values should be from known symptoms."""
        valid_symptoms = {
            "compile_error", "dependency_missing", "runtime_error",
            "build_failure", "permission_denied", "resource_exhaustion",
            "unclassified",
        }
        for t, s in error_classifier.SYMPTOM_MAP.items():
            with self.subTest(type=t):
                self.assertIn(s, valid_symptoms,
                              f"Symptom '{s}' for type '{t}' is not a known symptom")


class TestMainCLI(unittest.TestCase):
    """Tests for CLI entry point (main function)."""

    def test_signature_matches_expected(self):
        """Signature subcommand matches manual MD5 calculation."""
        expected = hashlib.md5("go build|2|go_compile".encode(), usedforsecurity=False).hexdigest()[:16]
        sig = error_classifier.generate_signature("go build", "2", "go_compile")
        self.assertEqual(sig, expected)


if __name__ == '__main__':
    unittest.main()
