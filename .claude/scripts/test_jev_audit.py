"""test_jev_audit.py — 自迭代基座审计层测试（TDD / RED 先行）。

覆盖：
  1. 盲评抽样：不泄露判官结论（防锚定偏差）
  2. 分层 + 确定性：按规则分层、同种子同结果
  3. 诚实指标：混淆矩阵 / TPR / TNR / 一致率 / κ / bootstrap CI / 覆盖率 / 校准等级
  4. 两种账本形态归一：sweep（嵌套 jev）与 verify_loop（顶层字段）
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import jev_audit as audit  # noqa: E402


def _sweep_row(rid: str, rule: str, jev_verdict: str | None,
               human: str | None = None, noul: float | None = None,
               confidence: float | None = None, purpose: str = "x") -> dict:
    return {
        "review_id": rid, "rule_id": rule, "purpose": purpose,
        "jev": {"verdict": jev_verdict, "noul": noul,
                "choice": jev_verdict if jev_verdict in ("符合", "不符合", "不适用") else None,
                "confidence": confidence},
        "human": ({"verdict": human, "reviewer": "tester"} if human else None),
    }


def _loop_row(rid: str, rule: str, verdict: str | None,
              human: str | None = None, noul: float | None = None,
              confidence: float | None = None, purpose: str = "x") -> dict:
    return {
        "review_id": rid, "rule_id": rule, "purpose": purpose,
        "verdict": verdict, "jev_noul": noul, "jev_choice": verdict,
        "jev_confidence": confidence,
        "human": ({"verdict": human, "reviewer": "tester"} if human else None),
    }


# ── 1. 盲评抽样 ────────────────────────────────────────────────────────

def test_blind_sample_never_exposes_judge_verdict():
    rows = [
        _sweep_row("r1", "soul.1.simple", "不符合", human=None, noul=0.2),
        _sweep_row("r2", "soul.1.simple", "符合", human=None, noul=0.9),
    ]
    sample = audit.blind_sample(rows, per_rule=2, seed=7)
    assert len(sample) == 2
    for item in sample:
        assert "jev" not in item
        assert "verdict" not in item
        assert "noul" not in item
        assert "confidence" not in item
        # 人类复核需要的信息仍在
        assert item["review_id"] and item["rule_id"]


def test_blind_sample_is_stratified_per_rule():
    rows = []
    for i in range(5):
        rows.append(_sweep_row(f"a{i}", "rule.a", "符合"))
    for i in range(5):
        rows.append(_sweep_row(f"b{i}", "rule.b", "不符合"))
    sample = audit.blind_sample(rows, per_rule=2, seed=1)
    assert len(sample) == 4
    assert {x["rule_id"] for x in sample} == {"rule.a", "rule.b"}
    assert sum(1 for x in sample if x["rule_id"] == "rule.a") == 2


def test_blind_sample_is_deterministic_for_same_seed():
    rows = [_sweep_row(f"r{i}", "rule.a", "符合") for i in range(20)]
    a = [x["review_id"] for x in audit.blind_sample(rows, per_rule=5, seed=42)]
    b = [x["review_id"] for x in audit.blind_sample(rows, per_rule=5, seed=42)]
    assert a == b


def test_blind_sample_only_includes_unlabeled_rows():
    rows = [
        _sweep_row("r1", "rule.a", "符合", human="符合"),
        _sweep_row("r2", "rule.a", "符合", human=None),
    ]
    sample = audit.blind_sample(rows, per_rule=5, seed=1)
    assert [x["review_id"] for x in sample] == ["r2"]


# ── 2. 账本形态归一 ────────────────────────────────────────────────────

def test_normalize_handles_sweep_shape():
    out = audit.normalize_row(_sweep_row("r1", "rule.a", "不符合", human="符合", noul=0.3))
    assert out["judge"] == "不符合"
    assert out["human"] == "符合"
    assert out["conf"] == 0.3


def test_normalize_handles_loop_shape():
    out = audit.normalize_row(_loop_row("r1", "rule.a", "不适用", human="不适用", confidence=0.99))
    assert out["judge"] == "不适用"
    assert out["human"] == "不适用"
    assert out["conf"] == 0.99


def test_normalize_abstain_is_none():
    out = audit.normalize_row(_sweep_row("r1", "rule.a", "证据不足"))
    assert out["judge"] is None


# ── 3. 诚实指标 ────────────────────────────────────────────────────────

def test_metrics_confusion_matrix_and_rates():
    rows = [
        # human 不符合：判官 2 次对，1 次错
        _sweep_row("t1", "rule.a", "不符合", human="不符合"),
        _sweep_row("t2", "rule.a", "不符合", human="不符合"),
        _sweep_row("t3", "rule.a", "符合", human="不符合"),
        # human 符合：判官 3 次对，1 次错
        _sweep_row("f1", "rule.a", "符合", human="符合"),
        _sweep_row("f2", "rule.a", "符合", human="符合"),
        _sweep_row("f3", "rule.a", "符合", human="符合"),
        _sweep_row("f4", "rule.a", "不符合", human="符合"),
    ]
    m = audit.metrics(rows)["rule.a"]
    assert m["n"] == 7
    assert m["confusion"]["不符合"]["不符合"] == 2
    assert m["confusion"]["不符合"]["符合"] == 1
    assert m["confusion"]["符合"]["符合"] == 3
    assert m["confusion"]["符合"]["不符合"] == 1
    assert round(m["tpr"], 3) == round(2 / 3, 3)
    assert round(m["tnr"], 3) == round(3 / 4, 3)
    assert round(m["agreement"], 3) == round(5 / 7, 3)


def test_metrics_abstain_excluded_from_denominator():
    rows = [
        _sweep_row("a1", "rule.a", "不符合", human="不符合"),
        _sweep_row("a2", "rule.a", "符合", human="不确定"),
    ]
    m = audit.metrics(rows)["rule.a"]
    assert m["n"] == 1
    assert m["abstain"] == 1


def test_metrics_tier_thresholds():
    def rows_with(n):
        return [_sweep_row(f"r{i}", "rule.a", "符合", human="符合") for i in range(n)]
    assert audit.metrics(rows_with(10))["rule.a"]["tier"] == "refuse"
    assert audit.metrics(rows_with(60))["rule.a"]["tier"] == "provisional"
    assert audit.metrics(rows_with(200))["rule.a"]["tier"] == "ok"


def test_metrics_bootstrap_ci_contains_point_estimate():
    rows = [
        _sweep_row("p1", "rule.a", "符合", human="符合"),
        _sweep_row("p2", "rule.a", "符合", human="不符合"),
        _sweep_row("p3", "rule.a", "不符合", human="不符合"),
        _sweep_row("p4", "rule.a", "不符合", human="不符合"),
    ]
    m = audit.metrics(rows, seed=3)["rule.a"]
    lo, hi = m["agreement_ci"]
    assert lo <= m["agreement"] <= hi


def test_metrics_coverage_uses_accept_threshold():
    rows = [
        _sweep_row("c1", "rule.a", "符合", human="符合", confidence=0.9),
        _sweep_row("c2", "rule.a", "符合", human="符合", confidence=0.5),
        _sweep_row("c3", "rule.a", "符合", human="符合", noul=0.8),
        _sweep_row("c4", "rule.a", "符合", human="符合", noul=0.2),
    ]
    m = audit.metrics(rows, accept_at={"rule.a": 0.7})["rule.a"]
    # c1 conf=0.9 ✓；c2 0.5 ✗；c3 noul=0.8 ✓；c4 0.2 ✗
    assert round(m["coverage"], 3) == 0.5


def test_metrics_skips_unlabeled_rows():
    rows = [_sweep_row("r1", "rule.a", "符合", human=None)]
    assert audit.metrics(rows) == {}
