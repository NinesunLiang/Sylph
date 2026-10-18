"""gov_score 的修正与假绿测量（TDD）。

背景：
  · 审计曾被重写（破坏 append-only）→ 现在改为追加 audit_correction，评分扣除。
  · VERIFIED ≠ 正确 → 用「先通过后推翻」的矛盾率做假绿代理指标。
"""
from __future__ import annotations

import json
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
         "count": 1, "approved_by": "lucas.liang", "timestamp": now},
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


def _pending(rid: str, i: int) -> str:
    return json.dumps({"review_id": rid, "rule_id": "rule.a",
                       "change": f"diff {i}", "human": None}, ensure_ascii=False)


def test_unapproved_shrink_is_detected_and_penalized(tmp_path, monkeypatch):
    ledger = tmp_path / "reviews.jsonl"
    stats = tmp_path / "stats.jsonl"
    corrections = tmp_path / "corrections.jsonl"
    ledger.write_text("\n".join(_pending(f"p{i}", i) for i in range(10)) + "\n", encoding="utf-8")
    stats.write_text(json.dumps({"total": 15}) + "\n", encoding="utf-8")
    monkeypatch.setattr(gs.jf, "LEDGER", ledger)
    monkeypatch.setattr(gs.jf, "LEDGER_STATS", stats)
    monkeypatch.setattr(gs.jf, "LEDGER_CORRECTIONS", corrections)

    integ = gs._ledger_integrity()
    assert integ["unapproved_shrink"] == 5
    assert integ["ok"] is False

    # gain 的 strict 口径把未署名删除加回分母：5 条标注 / 15 = 0.333
    rows = [{"review_id": f"p{i}", "rule_id": "rule.a", "change": f"diff {i}",
             "human": ({"verdict": "符合"} if i < 5 else None)} for i in range(10)]
    monkeypatch.setattr(gs.jf, "load_reviews", lambda *_a, **_k: rows)
    d = gs.gain(strict=True)
    assert d["metrics"]["effective_total"] == 15
    assert d["score"] == 6.67


def test_signed_removal_is_not_penalized(tmp_path, monkeypatch):
    ledger = tmp_path / "reviews.jsonl"
    stats = tmp_path / "stats.jsonl"
    corrections = tmp_path / "corrections.jsonl"
    ledger.write_text(_pending("p0", 0) + "\n", encoding="utf-8")
    stats.write_text(json.dumps({"total": 5}) + "\n", encoding="utf-8")
    corrections.write_text(json.dumps({"count": 4, "approved_by": "lucas.liang"}) + "\n",
                           encoding="utf-8")
    monkeypatch.setattr(gs.jf, "LEDGER", ledger)
    monkeypatch.setattr(gs.jf, "LEDGER_STATS", stats)
    monkeypatch.setattr(gs.jf, "LEDGER_CORRECTIONS", corrections)
    assert gs._ledger_integrity()["ok"] is True


def test_unapproved_abandoned_counts_as_stale(tmp_path, monkeypatch):
    old = (datetime.now(timezone.utc).replace(year=2025)).isoformat()
    toks = [{"status": "abandoned", "session": {"id": "t1", "updated_at": old},
             "_path": str(tmp_path / "t1.json")}]
    monkeypatch.setattr(gs, "_tokens", lambda: toks)
    d = gs.documentation(strict=True)
    assert d["metrics"]["unapproved_abandoned"] == 1
    assert d["metrics"]["stale_over_7d"] == 1
    assert d["score"] == 0.0


def test_signed_abandoned_is_excluded(tmp_path, monkeypatch):
    old = (datetime.now(timezone.utc).replace(year=2025)).isoformat()
    toks = [{"status": "abandoned", "abandoned_approved_by": "lucas.liang",
             "session": {"id": "t1", "updated_at": old},
             "_path": str(tmp_path / "t1.json")}]
    monkeypatch.setattr(gs, "_tokens", lambda: toks)
    assert gs.documentation(strict=True)["score"] == 10.0


def test_unsigned_correction_is_ignored(monkeypatch):
    now = _iso()
    events = [
        {"event_type": "redirect_escalated_to_hard_stop", "task_id": None, "timestamp": now},
        {"event_type": "redirect_escalated_to_hard_stop", "task_id": None, "timestamp": now},
        {"event_type": "audit_correction", "correction": "test_pollution",
         "count": 2, "timestamp": now},
    ]
    monkeypatch.setattr(gs, "_audit_events", lambda: events)
    monkeypatch.setattr(gs, "_tokens", lambda: [{"status": "active", "session": {"created_at": now}}])
    d = gs.human(strict=True)
    assert d["metrics"]["hard_stops_counted_30d"] == 2
    assert d["metrics"]["unsigned_correction_ignored"] == 2


def test_attested_correction_is_applied(monkeypatch):
    now = _iso()
    events = [
        {"event_type": "redirect_escalated_to_hard_stop", "task_id": None, "timestamp": now},
        {"event_type": "audit_correction", "correction": "test_pollution",
         "count": 1, "approved_by": "lucas.liang", "timestamp": now},
        {"event_type": "correction_attestation", "correction_ts": now,
         "approved_by": "lucas.liang", "timestamp": now},
    ]
    monkeypatch.setattr(gs, "_audit_events", lambda: events)
    monkeypatch.setattr(gs, "_tokens", lambda: [{"status": "active", "session": {"created_at": now}}])
    assert gs.human(strict=True)["metrics"]["hard_stops_counted_30d"] == 0


def test_false_green_zero_when_no_flip(monkeypatch):
    events = [
        {"event_type": "verify_decision", "task_id": "t1", "step": "S1", "decision": "VERIFIED"},
        {"event_type": "verify_decision", "task_id": "t1", "step": "S1", "decision": "VERIFIED"},
    ]
    monkeypatch.setattr(gs, "_audit_events", lambda: events)
    fg = gs.false_green()
    assert fg["metrics"]["contradiction_rate"] == 0.0
    assert fg["score"] == 10.0
