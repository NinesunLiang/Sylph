"""test_proposals_approver.py — 采纳台 v1（PLAN_SIMPLIFY C6, Phase 2）

list/accept/reject：accept 可空 note；reject 必须写原因（供蒸馏器学习）。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import proposals as P


def _seed(tmp: Path, props: list[dict]) -> Path:
    j = tmp / "proposals.jsonl"
    j.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in props) + "\n", encoding="utf-8")
    return j


def _read_all(j: Path) -> list[dict]:
    return [json.loads(l) for l in j.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_accept_sets_status_and_note():
    with tempfile.TemporaryDirectory() as td:
        j = _seed(Path(td), [{
            "id": "p-2026-09-08-001", "source": "distiller", "kind": "anti-pattern",
            "evidence": {"count": 3, "refs": []}, "suggestion": "x",
            "impact_estimate": "中", "status": "pending", "human_note": "", "test_commit": "",
        }])
        rc = P._mutate(str(j), "p-2026-09-08-001", "accepted", "采纳")
        assert rc == 0
        d = _read_all(j)[0]
        assert d["status"] == "accepted" and d["human_note"] == "采纳"


def test_reject_requires_note():
    with tempfile.TemporaryDirectory() as td:
        j = _seed(Path(td), [{
            "id": "p-2026-09-08-002", "source": "distiller", "kind": "gate-zombie",
            "evidence": {"count": 0, "refs": []}, "suggestion": "删门禁", "impact_estimate": "低",
            "status": "pending", "human_note": "", "test_commit": "",
        }])
        assert P._mutate(str(j), "p-2026-09-08-002", "rejected", "") == 1, "reject 无原因应拒绝"
        assert _read_all(j)[0]["status"] == "pending"
        assert P._mutate(str(j), "p-2026-09-08-002", "rejected", "此门禁即将启用") == 0
        assert _read_all(j)[0]["status"] == "rejected"


def test_mutate_unknown_id_returns_1():
    with tempfile.TemporaryDirectory() as td:
        j = _seed(Path(td), [{"id": "p-x", "status": "pending"}])
        assert P._mutate(str(j), "p-nope", "accepted", "") == 1
