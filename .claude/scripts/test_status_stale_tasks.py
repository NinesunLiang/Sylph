"""烂尾任务探测（TDD / RED 先行）。

背景：96 个令牌里有 18 个 `active`，最老的停在 2026-08-17（两个月）。
系统必须能自己发现「开工后没归档」的任务。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import carros_base as cb  # noqa: E402


def _write_token(root: Path, name: str, *, status: str, days_old: int) -> Path:
    ts = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    d = root / "20260101"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    p.write_text(json.dumps({
        "session": {"id": name, "created_at": ts, "updated_at": ts},
        "task_dir": f"/tmp/{name}",
        "status": status,
    }), encoding="utf-8")
    return p


def test_detects_active_task_older_than_threshold(tmp_path):
    _write_token(tmp_path, "old-task", status="active", days_old=30)
    _write_token(tmp_path, "fresh-task", status="active", days_old=1)
    stale = cb._stale_active_tokens(days=7, tokens_root=tmp_path)
    names = [s["task_id"] for s in stale]
    assert names == ["old-task"]
    assert stale[0]["age_days"] >= 29


def test_ignores_archived_tokens(tmp_path):
    _write_token(tmp_path, "done-task", status="archived", days_old=30)
    assert cb._stale_active_tokens(days=7, tokens_root=tmp_path) == []


def test_falls_back_to_created_at_when_updated_missing(tmp_path):
    d = tmp_path / "20260101"
    d.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    (d / "no-updated.json").write_text(json.dumps({
        "session": {"id": "no-updated", "created_at": old},
        "status": "active",
    }), encoding="utf-8")
    stale = cb._stale_active_tokens(days=7, tokens_root=tmp_path)
    assert [s["task_id"] for s in stale] == ["no-updated"]
