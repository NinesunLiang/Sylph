"""test_gov_distill.py — B 档治理域蒸馏（治理部分自迭代，A+B 开工 2026-10-22）

kind=gov-criterion 从判官账本（.omc/state/jev/reviews.jsonl）蒸馏：
  证据 = 人工裁决/备注（真实人判，非 AI 自证）+ 判官原判定 + 规则 id
  门禁 = 冷却期（14 天/同规则，rejected 不复活）+ 规则原文锁定
安全边界：提案只进 .omc/proposals/；accept 只登记 + 生成判官回放单，
冻结域（AGENTS.md/kernel.md/hooks）永不自动落盘。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proposals as P  # noqa: E402


def _ledger_entries():
    return [
        # soul.7.gain：2 条人工备注（含 1 条近期）+ 1 条无备注
        {"rule_id": "soul.7.gain", "verdict": "不符合",
         "human": {"verdict": "符合", "note": "重建 skill 是替换旧实现，判据应写明替换算增益",
                   "reviewer": "lucas.liang", "label_source": "human"}},
        {"rule_id": "soul.7.gain", "verdict": "符合",
         "human": {"verdict": "符合", "note": "删死链属消除冗余",
                   "reviewer": "lucas.liang", "label_source": "human"}},
        {"rule_id": "soul.7.gain", "verdict": "证据不足", "human": None},
        # soul.1.simple：只有 1 条备注 → 低于阈值
        {"rule_id": "soul.1.simple", "verdict": "不符合",
         "human": {"verdict": "符合", "note": "删 tombstone 死链，仓库认可",
                   "reviewer": "lucas.liang", "label_source": "human"}},
    ]


def test_gov_distill_creates_proposal_for_recurring_notes():
    props = P.make_gov_proposals(_ledger_entries(), threshold=2,
                                 registry=None, asof=date(2026, 10, 22))
    assert len(props) == 1, props
    p = props[0]
    assert p["kind"] == "gov-criterion"
    assert p["target"] == ".claude/scripts/jev_rules.yaml"
    assert "soul.7.gain" in p["suggestion"]
    assert p["impact_estimate"] == "高"
    assert p["replay_required"] is True
    assert p["evidence"]["count"] == 2 and len(p["evidence"]["refs"]) == 2
    assert p["evidence"]["locked_rule_text"], "规则原文必须随提案锁定"
    assert p["evidence"]["locked_source"] == "AGENTS.md:20"


def test_gov_distill_below_threshold_yields_nothing():
    with tempfile.TemporaryDirectory():
        assert P.make_gov_proposals(_ledger_entries(), threshold=3,
                                    registry=None, asof=date(2026, 10, 22)) == []


def test_gov_distill_empty_ledger_yields_nothing():
    assert P.make_gov_proposals([], threshold=2, registry=None,
                                asof=date(2026, 10, 22)) == []


def test_gov_cooling_14d_same_rule_suppressed():
    """同规则 14 天冷却：上次裁决未过 → 不再造新提案。"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "proposals.jsonl").write_text(json.dumps({
            "id": "p-2026-10-10-001", "kind": "gov-criterion",
            "suggestion": "改 soul.7.gain 判据", "status": "rejected",
            "human_note": "方向不对", "ts": "2026-10-10",
            "evidence": {"rule_ids": ["soul.7.gain"]},
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        props = P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                     asof=date(2026, 10, 22), jsonl_path=td / "proposals.jsonl")
    assert props == [], "14 天冷却期内同规则提案应被抑制"


def test_gov_cooling_expired_allows_again():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "proposals.jsonl").write_text(json.dumps({
            "id": "p-2026-09-01-001", "kind": "gov-criterion",
            "suggestion": "改 soul.7.gain 判据", "status": "rejected",
            "human_note": "方向不对", "ts": "2026-09-01",
            "evidence": {"rule_ids": ["soul.7.gain"]},
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        props = P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                     asof=date(2026, 10, 22), jsonl_path=td / "proposals.jsonl")
    assert len(props) == 1, "冷却期过（>14 天）允许重新提案"


def test_gov_pending_proposal_also_cooldown():
    """pending（在桌上）同样冷却 —— 已在桌上的不重复造。"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "proposals.jsonl").write_text(json.dumps({
            "id": "p-2026-10-18-001", "kind": "gov-criterion",
            "suggestion": "改 soul.7.gain 判据", "status": "pending",
            "human_note": "", "ts": "2026-10-18",
            "evidence": {"rule_ids": ["soul.7.gain"]},
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        props = P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                     asof=date(2026, 10, 22), jsonl_path=td / "proposals.jsonl")
    assert props == [], "pending 在桌上 + 冷却期 → 抑制"


def test_gov_accept_only_registers_never_writes_frozen(monkeypatch):
    """accept 治理提案 = 登记 + 生成回放单；绝不写冻结域/判官登记表。"""
    real_reg = Path(__file__).resolve().parent / "jev_rules.yaml"
    reg_before = real_reg.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        monkeypatch.setenv("CARROROS_GOV_REPLAY_DIR", str(td / "replay"))
        monkeypatch.setattr(P, "GOV_REPLAY_DIR", str(td / "replay"))
        j = td / "proposals.jsonl"
        j.write_text(json.dumps({
            "id": "p-2026-10-22-001", "kind": "gov-criterion",
            "target": ".claude/scripts/jev_rules.yaml",
            "suggestion": "改 soul.7.gain 判据：替换/删除属消除冗余应算增益",
            "evidence": {"count": 2, "refs": ["r1", "r2"],
                          "locked_rule_text": "增益优先…", "locked_source": "AGENTS.md:20"},
            "impact_estimate": "高", "status": "pending", "human_note": "", "test_commit": "",
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        rc = P._mutate(str(j), "p-2026-10-22-001", "accepted", "回放单已出，待 jev_fit replay")
        assert rc == 0
        d = json.loads(j.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert d["status"] == "accepted"
        assert d["replay_required"] is True
        assert d.get("replay_sheet"), "accept 必须生成判官回放单"
    assert real_reg.read_text(encoding="utf-8") == reg_before, "真实判官登记表不得被 accept 触碰"


def test_gov_replay_sheet_has_evidence_and_replay_requirement(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        monkeypatch.setenv("CARROROS_GOV_REPLAY_DIR", str(td / "replay"))
        monkeypatch.setattr(P, "GOV_REPLAY_DIR", str(td / "replay"))
        j = td / "proposals.jsonl"
        j.write_text(json.dumps({
            "id": "p-2026-10-22-001", "kind": "gov-criterion",
            "target": ".claude/scripts/jev_rules.yaml",
            "suggestion": "改 soul.7.gain 判据",
            "evidence": {"count": 2, "refs": ["ref-1", "ref-2"],
                          "locked_rule_text": "GT", "locked_source": "AGENTS.md:20"},
            "impact_estimate": "高", "status": "pending", "human_note": "", "test_commit": "",
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        P._mutate(str(j), "p-2026-10-22-001", "accepted", "ok")
        d = json.loads(j.read_text(encoding="utf-8").strip().splitlines()[-1])
        sheet = Path(d["replay_sheet"])
        assert sheet.exists()
        txt = sheet.read_text(encoding="utf-8")
        assert "ref-1" in txt and "ref-2" in txt
        assert "GT" in txt  # 规则原文锁定
        assert "jev_fit" in txt  # 回放路径
