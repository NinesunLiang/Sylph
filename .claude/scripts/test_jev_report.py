"""违规捕获机制测试。

用户 2026-10-19：不做批量盲评；看到违规就记一条，用它增强规则。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import jev_audit  # noqa: E402
import jev_fit as jf  # noqa: E402
import jev_report  # noqa: E402


def _run(monkeypatch, rule: str, note: str, evidence: str) -> int:
    monkeypatch.setattr(sys, "argv", [
        "jev_report.py", "--rule", rule, "--note", note,
        "--evidence", evidence, "--reviewer", "tester",
    ])
    return jev_report.main()


def test_report_creates_human_violation(monkeypatch):
    assert _run(monkeypatch, "rule.report.a", "note-a", "evidence-report-a") == 0
    rows = [r for r in jf.load_reviews(jf.LEDGER) if r.get("source") == "violation_report"]
    assert any(r["rule_id"] == "rule.report.a"
               and (r.get("human") or {}).get("verdict") == "不符合" for r in rows)


def test_report_is_idempotent(monkeypatch):
    _run(monkeypatch, "rule.report.b", "note-b", "evidence-report-b")
    before = len(jf.load_reviews(jf.LEDGER))
    _run(monkeypatch, "rule.report.b", "note-b", "evidence-report-b")
    assert len(jf.load_reviews(jf.LEDGER)) == before


def test_violation_summary_marks_ready_at_three(monkeypatch):
    for i in range(3):
        _run(monkeypatch, "rule.report.c", f"note-{i}", f"evidence-report-c-{i}")
    rep = jev_audit.violations(jf.load_reviews(jf.LEDGER))
    assert rep["rule.report.c"]["count"] >= 3
    assert rep["rule.report.c"]["ready_to_strengthen"] is True


def test_report_requires_evidence(monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "jev_report.py", "--rule", "rule.report.d", "--note", "no evidence",
        "--reviewer", "tester",
    ])
    assert jev_report.main() == 2
