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


def test_orphan_lock_quarantined_when_no_paired_json(tmp_path):
    """S9 还债项：裸锁（无配对 json）也必须回收——prune 之前只遍历 *.json 清不掉。"""
    omc = tmp_path / "omc"
    tokens = omc / "tokens"
    (omc / "state" / "audit").mkdir(parents=True, exist_ok=True)
    (tokens / "d1").mkdir(parents=True, exist_ok=True)
    (tokens / "d1" / "orphan.json.lock").write_text("", encoding="utf-8")
    old = cb.OMC_TOKENS, cb.OMC_ROOT
    cb.OMC_TOKENS, cb.OMC_ROOT = tokens, omc
    try:
        rc = cb.cmd_prune_stale_locks(dry_run=False, max_age_days=1.0)
    finally:
        cb.OMC_TOKENS, cb.OMC_ROOT = old
    assert rc == 0
    assert not (tokens / "d1" / "orphan.json.lock").exists()
    backups = list((omc / "backup" / "stale-cleanup").rglob("*.lock"))
    assert any(p.name == "orphan.json.lock" for p in backups)


def test_orphan_lock_dry_run_visible_and_untouched(tmp_path):
    omc = tmp_path / "omc"
    tokens = omc / "tokens"
    (omc / "state" / "audit").mkdir(parents=True, exist_ok=True)
    (tokens / "d1").mkdir(parents=True, exist_ok=True)
    (tokens / "d1" / "orphan.json.lock").write_text("", encoding="utf-8")
    old = cb.OMC_TOKENS, cb.OMC_ROOT
    cb.OMC_TOKENS, cb.OMC_ROOT = tokens, omc
    try:
        rc = cb.cmd_prune_stale_locks(dry_run=True, max_age_days=1.0)
    finally:
        cb.OMC_TOKENS, cb.OMC_ROOT = old
    assert rc == 0
    # dry-run 报告裸锁但不动文件
    assert (tokens / "d1" / "orphan.json.lock").exists()


def test_planning_stuck_quarantined_but_progress_kept(tmp_path):
    """S10 还债项：终态 + task.status=planning + stats.done=0 的存量 token 移备份；有推进的不动。"""
    omc = tmp_path / "omc"
    tokens = omc / "tokens"
    (omc / "state" / "audit").mkdir(parents=True, exist_ok=True)
    d1 = tokens / "d1"
    d1.mkdir(parents=True)
    (d1 / "stuck.json").write_text(
        json.dumps({"status": "completed", "task": {"status": "planning"}, "stats": {"done": 0, "total": 1}}),
        encoding="utf-8",
    )
    # 对照组：planning 但有推进（done>0）→ 非 stuck，保留
    (d1 / "progress.json").write_text(
        json.dumps({"status": "completed", "task": {"status": "planning"}, "stats": {"done": 3, "total": 4}}),
        encoding="utf-8",
    )
    old = cb.OMC_TOKENS, cb.OMC_ROOT
    cb.OMC_TOKENS, cb.OMC_ROOT = tokens, omc
    try:
        rc = cb.cmd_prune_stale_locks(dry_run=False, max_age_days=1.0)
    finally:
        cb.OMC_TOKENS, cb.OMC_ROOT = old
    assert rc == 0
    assert not (d1 / "stuck.json").exists()
    assert (d1 / "progress.json").exists()


def test_snapshots_keep_recent_seven(tmp_path):
    """S10 还债项：state/snapshots 只保留最近 7 份，其余移 backup。"""
    import os

    omc = tmp_path / "omc"
    tokens = omc / "tokens"
    tokens.mkdir(parents=True, exist_ok=True)  # cmd 开头要求 tokens 存在
    (omc / "state" / "audit").mkdir(parents=True, exist_ok=True)
    snap = omc / "state" / "snapshots"
    snap.mkdir(parents=True)
    now = time.time()
    for i in range(10):
        p = snap / f"precompact-{i:03d}.json"
        p.write_text("{}", encoding="utf-8")
        os.utime(p, (now - i * 100, now - i * 100))  # i 越小越新
    old = cb.OMC_TOKENS, cb.OMC_ROOT
    cb.OMC_TOKENS, cb.OMC_ROOT = tokens, omc
    try:
        rc = cb.cmd_prune_stale_locks(dry_run=False, max_age_days=1.0,
                                      prune_snapshots=True, keep_snapshots=7)
    finally:
        cb.OMC_TOKENS, cb.OMC_ROOT = old
    assert rc == 0
    assert len(list(snap.glob("*.json"))) == 7
    backups = list((omc / "backup" / "stale-cleanup").rglob("*.json"))
    assert len(backups) == 3
