"""test_anti_regrowth.py — 防膨胀闸（PLAN_SIMPLIFY C4/C6#4, Phase 2）

归档前必答「本轮删≥1 僵尸 或 证明无僵尸」，否则 BLOCK ——「少即是多」机械执行。
"""
from __future__ import annotations

import proposals as P


def test_no_zombie_passes_with_proof():
    r = P.anti_regrowth_check(zombies=[])
    assert r["ok"] is True
    assert "无僵尸" in r["note"]


def test_zombie_without_delete_blocks():
    r = P.anti_regrowth_check(zombies=[{"gate": "doc-quality", "last_seen": "2026-07-01"}])
    assert r["ok"] is False
    assert "删/归档 ≥1" in r["note"]
    assert len(r["zombies"]) == 1


def test_zombie_deleted_this_round_passes():
    r = P.anti_regrowth_check(zombies=[{"gate": "wide-glob", "last_seen": "2026-07-01",
                                        "deleted_this_round": True}])
    assert r["ok"] is True
    assert r["note"].startswith("本轮删/归档僵尸 1")
