"""test_proposals_distill.py — 蒸馏器 v1（PLAN_SIMPLIFY C2/C6, Phase 2）

gate 僵尸 → gate-zombie 提案。schema 见 plan C2。

index48 变更：原「error-dna 聚类 → anti-pattern 提案」一路随 error-dna 机制整体移除
（该数据源无生产者、12 天遥测 100% pending），对应测试同步删除。
"""
from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import proposals as P


def test_gate_zombie_becomes_proposal():
    zombies = [{"gate": "doc-quality", "last_seen": "2026-07-01", "recent_count": 0}]
    props = P.make_proposals(zombies, threshold=3, asof=date(2026, 9, 8))
    gz = [p for p in props if p["kind"] == "gate-zombie"]
    assert len(gz) == 1 and gz[0]["suggestion"], gz


def test_no_anti_pattern_kind_without_error_dna():
    """error-dna 移除后，蒸馏器不得再产出 anti-pattern 类提案。"""
    zombies = [{"gate": "x", "last_seen": "2026-07-01", "recent_count": 0}]
    props = P.make_proposals(zombies, threshold=3, asof=date(2026, 9, 8))
    assert not [p for p in props if p["kind"] == "anti-pattern"]


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
