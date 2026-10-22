"""test_gov_distill.py — B 档治理域蒸馏（治理部分自迭代，A+B 开工 2026-10-22）

kind=gov-criterion 从判官账本（.omc/state/jev/reviews.jsonl）蒸馏：
  证据 = 人判备注（note_trust 闸门：reviewer 是真人 + label_source=contemporaneous_human）
  门禁 = 冷却期（14 天/同规则，rejected 不复活）+ 规则原文锁定 + 首批范围白名单
安全边界：提案只进 .omc/proposals/；accept 只登记 + 生成判官回放单，
冻结域（AGENTS.md/kernel.md/hooks）永不自动落盘。

2026-10-22 审计修复：原夹具虚构 reviewer=lucas.liang / label_source="human"（真实
schema 无此值），导致「把 repo-history / claude-proxy 备注当人判」的 P0 缺陷永不可见。
现夹具按真实账本形状（resolution 记录 + reviewer 真值）构造，并显式覆盖非人判路径。
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


def _ledger_entries():
    """形状对齐真实账本：resolution 记录无 rule_id，靠 review_id 尾段回连规则。"""
    return [
        # soul.7.gain：2 条人判 + 1 条无备注
        {"kind": "resolution", "review_id": "p-dc662404d55f-soul.7.gain",
         "human": _human("重建 skill 是替换旧实现，判据应写明替换算增益")},
        {"kind": "resolution", "review_id": "p-aaaa1111bbbb-soul.7.gain",
         "human": _human("删死链属消除冗余")},
        {"kind": "pending", "review_id": "p-cccc2222dddd-soul.7.gain",
         "rule_id": "soul.7.gain", "human": None},
        # soul.1.simple：只有 1 条人判 → 低于阈值
        {"kind": "resolution", "review_id": "p-eeee3333ffff-soul.1.simple",
         "human": _human("删 tombstone 死链，仓库认可")},
    ]


def _ledger_untrusted():
    """真实账本现状：全部备注都是 repo-history / claude-proxy，无一条人判。"""
    return [
        {"kind": "resolution", "review_id": "p-dc662404d55f-soul.7.gain",
         "human": {"verdict": "符合", "note": "重建 skill 是替换旧实现",
                   "reviewer": "claude-proxy"}},
        {"kind": "resolution", "review_id": "p-aaaa1111bbbb-soul.7.gain",
         "human": {"verdict": "符合", "note": "删死链属消除冗余",
                   "reviewer": "repo-history"}},
    ]


# ── 蒸馏基本行为 ──────────────────────────────────────────────

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
    assert p["evidence"]["human_judged"] == 2
    assert p["evidence"]["trust"] == "human"
    assert len(p["evidence"]["refs"]) == 2
    assert p["evidence"]["locked_rule_text"], "规则原文必须随提案锁定"
    assert p["evidence"]["locked_source"] == "AGENTS.md:20"


def test_gov_id_follows_documented_schema():
    """P1 回归：ID 必须是 p-YYYY-MM-DD-NNN，不得加 -gov 之类的段。"""
    import re
    props = P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                 asof=date(2026, 10, 22), seq_start=17)
    assert props[0]["id"] == "p-2026-10-22-018", props[0]["id"]
    assert re.match(r"^p-\d{4}-\d{2}-\d{2}-\d{3}$", props[0]["id"])


def test_gov_distill_below_threshold_yields_nothing():
    assert P.make_gov_proposals(_ledger_entries(), threshold=3,
                                registry=None, asof=date(2026, 10, 22)) == []


def test_gov_distill_empty_ledger_yields_nothing():
    assert P.make_gov_proposals([], threshold=2, registry=None,
                                asof=date(2026, 10, 22)) == []


# ── P0：证据可信度闸门 ────────────────────────────────────────

def test_non_human_notes_do_not_count_in_strict_mode(capsys):
    """真实账本现状：全是 repo-history/claude-proxy → 不得造提案，且要喊出原因。"""
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
    """同一条备注重复记录不算两条证据；账本无 verdict 要如实写缺口，不写 '?'。"""
    dup = _ledger_entries() + [_ledger_entries()[0]]
    props = P.make_gov_proposals(dup, threshold=2, registry=None, asof=date(2026, 10, 22))
    refs = props[0]["evidence"]["refs"]
    assert len(refs) == len(set(refs)), f"refs 未去重: {refs}"
    assert "缺口" in refs[0] and "判官=?" not in refs[0], refs[0]


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


# ── 冷却期：三个边界都钉死（原来只测了 12 天，14 天边界空缺）──────

def _seeded_jsonl(td: Path, ts: str, status: str = "rejected") -> Path:
    j = td / "proposals.jsonl"
    j.write_text(json.dumps({
        "id": f"p-{ts}-001", "kind": "gov-criterion", "suggestion": "改 soul.7.gain 判据",
        "status": status, "human_note": "方向不对", "ts": ts,
        "evidence": {"rule_ids": ["soul.7.gain"]},
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    return j


def test_gov_cooldown_gap13_suppressed():
    with tempfile.TemporaryDirectory() as td:
        j = _seeded_jsonl(Path(td), "2026-10-09")  # 差 13 天
        assert P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                    asof=date(2026, 10, 22), jsonl_path=j) == []


def test_gov_cooldown_gap14_boundary_allowed():
    """边界语义：满 14 天即视为冷却结束（第 15 天起可提）。此处把语义钉死。"""
    with tempfile.TemporaryDirectory() as td:
        j = _seeded_jsonl(Path(td), "2026-10-08")  # 恰好 14 天
        assert len(P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                        asof=date(2026, 10, 22), jsonl_path=j)) == 1


def test_gov_cooldown_gap15_allowed():
    with tempfile.TemporaryDirectory() as td:
        j = _seeded_jsonl(Path(td), "2026-10-07")
        assert len(P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                        asof=date(2026, 10, 22), jsonl_path=j)) == 1


def test_gov_pending_proposal_also_cooldown():
    with tempfile.TemporaryDirectory() as td:
        j = _seeded_jsonl(Path(td), "2026-10-18", status="pending")
        assert P.make_gov_proposals(_ledger_entries(), threshold=2, registry=None,
                                    asof=date(2026, 10, 22), jsonl_path=j) == []


# ── 首批范围白名单（AGENTS.md）+ kernel.md 样本闸门 ─────────────

def test_out_of_scope_source_skipped(capsys):
    """README.md 源规则攒够备注也不得越界（原实现无白名单，靠巧合合规）。"""
    reg = {"proj.port.9001": {"text": "端口 9001", "source": "README.md:307"}}
    led = [{"rule_id": "proj.port.9001", "human": _human("端口应放宽")},
           {"rule_id": "proj.port.9001", "human": _human("确实该放宽")}]
    props = P.make_gov_proposals(led, threshold=2, registry=reg,
                                 asof=date(2026, 10, 22))
    assert props == []
    assert "白名单" in capsys.readouterr().out


def test_kernel_source_gated_by_sample_size(capsys):
    reg = {"k.1": {"text": "冻结规则", "source": ".claude/kernel.md:12"}}
    led = [{"rule_id": "k.1", "human": _human("a")},
           {"rule_id": "k.1", "human": _human("b")}]
    props = P.make_gov_proposals(led, threshold=2, registry=reg, asof=date(2026, 10, 22))
    assert props == [], "样本 <200 不得蒸馏冻结域规则"
    assert "冻结域" in capsys.readouterr().out


# ── accept 边界：只登记 + 回放单，绝不碰冻结域 ────────────────

def test_gov_accept_only_registers_never_writes_frozen(monkeypatch):
    """"""
    real_reg = Path(__file__).resolve().parent / "jev_rules.yaml"
    reg_before = real_reg.read_text(encoding="utf-8")
    frozen = [Path(__file__).resolve().parents[2] / "AGENTS.md",
              Path(__file__).resolve().parents[2] / ".claude" / "kernel.md"]
    frozen_before = {f: f.read_text(encoding="utf-8") for f in frozen}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        monkeypatch.setenv("CARROROS_GOV_REPLAY_DIR", str(td / "replay"))
        monkeypatch.setattr(P, "GOV_REPLAY_DIR", str(td / "replay"))
        j = td / "proposals.jsonl"
        j.write_text(json.dumps({
            "id": "p-2026-10-22-001", "kind": "gov-criterion",
            "target": ".claude/scripts/jev_rules.yaml",
            "suggestion": "改 soul.7.gain 判据：替换/删除属消除冗余应算增益",
            "evidence": {"count": 2, "refs": ["r1", "r2"], "human_judged": 2,
                          "trust": "human",
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
    for f, txt in frozen_before.items():
        assert f.read_text(encoding="utf-8") == txt, f"冻结域被改：{f}"


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
            "evidence": {"count": 2, "refs": ["ref-1", "ref-2"], "human_judged": 2,
                          "trust": "human",
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
        assert "更高" in txt and "≥" not in txt, "采纳闸门不得被放宽成 ≥"


# ── 端到端：_distill（原来零覆盖，重复 ID 与首跑崩溃都是手工冒烟才发现的）──

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
        # 同一份 proposals.jsonl 里已占用 p-...-001 与 p-...-005
        (td / "proposals.jsonl").write_text("".join(json.dumps({
            "id": f"p-2026-10-22-{n:03d}", "kind": "gate-zombie", "suggestion": f"旧提案{n}",
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
        out = td / "fresh"
        led = td / "ledger.jsonl"
        led.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n"
                               for e in _ledger_entries()), encoding="utf-8")
        assert _run_distill(out, led) == 0
        assert (out / "proposals.jsonl").exists()
