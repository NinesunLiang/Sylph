#!/usr/bin/env python3
"""
test_flywheel_analytics.py -- Unit tests for flywheel_analytics.py

Coverage:
  1. Parse valid flywheel log with multiple skill entries
  2. Parse log with JSON decode errors (skipped)
  3. Deprecated skill detection (>30 days)
  4. Empty log file
  5. Missing log file
  6. Entry with 'name' field instead of 'skill' field
  7. Multiple skills sorted by invocations descending
  8. Invalid JSON lines are skipped
  9. Comment lines starting with # are skipped
  10. Unknown skill fallback (no skill or name field)
"""

import unittest
import json
import os
import tempfile
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flywheel_analytics


class TestFlywheelAnalytics(unittest.TestCase):
    """Tests for flywheel_analytics main() function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def _run_with_log(self, lines, log_name="flywheel.log"):
        """Run flywheel analytics with given log lines and return (exit_code, report_dict)."""
        log_path = os.path.join(self.temp_dir, log_name)
        with open(log_path, 'w') as f:
            for line in lines:
                f.write(line + '\n')

        report_path = os.path.join(self.temp_dir, "report.json")
        old_stdout = sys.stdout
        sys.stdout = open(os.path.join(self.temp_dir, "stdout.txt"), 'w')
        old_argv = sys.argv
        sys.argv = ["flywheel_analytics.py", log_path, report_path]
        try:
            exit_code = flywheel_analytics.main()
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout
            sys.argv = old_argv

        report = {}
        if os.path.exists(report_path):
            with open(report_path) as f:
                report = json.load(f)
        return exit_code, report

    def test_basic_parse(self):
        """Parse a valid flywheel log with basic entries."""
        now = int(time.time())
        lines = [
            f"# ts={now - 100}",
            json.dumps({"skill": "lx-todo", "duration": 5}),
            json.dumps({"skill": "lx-code-review", "duration": 30}),
            json.dumps({"skill": "lx-todo", "duration": 3}),
        ]
        exit_code, report = self._run_with_log(lines)
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["total_skill_events"], 3)
        self.assertEqual(report["unique_skills"], 2)

    def test_deprecated_skill_detection(self):
        """Skill not seen for >30 days is marked deprecated."""
        old_time = int(time.time()) - 31 * 86400  # 31 days ago
        exit_code, report = self._run_with_log([
            f"# ts={old_time}",
            json.dumps({"skill": "ancient-skill"}),
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("ancient-skill", report["skills"])
        self.assertTrue(report["skills"]["ancient-skill"]["deprecated"])
        self.assertIn("ancient-skill", report["deprecated_skills"])

    def test_recent_skill_not_deprecated(self):
        """Recently used skill should not be deprecated."""
        now = int(time.time())
        exit_code, report = self._run_with_log([
            f"# ts={now}",
            json.dumps({"skill": "fresh-skill"}),
        ])
        self.assertEqual(exit_code, 0)
        self.assertFalse(report["skills"]["fresh-skill"]["deprecated"])

    def test_empty_log_file(self):
        """Empty log file produces zero-event report."""
        exit_code, report = self._run_with_log([])
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["total_skill_events"], 0)
        self.assertEqual(report["unique_skills"], 0)

    def test_log_not_found(self):
        """Missing log file returns exit code 1."""
        old_stdout = sys.stdout
        sys.stdout = open(os.path.join(self.temp_dir, "stdout_missing.txt"), 'w')
        old_argv = sys.argv
        sys.argv = ["flywheel_analytics.py", "/nonexistent/path/flywheel.log"]
        try:
            exit_code = flywheel_analytics.main()
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout
            sys.argv = old_argv
        self.assertEqual(exit_code, 1)

    def test_json_decode_errors_skipped(self):
        """Lines with invalid JSON are silently skipped."""
        now = int(time.time())
        lines = [
            f"# ts={now}",
            json.dumps({"skill": "valid-skill"}),
            "not valid json",
            json.dumps({"skill": "another-skill"}),
        ]
        exit_code, report = self._run_with_log(lines)
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["total_skill_events"], 2)

    def test_name_field_fallback(self):
        """Entry with 'name' instead of 'skill' is accepted."""
        now = int(time.time())
        exit_code, report = self._run_with_log([
            f"# ts={now}",
            json.dumps({"name": "legacy-entry", "duration": 10}),
        ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["total_skill_events"], 1)

    def test_skills_sorted_by_count_desc(self):
        """Skills in report should be sorted by invocation count descending."""
        now = int(time.time())
        exit_code, report = self._run_with_log([
            f"# ts={now}",
            json.dumps({"skill": "rare-skill"}),
            json.dumps({"skill": "common-skill"}),
            json.dumps({"skill": "common-skill"}),
            json.dumps({"skill": "common-skill"}),
        ])
        self.assertEqual(exit_code, 0)
        skills = list(report["skills"].items())
        for i in range(len(skills) - 1):
            self.assertGreaterEqual(skills[i][1]["invocations"], skills[i + 1][1]["invocations"])

    def test_comment_lines_skipped(self):
        """Comment lines starting with # are skipped."""
        now = int(time.time())
        exit_code, report = self._run_with_log([
            f"# ts={now}",
            "# this is a comment",
            json.dumps({"skill": "real-skill"}),
        ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["total_skill_events"], 1)
        self.assertIn("real-skill", report["skills"])

    def test_unknown_skill_fallback(self):
        """Entry without skill or name field uses 'unknown'."""
        now = int(time.time())
        exit_code, report = self._run_with_log([
            f"# ts={now}",
            json.dumps({"duration": 5}),  # no skill, no name
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("unknown", report["skills"])
        self.assertEqual(report["skills"]["unknown"]["invocations"], 1)

    def test_report_has_required_fields(self):
        """Report contains all required metadata fields."""
        now = int(time.time())
        exit_code, report = self._run_with_log([
            f"# ts={now}",
            json.dumps({"skill": "test-skill"}),
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("generated_ts", report)
        self.assertIn("generated", report)
        self.assertIn("total_log_lines", report)
        self.assertIn("skills", report)
        self.assertIn("deprecated_skills", report)


if __name__ == '__main__':
    unittest.main()
