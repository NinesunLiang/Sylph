#!/usr/bin/env python3
"""
test-edit-guard.py — Test suite for .claude/hooks/edit-guard.py

Verifies:
1. Blocks Edit to a file that was NOT previously read
2. Allows Edit after reading the file
3. read_tracker is checked (missing/empty tracker fails open)

Strategy: Integration test. Temporarily stashes mode tokens so the hook runs
in "normal" mode (not goal/ghost), and enables edit_guard in the harness cache.
"""

import json
import os
import re
import sys
import subprocess
import shutil
import unittest
from pathlib import Path


# ─── Paths ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = PROJECT_ROOT / ".claude" / "hooks" / "edit-guard.py"
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
TOKENS_DIR = STATE_DIR / "tokens"
HARNESS_CACHE = STATE_DIR / ".harness-cache"
TRACKER = STATE_DIR / "read-tracker.txt"
TRACKER_BAK = STATE_DIR / "read-tracker.txt.test_bak"
CACHE_BAK = STATE_DIR / ".harness-cache.test_bak"
TOKENS_BAK_DIR = STATE_DIR / "tokens.test_bak"

SOURCE_FILE = PROJECT_ROOT / "main.go"
README_FILE = PROJECT_ROOT / "README.md"


# ─── Fixture helpers ───

def _backup(path, backup):
    if path.exists():
        shutil.copy2(str(path), str(backup))


def _restore(path, backup):
    if backup.exists():
        shutil.copy2(str(backup), str(path))
        backup.unlink(missing_ok=True)
    elif path.exists():
        path.unlink(missing_ok=True)


def _setup_harness():
    """Enable edit_guard in harness cache + remove mode tokens so hook runs in normal mode."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Backup tracker, cache, and tokens ──
    _backup(TRACKER, TRACKER_BAK)
    _backup(HARNESS_CACHE, CACHE_BAK)
    if TOKENS_DIR.exists():
        if TOKENS_BAK_DIR.exists():
            shutil.rmtree(str(TOKENS_BAK_DIR))
        shutil.copytree(str(TOKENS_DIR), str(TOKENS_BAK_DIR))

    # ── Enable edit_guard in cache ──
    if HARNESS_CACHE.exists():
        text = HARNESS_CACHE.read_text(encoding="utf-8")
        text = re.sub(
            r"hooks_enabled\.edit_guard=false",
            "hooks_enabled.edit_guard=true",
            text,
        )
        if "hooks_enabled.edit_guard=true" not in text:
            text += "\nhooks_enabled.edit_guard=true"
        HARNESS_CACHE.write_text(text, encoding="utf-8")

    # ── Remove mode tokens (goal/ghost) so hook runs in "normal" mode ──
    if TOKENS_DIR.exists():
        shutil.rmtree(str(TOKENS_DIR))

    # Ensure source file exists
    if not SOURCE_FILE.exists():
        SOURCE_FILE.write_text("package main\n")


def _teardown_harness():
    """Restore all backed-up state."""
    _restore(TRACKER, TRACKER_BAK)
    _restore(HARNESS_CACHE, CACHE_BAK)
    if TOKENS_BAK_DIR.exists():
        if TOKENS_DIR.exists():
            shutil.rmtree(str(TOKENS_DIR))
        shutil.copytree(str(TOKENS_BAK_DIR), str(TOKENS_DIR))
        shutil.rmtree(str(TOKENS_BAK_DIR))


def _write_tracker(paths):
    TRACKER.parent.mkdir(parents=True, exist_ok=True)
    if paths:
        TRACKER.write_text("\n".join(paths) + "\n", encoding="utf-8")
    else:
        TRACKER.write_text("", encoding="utf-8")


def _delete_tracker():
    TRACKER.unlink(missing_ok=True)


def _run_hook(file_path):
    stdin_payload = json.dumps({
        "tool_input": {"file_path": file_path},
        "args": {},
    })
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=15,
    )
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"continue": False, "exit_code": result.returncode,
            "stderr": result.stderr, "stdout": result.stdout}


class TestEditGuardReadBeforeEdit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _setup_harness()

    @classmethod
    def tearDownClass(cls):
        _teardown_harness()

    def setUp(self):
        _backup(TRACKER, TRACKER_BAK)

    def tearDown(self):
        _restore(TRACKER, TRACKER_BAK)

    # ═══════════════════════════════════════════════════
    # Requirement 1: Blocks Edit to file NOT previously read
    # ═══════════════════════════════════════════════════

    def test_blocks_edit_without_read(self):
        _write_tracker(["/some/unrelated/file.go"])
        result = _run_hook(str(SOURCE_FILE))
        self.assertFalse(result.get("continue", True),
                         "Should block Edit for file not in read-tracker")

    def test_blocks_edit_empty_tracker(self):
        _write_tracker([])
        result = _run_hook(str(SOURCE_FILE))
        self.assertFalse(result.get("continue", True),
                         "Should block when read-tracker is empty")

    # ═══════════════════════════════════════════════════
    # Requirement 2: Allows Edit after reading the file
    # ═══════════════════════════════════════════════════

    def test_allows_edit_after_read(self):
        _write_tracker([str(SOURCE_FILE.resolve())])
        result = _run_hook(str(SOURCE_FILE))
        self.assertTrue(result.get("continue", False),
                        "Should allow Edit for previously read file")

    def test_allows_edit_resolved_path(self):
        _write_tracker([str(SOURCE_FILE.resolve())])
        input_path = os.path.normpath(
            str(PROJECT_ROOT / ".." / PROJECT_ROOT.name / SOURCE_FILE.name))
        result = _run_hook(input_path)
        self.assertTrue(result.get("continue", False),
                        "Should allow when resolved paths match")

    # ═══════════════════════════════════════════════════
    # Requirement 3: read_tracker is checked
    # ═══════════════════════════════════════════════════

    def test_missing_tracker_fails_open(self):
        _delete_tracker()
        result = _run_hook(str(SOURCE_FILE))
        self.assertTrue(result.get("continue", True),
                        "Missing read-tracker should fail-open (pass through)")

    def test_tracker_checked_bogus_path_blocks(self):
        _write_tracker(["/nonexistent/bogus.go"])
        result = _run_hook(str(SOURCE_FILE))
        self.assertFalse(result.get("continue", True),
                         "Should block because target path not in tracker")

    # ═══════════════════════════════════════════════════
    # Edge cases
    # ═══════════════════════════════════════════════════

    def test_non_source_file_passes(self):
        _write_tracker([])
        result = _run_hook(str(README_FILE))
        self.assertTrue(result.get("continue", False),
                        "Non-source file should pass through regardless of tracker")

    def test_no_file_path_fails_open(self):
        result = _run_hook("")
        self.assertTrue(result.get("continue", True),
                        "Empty file_path should fail-open")


if __name__ == "__main__":
    runner = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if runner.result.wasSuccessful() else 1)
