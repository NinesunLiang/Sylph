"""gov_score 的修正与假绿测量（TDD）。

背景：
  · 审计曾被重写（破坏 append-only）→ 现在改为追加 audit_correction，评分扣除。
  · VERIFIED ≠ 正确 → 用「先通过后推翻」的矛盾率做假绿代理指标。
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import gov_score as gs  # noqa: E402


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_strict_human_subtracts_test_pollution(monkeypatch):
    now = _iso()
    events = [
        {"event_type": "redirect_escalated_to_hard_stop", "task_id": None, "timestamp": now},
        {"event_type": "redirect_escalated_to_hard_stop", "task_id": "real-task", "timestamp": now},
        {"event_type": "audit_correction", "correction": "test_pollution",
         "count": 1, "timestamp": now},
    ]
    monkeypatch.setattr(gs, "_audit_events", lambda: events)
    monkeypatch.setattr(gs, "_tokens", lambda: [
        {"status": "active", "session": {"created_at": now}},
    ])
    d = gs.human(strict=True)
    assert d["metrics"]["hard_stops_counted_30d"] == 1
    assert d["metrics"]["test_pollution_correction"] == 1


def test_default_human_ignores_anonymous_events(monkeypatch):
    now = _iso()
    events = [
        {"event_type": "redirect_escalated_to_hard_stop", "task_id": None, "timestamp": now},
        {"event_type": "redirect_escalated_to_hard_stop", "task_id": "real-task", "timestamp": now},
    ]
    monkeypatch.setattr(gs, "_audit_events", lambda: events)
    monkeypatch.setattr(gs, "_tokens", lambda: [
        {"status": "active", "session": {"created_at": now}},
    ])
    assert gs.human(strict=False)["metrics"]["hard_stops_counted_30d"] == 1


def test_false_green_detects_verified_then_blocked(monkeypatch):
    events = [
        {"event_type": "verify_decision", "task_id": "t1", "step": "S1", "decision": "VERIFIED"},
        {"event_type": "verify_decision", "task_id": "t1", "step": "S1", "decision": "BLOCKED"},
        {"event_type": "verify_decision", "task_id": "t2", "step": "S1", "decision": "VERIFIED"},
    ]
    monkeypatch.setattr(gs, "_audit_events", lambda: events)
    fg = gs.false_green()
    assert fg["metrics"]["steps_verified"] == 2
    assert fg["metrics"]["steps_contradicted"] == 1
    assert fg["metrics"]["contradiction_rate"] == 0.5


def test_false_green_zero_when_no_flip(monkeypatch):
    events = [
        {"event_type": "verify_decision", "task_id": "t1", "step": "S1", "decision": "VERIFIED"},
        {"event_type": "verify_decision", "task_id": "t1", "step": "S1", "decision": "VERIFIED"},
    ]
    monkeypatch.setattr(gs, "_audit_events", lambda: events)
    fg = gs.false_green()
    assert fg["metrics"]["contradiction_rate"] == 0.0
    assert fg["score"] == 10.0
