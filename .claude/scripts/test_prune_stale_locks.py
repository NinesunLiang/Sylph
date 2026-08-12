"""Regression: prune-stale-locks quarantines stale token/lock residue only (index17 M2).

Covers: terminal+lock → lock-only quarantine; old active+lock → full quarantine;
fresh active+lock and lockless tokens → untouched. Reversible via backup dir.
"""
import json
import time
from pathlib import Path

import carros_base as cb


def _write_token(path: Path, status: str, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": status, "task": {"status": "x"}}), encoding="utf-8")
    Path(str(path) + ".lock").write_text("", encoding="utf-8")
    os_ts = time.localtime(mtime)
    import os
    os.utime(path, (mtime, mtime))
    os.utime(str(path) + ".lock", (mtime, mtime))


def _run(tmp_path, dry_run=False):
    omc = tmp_path / "omc"
    tokens = omc / "tokens"
    (omc / "state" / "audit").mkdir(parents=True, exist_ok=True)
    now = time.time()
    _write_token(tokens / "d1" / "archived_old.json", "archived", now - 86400 * 10)
    _write_token(tokens / "d1" / "active_old.json", "active", now - 86400 * 10)
    _write_token(tokens / "d1" / "active_fresh.json", "active", now - 60)
    # lockless terminal token — must never be touched
    (tokens / "d1" / "no_lock.json").write_text(
        json.dumps({"status": "completed"}), encoding="utf-8")
    old = cb.OMC_TOKENS, cb.OMC_ROOT
    cb.OMC_TOKENS, cb.OMC_ROOT = tokens, omc
    try:
        rc = cb.cmd_prune_stale_locks(dry_run=dry_run, max_age_days=1.0)
    finally:
        cb.OMC_TOKENS, cb.OMC_ROOT = old
    return rc, omc, tokens


def test_dry_run_moves_nothing(tmp_path):
    rc, omc, tokens = _run(tmp_path, dry_run=True)
    assert rc == 0
    assert (tokens / "d1" / "archived_old.json").exists()
    assert (tokens / "d1" / "archived_old.json.lock").exists()
    assert not (omc / "backup" / "stale-cleanup").exists()


def test_real_prune_quarantines_only_stale(tmp_path):
    rc, omc, tokens = _run(tmp_path)
    assert rc == 0
    # stale_lock: terminal token keeps token, lock removed
    assert (tokens / "d1" / "archived_old.json").exists()
    assert not (tokens / "d1" / "archived_old.json.lock").exists()
    # stale_active: token + lock quarantined
    assert not (tokens / "d1" / "active_old.json").exists()
    assert not (tokens / "d1" / "active_old.json.lock").exists()
    # fresh active + lockless token untouched
    assert (tokens / "d1" / "active_fresh.json").exists()
    assert (tokens / "d1" / "active_fresh.json.lock").exists()
    assert (tokens / "d1" / "no_lock.json").exists()
    # backup contains the quarantined files (reversible)
    backups = list((omc / "backup" / "stale-cleanup").rglob("*"))
    names = {p.name for p in backups}
    assert "active_old.json" in names
    assert "archived_old.json.lock" in names
