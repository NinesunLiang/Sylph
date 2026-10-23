"""jev_approve.py 回归锚点（D-016 第 1 档）。全部离线，不发网络请求。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))

import jev_approve  # noqa: E402
from pretool_gates import checks  # noqa: E402


def _patch_paths(monkeypatch, tmp_path):
    approval = tmp_path / "jev-approval.json"
    log = tmp_path / "jev-approval-log.jsonl"
    monkeypatch.setattr(jev_approve, "APPROVAL", approval)
    monkeypatch.setattr(jev_approve, "LOG", log)
    return approval


def test_accept_writes_approval_and_gate_honors_it(monkeypatch, tmp_path):
    approval = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "dummy")
    monkeypatch.setattr(jev_approve, "_judge",
                        lambda cmd, model, key: {"verdict": "ACCEPT", "score": 9.5,
                                                 "reasons": ["benign"]})
    monkeypatch.setattr(checks, "Path", lambda *a: approval)
    checks._JEV_APPROVAL_OVERRIDE = approval  # 供 checks 读取
    rc = jev_approve.main(["--command", "npm install left-pad"])
    assert rc == 0
    data = json.loads(approval.read_text(encoding="utf-8"))
    assert data["approvals"] and data["approvals"][0]["score"] == 9.5


def test_reject_does_not_write(monkeypatch, tmp_path):
    approval = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "dummy")
    monkeypatch.setattr(jev_approve, "_judge",
                        lambda cmd, model, key: {"verdict": "REJECT", "score": 2,
                                                 "reasons": ["destructive"]})
    rc = jev_approve.main(["--command", "pip install mystery"])
    assert rc == 1
    assert not approval.exists()


def test_low_score_accept_is_not_enough(monkeypatch, tmp_path):
    approval = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "dummy")
    monkeypatch.setattr(jev_approve, "_judge",
                        lambda cmd, model, key: {"verdict": "ACCEPT", "score": 5})
    assert jev_approve.main(["--command", "npm install x"]) == 1
    assert not approval.exists()


def test_missing_key_fails_closed(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "")
    assert jev_approve.main(["--command", "npm install x"]) == 2


def test_judge_unavailable_fails_closed(monkeypatch, tmp_path):
    approval = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "dummy")

    def boom(*a, **k):
        raise ValueError("no json")

    monkeypatch.setattr(jev_approve, "_judge", boom)
    assert jev_approve.main(["--command", "npm install x"]) == 2
    assert not approval.exists()


def test_expired_approval_is_ignored(monkeypatch, tmp_path):
    approval = tmp_path / "jev-approval.json"
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    approval.write_text(json.dumps({"approvals": [{
        "hash": "deadbeefdeadbeef", "verdict": "ACCEPT", "score": 10,
        "expires_at": past}]}), encoding="utf-8")

    real_path = checks.Path

    class _P:
        def __init__(self, *_a):
            pass

        def exists(self):
            return True

        def read_text(self, **_k):
            return approval.read_text(encoding="utf-8")

    monkeypatch.setattr(checks, "Path", _P)
    assert checks._has_fresh_jev_approval("x") is False
    monkeypatch.setattr(checks, "Path", real_path)
