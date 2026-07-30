#!/usr/bin/env python3
"""
test-postcompact-atomic.py — RED TDD for postcompact.py hardening

Contract:
  - S1.1: atomic write of resume-note.md via tmp + os.replace
  - S1.2: fail-silent on capsule validation errors
  - Stale notes (mtime > STALE_HOURS) auto-deleted by session-start.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POSTCOMPACT = ROOT / ".claude" / "hooks" / "postcompact.py"
SESSION_START = ROOT / ".claude" / "hooks" / "session-start.py"
STATE = ROOT / ".omc" / "state"
NOTE = STATE / "resume-note.md"
CAPSULE = STATE / "resume-capsule.json"


# ── Helpers ──────────────────────────────────────────────────────


def _write_capsule(token_path: str, plan_dir: str, step: str = "S1") -> None:
    CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    CAPSULE.write_text(json.dumps({
        "active_token": token_path,
        "plan_dir": plan_dir,
        "current_step": step,
        "current_phase": "executing",
        "task_id": "test-task",
    }), encoding="utf-8")


def _run_hook(hook: Path, payload: dict | None = None) -> subprocess.CompletedProcess:
    stdin = json.dumps(payload or {})
    return subprocess.run(
        ["python3", str(hook)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=10,
    )


# ── S1.1: atomic write ──────────────────────────────────────────


def test_postcompact_atomic_write_creates_note(tmp_path: Path) -> None:
    """Valid capsule → resume-note.md exists with content."""
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps({"status": "active"}), encoding="utf-8")
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    for f in ("plan.md", "research.md", "executor.md"):
        (plan_dir / f).write_text(f"# {f}\n", encoding="utf-8")
    _write_capsule(str(token_path), str(plan_dir))

    # Backup note
    backup = NOTE.read_bytes() if NOTE.exists() else None
    try:
        result = _run_hook(POSTCOMPACT)
        assert result.returncode == 0
        assert NOTE.exists()
        text = NOTE.read_text(encoding="utf-8")
        assert "AUTO-RESUME" in text
        assert "test-task" in text
        # No leftover tmp files
        tmp_files = list(NOTE.parent.glob(f"{NOTE.name}.*.tmp"))
        assert not tmp_files, f"leftover tmp: {tmp_files}"
    finally:
        if backup is None:
            NOTE.unlink(missing_ok=True)
        else:
            NOTE.write_bytes(backup)


def test_postcompact_no_capsule_no_note(tmp_path: Path) -> None:
    """Missing capsule → no resume-note.md written (graceful skip)."""
    backup = NOTE.read_bytes() if NOTE.exists() else None
    cap_backup = CAPSULE.read_bytes() if CAPSULE.exists() else None
    try:
        # Start clean: no capsule, no note
        if CAPSULE.exists():
            CAPSULE.unlink()
        if NOTE.exists():
            NOTE.unlink()

        result = _run_hook(POSTCOMPACT)
        assert result.returncode == 0
        # NOTE should not be created if no capsule
        assert not NOTE.exists(), "hook should NOT create note without capsule"
        # stdout should still be valid JSON
        out = json.loads(result.stdout)
        assert out.get("continue") is True
    finally:
        if cap_backup is not None:
            CAPSULE.write_bytes(cap_backup)
        if backup is None:
            NOTE.unlink(missing_ok=True)
        else:
            NOTE.write_bytes(backup)


def test_postcompact_corrupt_capsule_silent_fail() -> None:
    """Malformed JSON capsule → hook does NOT raise, returns continue."""
    backup = NOTE.read_bytes() if NOTE.exists() else None
    cap_backup = CAPSULE.read_bytes() if CAPSULE.exists() else None
    try:
        CAPSULE.parent.mkdir(parents=True, exist_ok=True)
        CAPSULE.write_text("{not valid json", encoding="utf-8")

        result = _run_hook(POSTCOMPACT)
        # Must not crash
        assert result.returncode == 0
        out = json.loads(result.stdout)
        assert out.get("continue") is True
    finally:
        if cap_backup is not None:
            CAPSULE.write_bytes(cap_backup)
        else:
            CAPSULE.unlink(missing_ok=True)
        if backup is None:
            NOTE.unlink(missing_ok=True)
        else:
            NOTE.write_bytes(backup)


# ── S1.3: stale detection in session-start ─────────────────────


def test_session_start_discards_stale_resume_note() -> None:
    """resume-note.md older than STALE_HOURS → deleted, no injection."""
    backup = NOTE.read_bytes() if NOTE.exists() else None
    try:
        NOTE.parent.mkdir(parents=True, exist_ok=True)
        NOTE.write_text("[AUTO-RESUME] stale\n", encoding="utf-8")
        # Backdate mtime to 25h ago
        old_time = time.time() - (25 * 3600)
        os.utime(NOTE, (old_time, old_time))

        result = _run_hook(SESSION_START, {"source": "compact"})
        assert result.returncode == 0
        # Note should be deleted
        assert not NOTE.exists(), "stale note should be deleted"
    finally:
        if backup is None:
            NOTE.unlink(missing_ok=True)
        else:
            NOTE.write_bytes(backup)


def test_session_start_fresh_resume_note_injected() -> None:
    """Fresh resume-note.md → content injected into additionalContext."""
    backup = NOTE.read_bytes() if NOTE.exists() else None
    try:
        NOTE.parent.mkdir(parents=True, exist_ok=True)
        NOTE.write_text("[AUTO-RESUME] fresh marker XYZ\n", encoding="utf-8")

        result = _run_hook(SESSION_START, {"source": "compact"})
        assert result.returncode == 0
        out = json.loads(result.stdout)
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "fresh marker XYZ" in ctx
    finally:
        if backup is None:
            NOTE.unlink(missing_ok=True)
        else:
            NOTE.write_bytes(backup)


def test_session_start_truncates_long_resume_note() -> None:
    """Note >500 chars → truncated at last newline before 500."""
    backup = NOTE.read_bytes() if NOTE.exists() else None
    try:
        NOTE.parent.mkdir(parents=True, exist_ok=True)
        long_text = "[AUTO-RESUME] " + ("x" * 800) + "\nEND\n"
        NOTE.write_text(long_text, encoding="utf-8")

        result = _run_hook(SESSION_START, {"source": "compact"})
        assert result.returncode == 0
        out = json.loads(result.stdout)
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        # Should NOT contain the full 800 xs (truncated)
        assert "x" * 500 not in ctx, "long note should be truncated"
    finally:
        if backup is None:
            NOTE.unlink(missing_ok=True)
        else:
            NOTE.write_bytes(backup)