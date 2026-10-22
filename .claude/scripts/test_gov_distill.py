"""test_gov_distill.py — B 档治理域蒸馏（治理部分自迭代，A+B 2026-10-22 开启）

kind=gov-criterion 从判官账本（.omc/state/jev/reviews.jsonl）产出裁决请求：
  触发 = 冲突驱动（用户口径 2026-10-23）：判官结论 vs 人判结论相反才请人裁决一次，
         不做日常排队。require_conflict=False 可退回「证据量驱动」。
  证据 = 人判备注（note_trust 闸门：reviewer 是真人 + label_source=contemporaneous_human）
         弃权（不确定/不适用）不算证据，也不算冲突（与 jev_fit「不确定视为弃权」同口径）
  门禁 = 冷却期（14 天/同规则）+ 规则原文锁定 + 首批范围白名单（AGENTS.md）+ kernel 样本闸门
安全边界：提案只进 .omc/proposals/；accept 只登记 + 生成判官回放单，
冻结域（AGENTS.md/kernel.md/hooks）永不自动落盘。
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proposals as P  # noqa: E402


def _human(note, verdict="符合", reviewer="lucas.liang",
           label_source="contemporaneous_human"):
    """真人判备注（可信）。"""
    return {"verdict": verdict, "note": note, "reviewer": reviewer,
            "label_source": label_source}


def _pair(rule, noul, human, rid_pad):
    """账本真实形状：pending（带 jev 原始信号）+ resolution（带人判）。"""
    review_id = f"p-{rid_pad}-{rule}"
    return (
        {"kind": "pending", "review_id": review_id, "rule_id": rule,
         "jev": {"noul": noul}},
        {"kind": "resolution", "review_id": review_id, "human": human},
    )


def _ledger_entries():
    """soul.7.gain：2 条真冲突（判官 0.1→不符合 vs 人判 符合）+ 1 条无备注；
    soul.1.simple：1 条冲突 → 低于阈值。"""
    rows = []
    for pad, note in (("aaa111", "重建 skill 是替换旧实现，判据应写明替换算增益"),
                      ("bbb222", "删死链属消除冗余")):
        rows += list(_pair("soul.7.gain", 0.1, _human(note), pad))
    rows.append({"kind": "pending", "review_id": "p-ccc333-soul.7.gain",
                 "rule_id": "soul.7.gain", "jev": {"noul": 0.9}, "human": None})
    rows += list(_pair("soul.1.simple", 0.1, _human("删 tombstone 死链，仓库认可"), "ddd444"))
    return rows


def _ledger_undecided():
    """只有判官弃权（0.5 → 证据不足）+ 人判明确：属判据不足信号，不是相反结论冲突。"""
    rows = []
    for pad in ("aaa111", "bbb222"):
        rows += list(_pair("soul.7.gain", 0.5, _human("判据没说清，我判符合"), pad))
    return rows


def _ledger_abstain():
    """人判弃权（不确定）+ 判官 不符合：弃权不算证据，也不算冲突。"""
    return list(_pair("soul.7.gain", 0.1, _human("看不准", verdict="不确定"), "eee555"))


def _ledger_untrusted():
    """真实账本现状：所有备注来自 repo-history / claude-proxy，无一条人判。"""
    rows = []
    for pad, rev in (("aaa111", "claude-proxy"), ("bbb222", "repo-history")):
        rows += list(_pair("soul.7.gain", 0.1,
                           _human("AI 代理写的备注", reviewer=rev,
                                  label_source="contemporaneous_human"), pad))
    return rows


# ── 冲突驱动：核心新口径 ────────────────────────────────────

def test_conflict_triggers_one_adjudication():
    props = P.make_gov_proposals(_ledger_entries(), threshold=2,
                                 registry=None, asof=date(2026, 10, 22))
    assert len(props) == 1, props
    p = props[0]
    assert p["kind"] == "gov-criterion"
    assert "冲突 2 次" in p["suggestion"], p["suggestion"]
    assert len(p["evidence"]["conflicts"]) == 2
    assert p["evidence"]["conflicts"][0]["judge"] == "不符合"
    assert p["evidence"]["conflicts"][0]["human"] == "符合"
    assert any("[冲突]" in r for r in p["evidence"]["refs"])


def test_no_opposite_conflict_no_adjudication(capsys):
    """判官弃权 + 人判明确 = 判据不足，不升级为裁决（不打扰日常）。"""
    props = P.make_gov_proposals(_ledger_undecided(), threshold=2, registry=None,
                                 asof=date(2026, 10, 22))
    assert props == []
    assert "不请人裁决" in capsys.readouterr().out


def test_abstain_is_not_evidence():
    """弃权（不确定）带 note 也不算证据：通行做法 + jev_fit 同口径。"""
    props = P.make_gov_proposals(_ledger_abstain(), threshold=1, registry=None,
                                 asof=date(2026, 10, 22), require_conflict=False)
    assert props == [], "弃权不得充当证据"


def test_require_conflict_false_keeps_legacy_evidence_mode():
    """退回证据量驱动（旧行为）仍可用，供对照/回滚。"""
    props = P.make_gov_proposals(_ledger_undecided(), threshold=2, registry=None,
                                 asof=date(2026, 10, 22), require_conflict=False)
    assert len(props) == 1


def test_find_conflicts_classification():
    rules = P.load_rules_full()
    cs = P.find_conflicts(_ledger_entries(), rules)
    assert {c["kind"] for c in cs} == {"opposite"}, cs
    cs2 = P.find_conflicts(_ledger_undecided(), rules)
    assert {c["kind"] for c in cs2} == {"undecided"}, cs2
    assert P.find_conflicts(_ledger_abstain(), rules) == [], "弃权不是冲突"


# ── 蒸馏基本行为 ──────────────────────────────────────────────

def test_gov_distill_creates_proposal_for_recurring_notes():
    p = P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                             asof=date(2026, 10, 22))[0]
    assert p["target"] == ".claude/scripts/jev_rules.yaml"
    assert p["impact_estimate"] == "高"
    assert p["replay_required"] is True
    assert p["evidence"]["human_judged"] == 2
    assert p["evidence"]["trust"] == "human"
    assert p["evidence"]["locked_rule_text"], "规则原文必须随提案锁定"
    assert p["evidence"]["locked_source"] == "AGENTS.md:20"


def test_gov_id_follows_documented_schema():
    """P1 回归：ID 必须是 p-YYYY-MM-DD-NNN，不得加 -gov 之类的段。"""
    import re
    p = P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                             asof=date(2026, 10, 22), seq_start=17)[0]
    assert p["id"] == "p-2026-10-22-018", p["id"]
    assert re.match(r"^p-\d{4}-\d{2}-\d{2}-\d{3}$", p["id"])


def test_gov_distill_below_threshold_yields_nothing():
    assert P.make_gov_proposals(_ledger_entries(), threshold=3,
                                registry=None, asof=date(2026, 10, 22)) == []


def test_gov_distill_empty_ledger_yields_nothing():
    assert P.make_gov_proposals([], threshold=2, registry=None,
                                asof=date(2026, 10, 22)) == []


# ── P0：证据可信度闸门 ────────────────────────────────────────

def test_non_human_notes_do_not_count_in_strict_mode(capsys):
    props = P.make_gov_proposals(_ledger_untrusted(), threshold=2, registry=None,
                                 asof=date(2026, 10, 22), trust_mode="strict")
    assert props == [], "非人判备注不得充当治理证据"
    out = capsys.readouterr().out
    assert "0 条人判" in out and "jev_fit.py judge" in out, out


def test_inform_mode_proposes_but_downgrades_and_labels():
    props = P.make_gov_proposals(_ledger_untrusted(), threshold=2, registry=None,
                                 asof=date(2026, 10, 22), trust_mode="inform")
    assert len(props) == 1
    p = props[0]
    assert p["impact_estimate"] == "中", "非人判证据必须降级影响估计"
    assert p["evidence"]["trust"] == "mixed"
    assert p["evidence"]["human_judged"] == 0
    assert "非人判" in p["suggestion"], p["suggestion"]
    assert any("[非人判" in r for r in p["evidence"]["refs"])


def test_refs_dedup_and_missing_verdict_surfaced():
    dup = _ledger_entries() + [_ledger_entries()[0]]
    refs = P.make_gov_proposals(dup, threshold=2, registry=None,
                                asof=date(2026, 10, 22))[0]["evidence"]["refs"]
    assert len(refs) == len(set(refs)), f"refs 未去重: {refs}"


def test_note_trust_classification():
    ok, _ = P.note_trust({"human": _human("x")})
    assert ok is True
    for bad in (
        {"human": {"note": "x", "reviewer": "repo-history"}},
        {"human": {"note": "x", "reviewer": "claude-proxy"}},
        {"human": {"note": "x", "reviewer": ""}},
        {"human": {"note": "x", "reviewer": "lucas.liang"}},            # 缺 label_source
        {"human": {"note": "x", "reviewer": "lucas.liang",
                   "label_source": "hindsight_repo"}},                  # 事后反推不可信
    ):
        assert P.note_trust(bad)[0] is False, bad


# ── 冷却期：三个边界都钉死 ────────────────────────────────────

def _seeded_jsonl(td: Path, ts: str, status: str = "rejected") -> Path:
    j = td / "proposals.jsonl"
    j.write_text(json.dumps({
        "id": f"p-{ts}-001", "kind": "gov-criterion", "suggestion": "改 soul.7.gain 判据",
        "status": status, "human_note": "方向不对", "ts": ts,
        "evidence": {"rule_ids": ["soul.7.gain"]},
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    return j


def _cooled(ts: str, **kw):
    with tempfile.TemporaryDirectory() as td:
        j = _seeded_jsonl(Path(td), ts, **kw)
        return P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                    asof=date(2026, 10, 22), jsonl_path=j)


def test_gov_cooldown_gap13_suppressed():
    assert _cooled("2026-10-09") == []


def test_gov_cooldown_gap14_boundary_allowed():
    """边界语义：满 14 天即视为冷却结束（第 15 天起可提）。语义在此钉死。"""
    assert len(_cooled("2026-10-08")) == 1


def test_gov_cooldown_gap15_allowed():
    assert len(_cooled("2026-10-07")) == 1


def test_gov_pending_proposal_also_cooldown():
    assert _cooled("2026-10-18", status="pending") == []


# ── 首批范围白名单（AGENTS.md）+ kernel.md 样本闸门 ─────────────

def test_out_of_scope_source_skipped(capsys):
    reg = {"proj.port.9001": {"text": "端口 9001", "source": "README.md:307"}}
    led = list(_pair("proj.port.9001", 0.1, _human("端口应放宽"), "aaa111")) + \
        list(_pair("proj.port.9001", 0.1, _human("确实该放宽"), "bbb222"))
    props = P.make_gov_proposals(led, threshold=2, registry=reg, asof=date(2026, 10, 22))
    assert props == []
    assert "白名单" in capsys.readouterr().out


def test_kernel_source_gated_by_sample_size(capsys):
    reg = {"k.1": {"text": "冻结规则", "source": ".claude/kernel.md:12"}}
    led = list(_pair("k.1", 0.1, _human("a"), "aaa111")) + \
        list(_pair("k.1", 0.1, _human("b"), "bbb222"))
    props = P.make_gov_proposals(led, threshold=2, registry=reg, asof=date(2026, 10, 22),
                                 require_conflict=False)
    assert props == [], "样本 <200 不得蒸馏冻结域规则"
    assert "冻结域" in capsys.readouterr().out


# ── accept 边界：只登记 + 回放单，绝不碰冻结域 ────────────────

def _seed_accept(tmp: Path, monkeypatch, refs=("r1", "r2"), trust="human"):
    monkeypatch.setenv("CARROROS_GOV_REPLAY_DIR", str(tmp / "replay"))
    monkeypatch.setattr(P, "GOV_REPLAY_DIR", str(tmp / "replay"))
    j = tmp / "proposals.jsonl"
    j.write_text(json.dumps({
        "id": "p-2026-10-22-001", "kind": "gov-criterion",
        "target": ".claude/scripts/jev_rules.yaml",
        "suggestion": "改 soul.7.gain 判据",
        "evidence": {"count": len(refs), "refs": list(refs), "human_judged": 2,
                      "trust": trust, "locked_rule_text": "GT", "locked_source": "AGENTS.md:20"},
        "impact_estimate": "高", "status": "pending", "human_note": "", "test_commit": "",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    return j


def test_gov_accept_only_registers_never_writes_frozen(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    real_reg = Path(__file__).resolve().parent / "jev_rules.yaml"
    frozen = [real_reg, root / "AGENTS.md", root / ".claude" / "kernel.md"]
    before = {f: f.read_text(encoding="utf-8") for f in frozen}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        j = _seed_accept(td, monkeypatch)
        rc = P._mutate(str(j), "p-2026-10-22-001", "accepted", "回放单已出")
        assert rc == 0
        d = json.loads(j.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert d["status"] == "accepted"
        assert d["replay_required"] is True
        assert d.get("replay_sheet"), "accept 必须生成判官回放单"
    for f, txt in before.items():
        assert f.read_text(encoding="utf-8") == txt, f"冻结域被改：{f}"


def test_gov_replay_sheet_has_evidence_and_replay_requirement(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        j = _seed_accept(td, monkeypatch, refs=("ref-1", "ref-2"))
        P._mutate(str(j), "p-2026-10-22-001", "accepted", "ok")
        d = json.loads(j.read_text(encoding="utf-8").strip().splitlines()[-1])
        sheet = Path(d["replay_sheet"])
        assert sheet.exists()
        txt = sheet.read_text(encoding="utf-8")
        for need in ("ref-1", "ref-2", "GT", "jev_fit"):
            assert need in txt, need
        assert "更高" in txt and "≥" not in txt, "采纳闸门不得被放宽成 ≥"


# ── 端到端：_distill ─────────────────────────────────────────

def _run_distill(out_dir: Path, ledger_path: Path):
    import argparse
    args = argparse.Namespace(
        threshold=3, out=str(out_dir), gate_pass=str(out_dir / "nogate"),
        window=14, ledger=str(ledger_path), gov_threshold=2, gov_trust="strict")
    return P._distill(args)


def test_distill_end_to_end_no_id_collision():
    """P1 回归：gov 提案必须拿到不撞的号，且不得被 write_proposals 静默丢弃。"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        today = date.today().isoformat()
        (td / "proposals.jsonl").write_text("".join(json.dumps({
            "id": f"p-{today}-{n:03d}", "kind": "gate-zombie", "suggestion": f"旧提案{n}",
            "evidence": {"count": 0, "refs": ["x"]}, "impact_estimate": "低",
            "status": "pending", "human_note": "", "test_commit": "",
        }, ensure_ascii=False) + "\n" for n in (1, 5)), encoding="utf-8")
        led = td / "ledger.jsonl"
        led.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n"
                               for e in _ledger_entries()), encoding="utf-8")
        assert _run_distill(td, led) == 0
        rows = [json.loads(l) for l in (td / "proposals.jsonl").read_text(
            encoding="utf-8").splitlines() if l.strip()]
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids)), f"ID 撞车: {ids}"
        gov = [r for r in rows if r["kind"] == "gov-criterion"]
        assert len(gov) == 1, f"治理提案被丢弃或未生成: {[r['kind'] for r in rows]}"
        assert int(gov[0]["id"].rsplit("-", 1)[-1]) > 5, f"未接续已用号: {gov[0]['id']}"


def test_distill_first_run_on_empty_out_dir():
    """P2 回归：基线版本在此崩溃（existing UnboundLocalError）。"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        led = td / "ledger.jsonl"
        led.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n"
                               for e in _ledger_entries()), encoding="utf-8")
        out = td / "fresh"
        assert _run_distill(out, led) == 0
        assert (out / "proposals.jsonl").exists()
