"""test_proposals_distill.py — 蒸馏器 v1（PLAN_SIMPLIFY C2/C6, Phase 2）

error-dna 聚类 → anti-pattern 提案；gate 僵尸 → gate-zombie 提案。schema 见 plan C2。
"""
from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import proposals as P


def _mk_error_dna(tmp: Path, rows: list[dict]) -> Path:
    p = tmp / "error-dna.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p


def test_anti_pattern_proposal_clusters_by_type():
    rows = [
        {"ts": 1, "error_type": "bash_path_not_found", "resolution": "pending",
         "cmd": "ls /nope", "retry_count": 3},
        {"ts": 2, "error_type": "bash_path_not_found", "resolution": "pending",
         "cmd": "cat /nope", "retry_count": 1},
        {"ts": 3, "error_type": "bash_path_not_found", "resolution": "pending",
         "cmd": "rm /nope", "retry_count": 0},
        {"ts": 4, "error_type": "typeerror_sig", "resolution": "fixed",  # 已修不算
         "cmd": "x()", "retry_count": 0},
    ]
    props = P.make_proposals(rows, zombies=[], threshold=3, asof=date(2026, 9, 8))
    ap = [p for p in props if p["kind"] == "anti-pattern"]
    assert len(ap) == 1, f"应仅聚类 bash_path_not_found(3 条 pending): {[p['kind'] for p in props]}"
    assert ap[0]["evidence"]["count"] == 3
    assert ap[0]["status"] == "pending" and ap[0]["impact_estimate"] in ("高", "中", "低")
    assert ap[0]["id"].startswith("p-2026-09-08-")


def test_gate_zombie_becomes_proposal():
    zombies = [{"gate": "doc-quality", "last_seen": "2026-07-01", "recent_count": 0}]
    props = P.make_proposals(rows=[], zombies=zombies, threshold=3, asof=date(2026, 9, 8))
    gz = [p for p in props if p["kind"] == "gate-zombie"]
    assert len(gz) == 1 and gz[0]["suggestion"], gz


def test_write_proposals_outputs_jsonl_and_md():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td) / "proposals"
        props = [{
            "id": "p-2026-09-08-001", "source": "distiller", "kind": "anti-pattern",
            "evidence": {"count": 3, "refs": ["error-dna.jsonl:1"]},
            "suggestion": "为 bash_path_not_found 加已知签名映射", "impact_estimate": "中",
            "status": "pending", "human_note": "", "test_commit": "",
        }]
        jsonl, md = P.write_proposals(props, out_dir / "proposals.jsonl", out_dir / "proposals.md")
        assert jsonl.exists() and md.exists()
        rec = json.loads(jsonl.read_text().strip().splitlines()[-1])
        assert rec["id"] == props[0]["id"] and rec["status"] == "pending"
        assert props[0]["id"] in md.read_text(encoding="utf-8")
