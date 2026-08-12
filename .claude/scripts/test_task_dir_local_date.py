"""Regression: task date directory uses LOCAL date, not UTC (index19 M?).

Bug: `_get_date_str()` used `datetime.now(timezone.utc)` — at UTC 19:00 (local
+8 = next day 03:00) the task landed in yesterday's date dir. On 2026-08-13
(local) a task created at 03:38 was filed under 20260812.

Fix contract: `_get_date_str()` returns the LOCAL calendar date.
"""
from datetime import datetime, timezone

import pytest

import carros_base as cb

# UTC 19:38 on 2026-08-12 == local (Asia/Shanghai +8) 03:38 on 2026-08-13
FIXED_UTC_19_38 = datetime(2026, 8, 12, 19, 38, 0, tzinfo=timezone.utc)
EXPECTED_LOCAL_DATE = "20260813"


@pytest.fixture
def patch_utcnow(monkeypatch):
    """Pin datetime.now(timezone.utc) to a fixed moment (UTC evening)."""

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return FIXED_UTC_19_38.astimezone(tz)
            # naive now() → local wall clock equivalent
            return FIXED_UTC_19_38.astimezone().replace(tzinfo=None)

    monkeypatch.setattr(cb, "datetime", FakeDatetime)


def test_get_date_str_uses_local_calendar_date(patch_utcnow):
    """At UTC 19:38 local is next day 03:38; dir date must be the local date."""
    assert cb._get_date_str() == EXPECTED_LOCAL_DATE


def test_init_task_paths_uses_local_date_dir(patch_utcnow, tmp_path, monkeypatch):
    """Task/token dirs must be filed under the local date, not UTC date."""
    monkeypatch.setattr(cb, "OMC_TASKS", tmp_path / "tasks")
    monkeypatch.setattr(cb, "OMC_TOKENS", tmp_path / "tokens")
    cb._init_task_paths(task_id="probe-local-date")
    assert "20260813" in str(cb.TASK_DIR)
    assert "20260813" in str(cb.TOKEN_PATH)


def test_audit_file_uses_local_date(patch_utcnow, tmp_path, monkeypatch):
    """Audit JSONL shards follow local date (inline fallback path)."""
    adir = tmp_path / "audit"
    monkeypatch.setattr(cb, "carros_utils", None)
    monkeypatch.setattr(cb, "AUDIT_DIR", adir)
    cb._write_audit("test", {"k": "v"})
    files = [p.name for p in adir.glob("*.jsonl")]
    assert files == [f"{EXPECTED_LOCAL_DATE}.jsonl"]
