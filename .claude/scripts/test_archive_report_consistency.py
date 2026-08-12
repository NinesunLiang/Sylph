import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/scripts"))

from carros_utils import generate_final_report


class ArchiveReportConsistencyTest(unittest.TestCase):
    def test_report_uses_archived_status_and_completion(self):
        token = {
            "status": "archived",
            "session": {"id": "sample", "level": "L1"},
            "stats": {"done": 3, "total": 3},
            "task": {"status": "completed", "goal": "sample goal"},
        }
        report = generate_final_report(token)
        self.assertIn("**状态:** archived", report)
        self.assertIn("**完成度:** 3/3 步", report)

    def test_report_preserves_conflict_warning_without_rewriting_progress(self):
        token = {
            "status": "archived",
            "session": {"id": "sample", "level": "L1"},
            "stats": {"done": 1, "total": 3},
            "task": {"status": "active", "goal": "sample goal"},
            "archive_warnings": ["state_conflict: token 1/3 vs plan 3/3"],
        }
        report = generate_final_report(token)
        self.assertIn("**完成度:** 1/3 步", report)
        self.assertIn("state_conflict: token 1/3 vs plan 3/3", report)


if __name__ == "__main__":
    unittest.main()
