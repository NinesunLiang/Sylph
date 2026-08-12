"""Focused regressions for the advisory cross-session edit lock (index12 S3 / P1-5).

Concurrent agent sessions can edit the same non-frozen shared script and race (observed
in index11 E11-004/005). A frozen hook cannot enforce serialization, so this is an
advisory CAS lock any governed agent can check before writing a shared file.
Red-first: acquire/release/conflict/stale-steal/corrupt-fail-closed.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from write_lock import acquire_edit_lock, release_edit_lock, edit_lock_status  # noqa: E402


def test_edit_lock_acquire_release(tmp_path):
    target = tmp_path / "shared.py"
    ok, info = acquire_edit_lock(target, holder="sess-A")
    assert ok
    assert info["holder"] == "sess-A"
    assert edit_lock_status(target)["locked"] is True
    assert release_edit_lock(target, "sess-A") is True
    assert edit_lock_status(target)["locked"] is False


def test_edit_lock_conflict_blocks_second_holder(tmp_path):
    target = tmp_path / "shared.py"
    acquire_edit_lock(target, holder="sess-A")
    ok, info = acquire_edit_lock(target, holder="sess-B")
    assert ok is False
    assert info["holder"] == "sess-A"
    # release still requires the original holder
    assert release_edit_lock(target, "sess-B") is False
    assert edit_lock_status(target)["holder"] == "sess-A"


def test_edit_lock_stale_can_be_stealed(tmp_path):
    target = tmp_path / "shared.py"
    acquire_edit_lock(target, holder="sess-A", ttl_sec=0)
    ok, info = acquire_edit_lock(target, holder="sess-B")
    assert ok is True
    assert info["holder"] == "sess-B"


def test_edit_lock_corrupt_fails_closed(tmp_path):
    target = tmp_path / "shared.py"
    lock = Path(str(target) + ".edit.lock")
    lock.write_text("{not-json", encoding="utf-8")
    ok, info = acquire_edit_lock(target, holder="sess-A")
    assert ok is False  # never steal a corrupt lock silently
    assert info.get("corrupt") is True


def test_edit_lock_ttl_expiry_reports_status(tmp_path):
    target = tmp_path / "shared.py"
    acquire_edit_lock(target, holder="sess-A", ttl_sec=0)
    status = edit_lock_status(target)
    assert status["expired"] is True
    assert status["locked"] is False
