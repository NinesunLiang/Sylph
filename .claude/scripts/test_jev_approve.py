"""jev_approve.py 回归锚点（D-017：JEV 决策模型签批）。全部离线，不发网络请求。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))

import jev_approve  # noqa: E402
from pretool_gates import checks  # noqa: E402


def _answers(choice="allow", conf=0.9, deny=0.02, ask=0.08, risk=0.2):
    return {
        "action": {"type": "choice", "choice": choice,
                   "probabilities": {"allow": 1 - deny - ask, "ask": ask, "deny": deny},
                   "confidence": conf},
        "risk": {"type": "score", "score": risk},
    }


def test_decide_accepts_confident_safe_allow():
    d = jev_approve._decide(_answers(), "typesafe/jev-1.13")
    assert d["verdict"] == "ACCEPT", d


def test_decide_rejects_deny_choice():
    d = jev_approve._decide(_answers(choice="deny", conf=0.99, deny=0.99, ask=0.01, risk=2.9))
    assert d["verdict"] == "REJECT", d


def test_decide_rejects_high_deny_probability():
    """choice=allow 但 P(deny) 偏高 → 不放行。"""
    d = jev_approve._decide(_answers(conf=0.9, deny=0.4, ask=0.1))
    assert d["verdict"] == "REJECT", d


def test_decide_rejects_low_confidence():
    d = jev_approve._decide(_answers(conf=0.2, deny=0.0, ask=0.1))
    assert d["verdict"] == "REJECT", d


def test_decide_rejects_high_risk_score():
    d = jev_approve._decide(_answers(conf=0.95, deny=0.01, ask=0.04, risk=2.5))
    assert d["verdict"] == "REJECT", d


def _patch_paths(monkeypatch, tmp_path):
    approval = tmp_path / "jev-approval.json"
    monkeypatch.setattr(jev_approve, "APPROVAL", approval)
    monkeypatch.setattr(jev_approve, "LOG", tmp_path / "log.jsonl")
    return approval


def test_accept_writes_approval(monkeypatch, tmp_path):
    approval = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "dummy")
    monkeypatch.setattr(jev_approve, "_judge",
                        lambda cmd, model, key: jev_approve._decide(_answers(), model))
    assert jev_approve.main(["--command", "npm install lodash"]) == 0
    data = json.loads(approval.read_text(encoding="utf-8"))
    assert data["approvals"][0]["verdict"] == "ACCEPT"


def test_reject_does_not_write(monkeypatch, tmp_path):
    approval = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "dummy")
    monkeypatch.setattr(jev_approve, "_judge",
                        lambda cmd, model, key: jev_approve._decide(
                            _answers(choice="deny", conf=0.99, deny=0.99, risk=2.9), model))
    assert jev_approve.main(["--command", "pip install mystery"]) == 1
    assert not approval.exists()


def test_missing_key_fails_closed(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "")
    assert jev_approve.main(["--command", "npm install x"]) == 2


def test_judge_unavailable_fails_closed(monkeypatch, tmp_path):
    approval = _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(jev_approve, "_load_key", lambda: "dummy")

    def boom(*a, **k):
        raise ValueError("no answers")

    monkeypatch.setattr(jev_approve, "_judge", boom)
    assert jev_approve.main(["--command", "npm install x"]) == 2
    assert not approval.exists()


def test_expired_approval_is_ignored(monkeypatch, tmp_path):
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    blob = json.dumps({"approvals": [{
        "hash": "deadbeefdeadbeef", "verdict": "ACCEPT", "score": 10,
        "expires_at": past}]})

    class _P:
        def __init__(self, *_a):
            pass

        def exists(self):
            return True

        def read_text(self, **_k):
            return blob

    monkeypatch.setattr(checks, "Path", _P)
    assert checks._has_fresh_jev_approval("x") is False
