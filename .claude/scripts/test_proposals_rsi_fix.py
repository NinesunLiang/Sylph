"""test_proposals_rsi_fix.py — RSI 修复回归锚点（2026-10-24）

锁死三件事：
  1. 被拒绝的提案在冷却期内不得换号复活（所有 kind，不只 gov-criterion）。
  2. 裁决必须写清「谁、何时、通过什么」；历史无归属裁决要被显式计数。
  3. RSI 三指标（采纳数 / 转化率 / 体重）必须能算出来。
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import proposals as P


def _seed(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def _read(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _gate_prop(pid: str, gate: str = "verify") -> dict:
    return {
        "id": pid, "source": "distiller", "kind": "gate-zombie",
        "evidence": {"count": 0, "refs": [f"gate-pass-count.jsonl: {gate} last=2026-09-10"]},
        "suggestion": f"门禁「{gate}」近 14 天 0 触发 → 删除或降 warn 观察（少即是多）",
        "impact_estimate": "低", "status": "pending", "human_note": "", "test_commit": "",
    }


def _args(tmp_path: Path, ledger: Path) -> SimpleNamespace:
    return SimpleNamespace(
        threshold=3, out=str(tmp_path), gate_pass=str(tmp_path / "gp.jsonl"),
        window=14, ledger=str(ledger), gov_threshold=2, gov_trust="strict",
    )


def _patch_sources(monkeypatch, zombies: list[dict]):
    monkeypatch.setattr("gate_zombie_report.gate_zombie_report",
                        lambda *a, **k: {"zombies": zombies, "rate": 0.0})
    monkeypatch.setattr("zombie_scan.find_zombies", lambda *a, **k: [])


def test_rejected_gate_zombie_not_revived_within_cooldown(tmp_path, monkeypatch):
    out = tmp_path / "proposals.jsonl"
    old = _gate_prop("p-2026-10-20-001")
    old.update({"status": "rejected", "decided_by": "lucas.liang",
                "decided_at": (date.today() - timedelta(days=3)).isoformat() + "T00:00:00+00:00",
                "human_note": "不是僵尸"})
    _seed(out, [old])
    ledger = _seed(tmp_path / "ledger.jsonl", [])
    _patch_sources(monkeypatch, [{"gate": "verify", "last_seen": "2026-09-10"}])

    rc = P._distill(_args(tmp_path, ledger))
    assert rc == 0
    rows = _read(out)
    pending = [r for r in rows if r["status"] == "pending"]
    assert pending == [], f"冷却期内不应复活：{pending}"


def test_rejected_gate_zombie_revives_after_cooldown(tmp_path, monkeypatch):
    out = tmp_path / "proposals.jsonl"
    old = _gate_prop("p-2026-09-30-001")
    old.update({"status": "rejected", "decided_by": "lucas.liang",
                "decided_at": (date.today() - timedelta(days=P.PROPOSAL_COOLDOWN_DAYS + 1)).isoformat()
                + "T00:00:00+00:00", "human_note": "再观察"})
    _seed(out, [old])
    ledger = _seed(tmp_path / "ledger.jsonl", [])
    _patch_sources(monkeypatch, [{"gate": "verify", "last_seen": "2026-09-10"}])

    rc = P._distill(_args(tmp_path, ledger))
    assert rc == 0
    pending = [r for r in _read(out) if r["status"] == "pending"]
    assert len(pending) == 1, "冷却期满应允许重新提案"


def test_rejected_delete_candidate_not_revived_within_cooldown(tmp_path, monkeypatch):
    out = tmp_path / "proposals.jsonl"
    old = {
        "id": "p-2026-10-20-001", "source": "distiller", "kind": "delete-candidate",
        "evidence": {"count": 1, "refs": ["x.py 无任何引用"]},
        "suggestion": "删除/归档死代码 .claude/scripts/x.py（未被代码/配置/文档引用）",
        "impact_estimate": "低", "status": "rejected",
        "decided_at": (date.today() - timedelta(days=3)).isoformat() + "T00:00:00+00:00",
        "human_note": "还有用",
    }
    _seed(out, [old])
    ledger = _seed(tmp_path / "ledger.jsonl", [])
    _patch_sources(monkeypatch, [])
    monkeypatch.setattr("zombie_scan.find_zombies",
                        lambda *a, **k: [".claude/scripts/x.py"])

    rc = P._distill(_args(tmp_path, ledger))
    assert rc == 0
    pending = [r for r in _read(out) if r["status"] == "pending"]
    assert pending == [], f"delete-candidate 也应遵守冷却期：{pending}"


def test_mutate_records_who_and_when(tmp_path):
    j = _seed(tmp_path / "proposals.jsonl", [_gate_prop("p-2026-10-24-001")])
    assert P._mutate(j, "p-2026-10-24-001", "rejected", "不是僵尸") == 0
    row = _read(j)[0]
    assert row["status"] == "rejected"
    assert row.get("decided_by"), "必须记录裁决人"
    assert row.get("decided_at"), "必须记录裁决时间"
    assert row.get("decision_source") == "propose_cli"


def test_stats_reports_three_metrics(tmp_path):
    rows = [
        {**_gate_prop("p-2026-10-20-001"), "status": "accepted", "decided_by": "lucas.liang"},
        {**_gate_prop("p-2026-10-20-002", "oracle"), "status": "rejected", "decided_by": "lucas.liang"},
        {**_gate_prop("p-2026-10-20-003", "stall"), "status": "rejected"},
        {**_gate_prop("p-2026-10-20-004", "budget"), "status": "deferred"},
        {**_gate_prop("p-2026-10-20-005", "loop"), "status": "pending"},
    ]
    j = _seed(tmp_path / "proposals.jsonl", rows)
    s = P.rsi_stats(j, root=Path(__file__).resolve().parents[2])

    assert s["accepted"] == 1
    assert s["pending"] == 1
    assert s["decided"] == 4
    assert s["adoption_rate"] == 0.25
    assert s["unverified_decisions"] == 2
    assert s["weight"]["code_lines"] > 0
    assert s["weight"]["doc_lines"] > 0
