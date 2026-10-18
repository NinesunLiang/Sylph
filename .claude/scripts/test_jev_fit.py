"""jev_fit.py 的依赖 TDD —— 判据拟合闭环。

闭环的价值在于「用回放证明判据改得更好了」。
没有回放的判据修改等于拍脑袋，所以这里把回放路径测死。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_fit as jf  # noqa: E402


class FakeClient:
    """按 rule_id 返回预设判定，用于回放。"""

    def __init__(self, verdict_by_rule: dict):
        self.map = verdict_by_rule
        self.calls = 0

    def judge(self, state, questions, model):
        self.calls += 1
        answers = {}
        for rid in questions:
            v = self.map.get(rid, "符合")
            if v == "符合":
                answers[rid] = {"type": "noul", "noul": 0.95}
            elif v == "不符合":
                answers[rid] = {"type": "noul", "noul": 0.05}
            else:
                answers[rid] = {"type": "noul", "noul": 0.50}
        return {
            "answers": answers, "id": "x", "model": f"{model}-20260917",
            "provider": "TypeSafe",
            "usage": {"input_tokens": 1, "output_tokens": 1, "cost": 0.0},
        }


def _entry(rule_id, jev, human, note="", reviewer="human"):
    return {
        "review_id": f"r-{rule_id}-{human}",
        "recorded_at": "2026-10-15T00:00:00Z",
        "rule_id": rule_id,
        "registry_version": "v3-draft",
        "change_fingerprint": "abc",
        "purpose": "测试改动",
        "change": "diff ...",
        "changed_paths": ["a.py"],
        "repo_context": "",
        "jev": {"verdict": jev, "noul": 0.5, "choice": None, "confidence": None},
        "human": {"verdict": human, "note": note, "reviewer": reviewer},
    }


def test_ledger_roundtrip(tmp_path):
    led = tmp_path / "reviews.jsonl"
    jf.append_review(_entry("soul.1.simple", "符合", "不符合"), led)
    jf.append_review(_entry("soul.7.gain", "符合", "符合"), led)
    rows = jf.load_reviews(led)
    assert len(rows) == 2
    assert rows[0]["rule_id"] == "soul.1.simple"


def test_ledger_missing_is_empty(tmp_path):
    assert jf.load_reviews(tmp_path / "nope.jsonl") == []


# ── 待复核队列：低置信自己攒样本 ───────────────────────────────────
def test_pending_enqueue_and_resolve(tmp_path):
    led = tmp_path / "reviews.jsonl"
    jf.enqueue_pending({
        "review_id": "p-1", "rule_id": "soul.1.simple",
        "jev": {"verdict": "不能判定", "noul": None, "choice": "不符合", "confidence": 0.27},
        "purpose": "改了钩子", "change": "diff", "changed_paths": ["a.py"],
        "repo_context": "", "human": None,
    }, led)
    rows = jf.load_reviews(led)
    assert len(rows) == 1
    assert rows[0]["human"] is None, "入队时应无人工判定"

    # 复核结论以另一条记录追加，读的时候自动合并
    jf.append_review({
        "kind": "resolution", "review_id": "p-1",
        "human": {"verdict": "符合", "note": "这条改动跟 API 类型无关", "reviewer": "lu"},
    }, led)
    rows = jf.load_reviews(led)
    assert len(rows) == 1, "resolution 不应变成新条目"
    assert rows[0]["human"]["verdict"] == "符合"
    assert rows[0]["human"]["reviewer"] == "lu"


def test_pending_enqueue_is_idempotent(tmp_path):
    """同一条未复核的重复入队不得堆积。"""
    led = tmp_path / "reviews.jsonl"
    entry = {"review_id": "p-1", "rule_id": "soul.1.simple", "jev": {},
             "purpose": "", "change": "diff x", "changed_paths": [], "repo_context": "",
             "human": None}
    jf.enqueue_pending(entry, led)
    jf.enqueue_pending(entry, led)
    assert len(jf.load_reviews(led)) == 1


def test_analyze_skips_pending_rows():
    """待复核条目还没人判，不能进一致率 —— 否则 analyze 会直接崩。

    这条测试要**把 pending 原样喂给 analyze**，不能自己先过滤掉，
    否则测的是测试自己，不是被测代码。
    """
    rows = [
        _entry("soul.1.simple", "符合", "符合"),
        {"review_id": "p-1", "rule_id": "soul.1.simple", "jev": {"verdict": "不能判定"},
         "purpose": "", "change": "", "human": None},
        {"review_id": "p-2", "rule_id": "know.official-first", "jev": {"verdict": "不能判定"},
         "purpose": "", "change": "", "human": None},
    ]
    rep = jf.analyze(rows)
    assert rep["soul.1.simple"]["total"] == 1, "待复核不得计入分母"
    assert "know.official-first" not in rep, "只有待复核、无人判的规则不该出现"


# ── 外部基准：样本量分档与 κ ───────────────────────────────────────
def test_sample_tier_uses_external_baseline():
    """样本量分档取 jev-eval 的做法：<50 拒绝、50~200 临时、>=200 可用。"""
    assert jf.sample_tier(3) == "refuse"
    assert jf.sample_tier(49) == "refuse"
    assert jf.sample_tier(50) == "provisional"
    assert jf.sample_tier(199) == "provisional"
    assert jf.sample_tier(200) == "ok"


def test_cohen_kappa_penalises_chance_agreement():
    """原始一致率会在类别不平衡时虚高，κ 把碰巧一致扣掉。"""
    # 全判「符合」也能拿到 1.0 原始一致率，但 κ 会暴露问题
    all_same = [("符合", "符合")] * 8 + [("不符合", "不符合")] * 2
    assert jf.cohen_kappa(all_same) == 1.0
    # 完全随机（各类占比相同）κ ≈ 0
    chance = [("符合", "符合"), ("不符合", "不符合"),
              ("符合", "不符合"), ("不符合", "符合")]
    assert jf.cohen_kappa(chance) == 0.0


def test_cohen_kappa_needs_two_samples():
    assert jf.cohen_kappa([]) is None
    assert jf.cohen_kappa([("符合", "符合")]) is None


# ── 留出集：防止「一边挑阈值一边打分」 -------------------------------------------------------------------
def test_holdout_split_is_deterministic():
    rows = [{"review_id": f"r-{i}", "rule_id": "x", "human": {"verdict": "符合"}} for i in range(50)]
    t1, h1 = jf.split_holdout(rows, frac=0.3, seed="s")
    t2, h2 = jf.split_holdout(rows, frac=0.3, seed="s")
    assert [r["review_id"] for r in h1] == [r["review_id"] for r in h2], "同种子必须切出同一批"
    assert len(t1) + len(h1) == 50
    assert 0 < len(h1) < 50, "两集都应有内容"


def test_holdout_split_different_seed_differs():
    rows = [{"review_id": f"r-{i}", "rule_id": "x", "human": {"verdict": "符合"}} for i in range(50)]
    _, h1 = jf.split_holdout(rows, frac=0.3, seed="s1")
    _, h2 = jf.split_holdout(rows, frac=0.3, seed="s2")
    assert [r["review_id"] for r in h1] != [r["review_id"] for r in h2]


def test_holdout_frac_bounds():
    rows = [{"review_id": f"r-{i}", "rule_id": "x", "human": {"verdict": "符合"}} for i in range(50)]
    _, h = jf.split_holdout(rows, frac=0.0)
    assert h == []
    _, h = jf.split_holdout(rows, frac=1.0)
    assert len(h) == 50


# ── 标签来源：参考答案的可信度必须显式 -----------------------------------------------------------------
def test_label_breakdown():
    rows = [
        _entry("a", "符合", "符合"),
        _entry("b", "符合", "符合"),
    ]
    rows[0]["human"]["label_source"] = "contemporaneous_human"
    rows[1]["human"]["label_source"] = "hindsight_repo"
    b = jf.label_breakdown(rows)
    assert b["contemporaneous_human"] == 1
    assert b["hindsight_repo"] == 1


def test_label_breakdown_marks_unspecified_and_skips_pending():
    rows = [
        _entry("a", "符合", "符合"),
        {"review_id": "p", "rule_id": "a", "jev": {}, "purpose": "", "change": "", "human": None},
    ]
    rows[0]["human"].pop("label_source", None)
    b = jf.label_breakdown(rows)
    assert b == {"unspecified": 1}, "待复核条目不得计入标签统计"


def test_only_contemporaneous_human_is_trusted():
    """事后反推的标签有后见之明偏差，不能和同期人工判定等价。"""
    assert jf.TRUSTED_LABEL == "contemporaneous_human"
    assert "hindsight_repo" in jf.LABEL_SOURCES
    assert "llm_proxy" in jf.LABEL_SOURCES


def test_ledger_rejects_secret(tmp_path):
    bad = _entry("soul.1.simple", "符合", "符合", note="Bearer sk-or-v1-deadbeef")
    with pytest.raises(ValueError):
        jf.append_review(bad, tmp_path / "reviews.jsonl")


# ── analyze ────────────────────────────────────────────────────────
def test_analyze_computes_agreement():
    rep = jf.analyze([
        _entry("soul.1.simple", "符合", "符合"),
        _entry("soul.1.simple", "不符合", "符合"),
        _entry("soul.7.gain", "符合", "符合"),
    ])
    assert rep["soul.1.simple"]["total"] == 2
    assert rep["soul.1.simple"]["agree"] == 1
    assert rep["soul.1.simple"]["agreement"] == 0.5
    assert rep["soul.7.gain"]["agreement"] == 1.0
    assert len(rep["soul.1.simple"]["diverged"]) == 1


def test_analyze_treats_uncertain_as_abstain():
    """「不确定」是弃权，不进分母 —— 否则人会靠弃权刷高一致率。"""
    rep = jf.analyze([
        _entry("soul.1.simple", "符合", "符合"),
        _entry("soul.1.simple", "不符合", "不确定"),
    ])
    assert rep["soul.1.simple"]["total"] == 1
    assert rep["soul.1.simple"]["abstain"] == 1
    assert rep["soul.1.simple"]["agreement"] == 1.0


def test_analyze_diverged_carries_evidence():
    rep = jf.analyze([_entry("soul.1.simple", "不符合", "符合", note="这条其实是清理", reviewer="lu")])
    d = rep["soul.1.simple"]["diverged"][0]
    assert d["human"] == "符合" and d["jev"] == "不符合"
    assert d["note"] == "这条其实是清理"
    assert d["reviewer"] == "lu"


# ── replay ─────────────────────────────────────────────────────────
def test_replay_uses_human_labels(tmp_path):
    rows = [
        _entry("soul.1.simple", "符合", "符合"),
        _entry("soul.1.simple", "不符合", "符合"),
    ]
    # 新登记表下模型全判「符合」→ 与人工判定 2/2 一致
    rep = jf.replay(rows, SCRIPTS_DIR / "jev_rules.yaml", FakeClient({"soul.1.simple": "符合"}))
    assert rep["soul.1.simple"]["total"] == 2
    assert rep["soul.1.simple"]["agree"] == 2
    assert rep["soul.1.simple"]["agreement"] == 1.0


def test_replay_detects_regression(tmp_path):
    rows = [_entry("soul.1.simple", "符合", "符合")]
    rep = jf.replay(rows, SCRIPTS_DIR / "jev_rules.yaml", FakeClient({"soul.1.simple": "不符合"}))
    assert rep["soul.1.simple"]["agreement"] == 0.0
    assert rep["soul.1.simple"]["diverged"][0]["human"] == "符合"


def test_replay_skips_abstain_and_script_rules():
    rows = [
        _entry("soul.1.simple", "符合", "不确定"),
        _entry("proj.c7.redline", "符合", "符合"),  # script 类，不进 Jev
    ]
    rep = jf.replay(rows, SCRIPTS_DIR / "jev_rules.yaml", FakeClient({}))
    assert rep == {}, "弃权与 script 类都不应参与回放"


def test_fingerprint_is_stable_and_content_sensitive():
    a = jf._fingerprint("p", "c", ["x.py"])
    assert a == jf._fingerprint("p", "c", ["x.py"])
    assert a != jf._fingerprint("p", "c2", ["x.py"])
    # 路径顺序不影响指纹
    assert jf._fingerprint("p", "c", ["a.py", "b.py"]) == jf._fingerprint("p", "c", ["b.py", "a.py"])


# ── 人机接口：少打字、且不会撞车 ────────────────────────────────────
def test_shortest_unique_substring():
    ids = ["p-aaaa1111-soul.1.reuse", "p-bbbb2222-soul.1.reuse",
           "p-aaaa1111-soul.7.gain"]
    s = jf.shortest_unique_substring(ids[0], ids)
    assert s in ids[0] and all(s not in x for x in ids[1:]), s
    assert len(s) <= 8, "应当尽量短"


def test_shortest_unique_substring_handles_collision():
    """不能用「末 N 位」偷懒：同一规则多条待复核时末位会撞车。"""
    ids = ["p-11111111-soul.1.reuse", "p-22222222-soul.1.reuse"]
    a = jf.shortest_unique_substring(ids[0], ids)
    b = jf.shortest_unique_substring(ids[1], ids)
    assert a != b, "两条必须给出不同前缀"
    assert all(a not in x for x in ids[1:])
    assert all(b not in x for x in ids[:-1])


def test_pending_prints_usable_commands(tmp_path, capsys):
    """打印出来的命令必须真的能跑 —— 前缀唯一、可直接复制。"""
    led = tmp_path / "reviews.jsonl"
    for i in (1, 2):
        jf.enqueue_pending({
            "review_id": f"p-{i:08d}-soul.1.reuse", "rule_id": "soul.1.reuse",
            "jev": {"verdict": "不能判定"}, "purpose": "x", "change": f"diff {i}",
            "changed_paths": [], "repo_context": "", "human": None,
        }, led)

    class A:
        ledger = str(led)

    jf.cmd_pending(A())
    out = capsys.readouterr().out
    prefixes = [
        ln.split("--review-id ")[1].split()[0]
        for ln in out.splitlines()
        if "--review-id " in ln and "可以只给" not in ln
    ]
    assert len(prefixes) == 2
    rows = jf.load_reviews(led)
    for p in prefixes:
        full, err = jf._resolve_review_id(p, rows)
        assert full and not err, f"{p} 不能唯一定位：{err}"


def test_resolve_review_id_reports_ambiguity():
    rows = [{"review_id": "p-aa-soul.1.reuse"}, {"review_id": "p-ab-soul.1.reuse"}]
    full, err = jf._resolve_review_id("p-a", rows)
    assert full is None and "不唯一" in err
    full, err = jf._resolve_review_id("nope", rows)
    assert full is None and "没有匹配" in err


# ── 2026-10-18 降噪：空 diff 不入队 / 同指纹去重 / 每规则上限 ────────

def _pending_entry(rid: str, rule: str, change: str, fp: str | None = None) -> dict:
    e = {"review_id": rid, "rule_id": rule, "change": change,
         "jev": {"verdict": "证据不足"}}
    if fp is not None:
        e["change_fingerprint"] = fp
    return e


def test_enqueue_skips_empty_change(tmp_path):
    led = tmp_path / "reviews.jsonl"
    jf.enqueue_pending(_pending_entry("p-1", "rule.a", ""), led)
    assert not led.exists() or not led.read_text().strip()


def test_enqueue_dedupes_same_rule_and_fingerprint(tmp_path):
    led = tmp_path / "reviews.jsonl"
    jf.enqueue_pending(_pending_entry("p-1", "rule.a", "diff A", fp="fp-1"), led)
    jf.enqueue_pending(_pending_entry("p-2", "rule.a", "diff A", fp="fp-1"), led)
    assert len(jf.load_reviews(led)) == 1


def test_enqueue_keeps_different_fingerprints(tmp_path):
    led = tmp_path / "reviews.jsonl"
    jf.enqueue_pending(_pending_entry("p-1", "rule.a", "diff A", fp="fp-1"), led)
    jf.enqueue_pending(_pending_entry("p-2", "rule.a", "diff B", fp="fp-2"), led)
    assert len(jf.load_reviews(led)) == 2


def test_enqueue_caps_pending_per_rule(tmp_path):
    led = tmp_path / "reviews.jsonl"
    for i in range(jf.MAX_PENDING_PER_RULE + 5):
        jf.enqueue_pending(_pending_entry(f"p-{i}", "rule.a", f"diff {i}", fp=f"fp-{i}"), led)
    assert len(jf.load_reviews(led)) == jf.MAX_PENDING_PER_RULE
