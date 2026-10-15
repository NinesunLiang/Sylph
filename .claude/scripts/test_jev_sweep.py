"""P1-a 离线 JEV-C shadow 的依赖 TDD。

对应 plan.md「P1 施工细则 §6 依赖 TDD」的 15 条用例。
先红后绿：本文件先写，实现前应当全部 FAIL。

设计边界（必须一直成立）：
  · 不接 verify 路径，不碰 carros_base.py
  · 不改 token.json / plan.md / executor.md / audit
  · 不调用 complete_step_atomic，不改变任何 Goal 状态
  · 不接收、不写入真实 key
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_sweep as js  # noqa: E402


RULES_PATH = SCRIPTS_DIR / "jev_rules.yaml"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def registry() -> dict:
    return js.load_registry(RULES_PATH)


class FakeJevClient:
    """假客户端：不联网，按预设返回。"""

    def __init__(self, answers: dict, usage: dict | None = None):
        self.answers = answers
        self.calls: list[dict] = []
        self.usage = usage or {"input_tokens": 100, "output_tokens": 10, "cost": 0.00002}

    def judge(self, state, questions, model):
        self.calls.append({"state": state, "questions": questions, "model": model})
        return {
            "answers": {k: v for k, v in self.answers.items() if k in questions},
            "id": "gen-dec-test",
            "model": f"{model}-20260917",
            "provider": "TypeSafe",
            "usage": self.usage,
        }


# ── 1. 登记表完整性 ────────────────────────────────────────────────
def test_registry_complete(registry):
    required = {
        "rule_id", "source", "text", "rule_target", "judge_by",
        "criteria_true", "criteria_false", "failure_action",
    }
    problems = js.validate_registry(registry)
    assert problems == [], f"登记表缺字段/非法: {problems}"
    for rule in registry["rules"]:
        missing = required - set(rule)
        assert not missing, f"{rule.get('rule_id')} 缺字段 {missing}"


def test_registry_target_values_are_valid(registry):
    for rule in registry["rules"]:
        assert rule["rule_target"] in ("code", "behavior"), rule["rule_id"]
        assert rule["judge_by"] in ("script", "jev", "hybrid"), rule["rule_id"]


# ── 2. 登记表与真源一致 ────────────────────────────────────────────
def test_registry_matches_sources(registry):
    mismatches = js.check_sources(registry, ROOT)
    assert mismatches == [], f"登记表与真源不一致: {mismatches}"


# ── 3. 只判代码：登记表必须拒绝行为类规则 ──────────────────────────
def test_registry_contains_code_rules_only(registry):
    """JEV-C 的检测对象是 commit 内容。AI 行为在检测时已成定局，事后算账零价值。"""
    for rule in registry["rules"]:
        assert rule["rule_target"] == "code", (
            f"{rule['rule_id']} 是行为类规则，不得进入本表；"
            "行为类应由执行前引导 + 执行中 hook 门禁承载"
        )


def test_validate_rejects_behavior_rule():
    registry = {
        "rules": [{
            "rule_id": "soul.2.verify", "source": "AGENTS.md:15", "text": "x",
            "rule_target": "behavior", "judge_by": "jev",
            "criteria_true": "a", "criteria_false": "b", "failure_action": "c",
        }]
    }
    problems = js.validate_registry(registry)
    assert any("行为类规则" in p for p in problems), problems


def test_behavior_rules_are_recorded_as_moved_out(registry):
    """移出去的行为类规则必须登记去向，审计时不重复立项。"""
    moved = registry.get("behavior_rules_moved_out") or []
    assert moved, "应当登记行为类规则的去向"
    for item in moved:
        assert item.get("where"), f"{item.get('rule_id')} 没写去向"


# ── 4. script 类不得送 Jev ─────────────────────────────────────────
def test_script_rules_not_sent_to_jev(registry):
    script_rules, jev_rules = js.split_by_judge(registry["rules"])
    assert script_rules, "应当存在 script 类规则"
    questions = js.build_questions(jev_rules)
    for rule in script_rules:
        assert rule["rule_id"] not in questions, f"{rule['rule_id']} 是 script 类却进了 Jev 请求"


# ── 5. 原语选择 ────────────────────────────────────────────────────
def test_primitive_selection(registry):
    binary = [r for r in registry["rules"] if js.primitive_for(r) == "noul"]
    assert binary, "应当有二值规则"
    tri = {"rule_id": "x", "judge_by": "jev", "allow_not_applicable": True}
    assert js.primitive_for(tri) == "choice"


def test_build_questions_carries_rule_text(registry):
    _, jev_rules = js.split_by_judge(registry["rules"])
    questions = js.build_questions(jev_rules)
    for rule in jev_rules:
        q = questions[rule["rule_id"]]
        blob = json.dumps(q, ensure_ascii=False)
        # 规则原文必须完整传入，不能只给 rule_id
        anchor = rule["text"][:16]
        assert anchor in blob, f"{rule['rule_id']} 的规则原文没传进 criteria"


def test_build_questions_subject_defaults_to_change(registry):
    """默认仍在判「本次改动」—— 扫 commit 的老路径不能因为新参数变了味。"""
    _, jev_rules = js.split_by_judge(registry["rules"])
    q = js.build_questions(jev_rules)
    blob = json.dumps(q, ensure_ascii=False)
    assert "本次改动" in blob


def test_build_questions_subject_is_swappable(registry):
    """体检存量资源时必须换主语。

    不然 Jev 会去判一个根本不存在的「本次改动」—— 问题问错了，
    它答得再确定也没意义。这是本参数存在的唯一理由。

    注意只断言**外层包装**用了新主语，不断言整块文本里没有「本次改动」：
    规则原文自己就写着「本次改动是在消除冗余」（soul.7.gain 等），
    那是规则内容，不该也不能被替换掉。
    """
    _, jev_rules = js.split_by_judge(registry["rules"])
    q = js.build_questions(jev_rules, "这个存量机制文件")

    for rule in jev_rules:
        entry = q[rule["rule_id"]]
        assert entry["instructions"].startswith("这个存量机制文件"), (
            f"{rule['rule_id']} 的问题没换主语"
        )
        for key in ("true", "false", "符合", "不符合"):
            if key in entry["criteria"]:
                assert entry["criteria"][key].startswith("这个存量机制文件"), (
                    f"{rule['rule_id']}.{key} 的判据没换主语"
                )
        # 规则原文照旧必须完整在
        anchor = rule["text"][:16]
        assert anchor in json.dumps(entry, ensure_ascii=False), (
            f"{rule['rule_id']} 换主语后丢了规则原文"
        )


# ── 6. 阈值三段 ────────────────────────────────────────────────────
def test_threshold_three_bands():
    assert js.verdict_from_noul(0.95, 0.85, 0.30) == js.VERDICT_OK
    assert js.verdict_from_noul(0.50, 0.85, 0.30) == js.VERDICT_INSUFFICIENT
    assert js.verdict_from_noul(0.10, 0.85, 0.30) == js.VERDICT_BAD
    # 边界值必须落在正确一侧
    assert js.verdict_from_noul(0.85, 0.85, 0.30) == js.VERDICT_OK
    assert js.verdict_from_noul(0.30, 0.85, 0.30) == js.VERDICT_BAD


def test_choice_threshold():
    assert js.verdict_from_choice("符合", 0.9, 0.8) == js.VERDICT_OK
    assert js.verdict_from_choice("不符合", 0.9, 0.8) == js.VERDICT_BAD
    assert js.verdict_from_choice("不适用", 0.9, 0.8) == js.VERDICT_NA
    # 置信度不足 → 不能判定：低置信一律不给结论
    assert js.verdict_from_choice("符合", 0.3, 0.8) == js.VERDICT_UNDECIDED


def test_choice_uses_confidence_at_not_accept_at():
    """三值用 confidence_at；三选项均分时 confidence≈0.33，
    沿用二值的 accept_at 会让判定大面积落进「证据不足」，等于工具不表态。"""
    rule = {
        "rule_id": "x", "source": "AGENTS.md:1", "text": "t",
        "rule_target": "code", "judge_by": "jev", "allow_not_applicable": True,
        "criteria_true": "a", "criteria_false": "b", "failure_action": "c",
        "accept_at": 0.85, "reject_at": 0.30, "confidence_at": 0.55,
    }
    row = js._row(rule)
    js._apply_answer(row, rule, {
        "type": "choice", "choice": "符合", "confidence": 0.72,
        "probabilities": {"符合": 0.72, "不符合": 0.1, "不适用": 0.18},
    })
    assert row["verdict"] == js.VERDICT_OK
    # 低于 confidence_at → 不给结论
    js._apply_answer(row, rule, {
        "type": "choice", "choice": "符合", "confidence": 0.40,
        "probabilities": {},
    })
    assert row["verdict"] == js.VERDICT_UNDECIDED


def test_low_confidence_never_yields_a_conclusion():
    """低置信一律不给结论。

    模型没把握时，无论它选了「不符合」还是「符合」，都不能包装成结论 ——
    既不能把瞎猜当违规，也不能把瞎猜当通过。

    实测：某次纯 .py 钩子改动的 proj.api.type-align 选了「不符合」但 conf 只有 0.27
    （三选项均匀分布是 0.33，等于瞎猜），改动内容跟 API 类型毫无关系。
    """
    reg = js.load_registry(RULES_PATH)
    _, jev_rules = js.split_by_judge(reg["rules"])
    answers = {
        r["rule_id"]: {
            "type": "choice", "choice": "不符合", "confidence": 0.27,
            "probabilities": {"不符合": 0.27},
        }
        for r in jev_rules
    }
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers),
        registry=reg, rules_to_judge=jev_rules, dry_run=True,
    )
    seen = 0
    for row in result["results"]:
        rule = next(r for r in reg["rules"] if r["rule_id"] == row["rule_id"])
        if rule.get("requires"):
            continue  # 判定单元不匹配，走「不适用」
        if row["jev_primitive"] == "choice":
            assert row["verdict"] == js.VERDICT_UNDECIDED, row["rule_id"]
            # 原始信号要留档 —— 它是「规则判据可能有问题」的证据
            assert row["raw_choice"] == "不符合", row["rule_id"]
            assert row["uncertain_note"], row["rule_id"]
            seen += 1
    assert seen, "应当检查到至少一条三值规则"
    assert result["summary"]["violated"] == [], "低置信不得产出结论"


def test_uncertain_on_key_rule_escalates_for_rule_tuning():
    """关键规则低置信 → 升级给人，但目的是复核**规则判据**，不是判这次改动。"""
    reg = js.load_registry(RULES_PATH)
    _, jev_rules = js.split_by_judge(reg["rules"])
    answers = {
        r["rule_id"]: {
            "type": "choice", "choice": "不符合", "confidence": 0.27,
            "probabilities": {},
        }
        for r in jev_rules
    }
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers),
        registry=reg, rules_to_judge=jev_rules, dry_run=True,
    )
    escalated = {e["rule_id"] for e in result["summary"]["escalate_for_rule_tuning"]}
    assert escalated, "关键规则低置信时应当升级复核"
    marked = {r["rule_id"] for r in reg["rules"] if r.get("escalate_when_uncertain")}
    assert escalated <= marked, "只升级标了 escalate_when_uncertain 的规则"
    assert "soul.1.simple" in escalated, "最高权重哲学规则应在升级名单里"


def test_unimportant_rule_uncertainty_does_not_escalate():
    """不重要的低置信直接放着不管，不打扰人。"""
    reg = js.load_registry(RULES_PATH)
    _, jev_rules = js.split_by_judge(reg["rules"])
    quiet = [r["rule_id"] for r in jev_rules if not r.get("escalate_when_uncertain")]
    assert quiet, "应当存在不需要升级的规则"
    answers = {
        r["rule_id"]: {"type": "choice", "choice": "不符合", "confidence": 0.10,
                       "probabilities": {}}
        for r in jev_rules
    }
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers),
        registry=reg, rules_to_judge=jev_rules, dry_run=True,
    )
    escalated = {e["rule_id"] for e in result["summary"]["escalate_for_rule_tuning"]}
    assert not (set(quiet) & escalated), "未标记的规则不得升级"


# ── 7. 越界值拒绝 ──────────────────────────────────────────────────
@pytest.mark.parametrize("bad", [-0.1, 1.1, None, "0.9", float("nan")])
def test_out_of_range_probability_rejected(bad):
    assert js.verdict_from_noul(bad, 0.85, 0.30) == js.VERDICT_UNAVAILABLE


# ── 8. HTTP 错误映射 ───────────────────────────────────────────────
@pytest.mark.parametrize("code,action", [
    (400, "fatal"), (401, "fatal"), (402, "fatal"), (403, "fatal"),
    (413, "shard"), (429, "retry_after"),
    (500, "unavailable"), (502, "unavailable"), (503, "unavailable"),
    (524, "unavailable"), (529, "unavailable"),
])
def test_http_error_mapping(code, action):
    assert js.http_error_action(code) == action


def test_unknown_http_code_is_unavailable():
    assert js.http_error_action(418) == "unavailable"


# ── 9. answers 缺项 ────────────────────────────────────────────────
def test_missing_answer_is_unavailable(registry):
    """答案缺项 → UNAVAILABLE。

    注意排除 requires=delivery 的规则：那是**判定单元不匹配**，
    正确结论是「不适用」，不是服务层失败。
    """
    _, jev_rules = js.split_by_judge(registry["rules"])
    client = FakeJevClient(answers={})
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
    )
    checked = 0
    for row in result["results"]:
        if row["judge_by"] == "script":
            continue  # 脚本类不调模型，与「答案缺项」无关
        rule = next(r for r in registry["rules"] if r["rule_id"] == row["rule_id"])
        if rule.get("requires") == "delivery":
            assert row["verdict"] == js.VERDICT_NA, row["rule_id"]
            continue
        if rule.get("requires") == "repo_context":
            # 规则适用但我们没喂上下文 → 判不了，不是「不适用」（那是逃逸）
            assert row["verdict"] == js.VERDICT_INSUFFICIENT, row["rule_id"]
            continue
        assert row["verdict"] == js.VERDICT_UNAVAILABLE, row["rule_id"]
        checked += 1
    assert checked, "应当有非 delivery 类规则被检查到"


# ── 10. 判定对象一律是交付物本体 ───────────────────────────────────
def test_all_rows_judge_deliverables(registry):
    """既然不判行为，就不该再有 artifact/trace 之分。"""
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
    )
    assert not hasattr(js, "JUDGED_TRACE"), "行为检测移除后不应再有 trace 概念"
    for row in result["results"]:
        assert row["rule_target"] == "code", row["rule_id"]


DIFF_WITH_BAD_DATA = """diff --git a/src/api/client.ts b/src/api/client.ts
--- a/src/api/client.ts
+++ b/src/api/client.ts
@@ -1,3 +1,4 @@
-const a = 1
+const projectId = param.project_id ?? 'P001'
+const name = user.name ?? '未命名'
+const x: any = 1
"""

DIFF_CLEAN = """diff --git a/src/api/client.ts b/src/api/client.ts
--- a/src/api/client.ts
+++ b/src/api/client.ts
@@ -1,3 +1,4 @@
-const a = 1
+const projectId = param.project_id
+const name = user.name ?? '-'
"""


def _rule(rid, checks, suffixes=None):
    return {
        "rule_id": rid, "source": "x:1", "text": "t", "rule_target": "code",
        "judge_by": "script", "criteria_true": "a", "criteria_false": "b",
        "failure_action": "c", "script_check": checks,
    }


def test_added_lines_ignores_context_and_removed():
    """判的是「改了什么」，不能把原本就有的、或删掉的行算进来。"""
    lines = js._added_lines(DIFF_WITH_BAD_DATA)
    assert any("P001" in ln for ln in lines)
    assert not any(ln.startswith("const a = 1") for ln in lines), "删除行不得计入"


def test_added_lines_filters_by_suffix():
    lines = js._added_lines(DIFF_WITH_BAD_DATA, suffixes=[".tsx"])
    assert lines == [], "后缀不匹配时不应取到任何行"


def test_forbidden_pattern_catches_fake_data():
    r = _rule("proj.data.no-fake-data", [{
        "kind": "forbidden_pattern",
        "patterns": ["?? 'P001'", "?? '未命名'"],
        "scope": "added_lines",
    }])
    out = js.evaluate_script_rule(r, DIFF_WITH_BAD_DATA, ["src/api/client.ts"], Path("."))
    assert out["verdict"] == js.VERDICT_BAD
    assert "P001" in out["evidence"]


def test_forbidden_pattern_passes_clean_change():
    r = _rule("proj.data.no-fake-data", [{
        "kind": "forbidden_pattern", "patterns": ["?? 'P001'"], "scope": "added_lines",
    }])
    out = js.evaluate_script_rule(r, DIFF_CLEAN, ["src/api/client.ts"], Path("."))
    assert out["verdict"] == js.VERDICT_OK


def test_forbidden_regex_catches_any():
    r = _rule("proj.ts.no-any", [{
        "kind": "forbidden_regex", "regex": r"\bany\b\s*[;,)>=|]", "suffixes": [".ts", ".tsx"],
        "scope": "added_lines",
    }])
    out = js.evaluate_script_rule(r, DIFF_WITH_BAD_DATA, ["src/api/client.ts"], Path("."))
    assert out["verdict"] == js.VERDICT_BAD


def test_line_limit_reads_real_file(tmp_path):
    big = tmp_path / "Big.tsx"
    big.write_text("\n".join(f"// {i}" for i in range(320)), encoding="utf-8")
    r = _rule("proj.c7.redline", [{"kind": "line_limit", "suffixes": [".tsx"], "max": 300}])
    out = js.evaluate_script_rule(r, "", ["Big.tsx"], tmp_path)
    assert out["verdict"] == js.VERDICT_BAD
    assert "320" in out["evidence"]


def test_path_forbidden_catches_flat_component():
    r = _rule("proj.dir.no-flat-component", [{
        "kind": "path_forbidden", "regex": r"(^|/)pages/[^/]+/modules/[^/]+\.tsx$",
    }])
    out = js.evaluate_script_rule(r, "", ["src/pages/ecosystem/modules/Register.tsx"], Path("."))
    assert out["verdict"] == js.VERDICT_BAD


def test_script_rule_not_applicable_when_no_matching_files():
    """本次没碰相关文件，规则应判「不适用」，不是「符合」也不是「不符合」。"""
    r = _rule("proj.c7.redline", [{"kind": "line_limit", "suffixes": [".tsx"], "max": 300}])
    out = js.evaluate_script_rule(r, "", ["README.md"], Path("."))
    assert out["verdict"] == js.VERDICT_NA


def test_script_rule_without_config_is_unavailable():
    r = _rule("proj.unknown", [])
    out = js.evaluate_script_rule(r, "", ["a.py"], Path("."))
    assert out["verdict"] == js.VERDICT_UNAVAILABLE


def test_script_rules_run_without_calling_jev(registry):
    """脚本规则必须就地判定，不能出现在送往 Jev 的请求里，也不能再是「未覆盖」。"""
    client = FakeJevClient({})
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=registry,
        rules_to_judge=js.split_by_judge(registry["rules"])[1], dry_run=True,
        change_text=DIFF_WITH_BAD_DATA, changed_paths=["src/api/client.ts"],
    )
    js_ids = {r["rule_id"] for r in result["results"] if r["judge_by"] == "script"}
    assert js_ids, "脚本类规则必须被评估"
    sent_to_jev = set()
    for call in client.calls:
        sent_to_jev |= set(call["questions"])
    assert not (js_ids & sent_to_jev), "脚本类规则不得送 Jev"
    skipped = {s["rule_id"] for s in result["skipped_rule_ids"]}
    assert not (js_ids & skipped), "已评估的脚本规则不得再算未覆盖"


def test_all_script_rules_have_config(registry):
    for r in registry["rules"]:
        if r["judge_by"] == "script":
            assert r.get("script_check"), f"{r['rule_id']} 是脚本类却没有 script_check"


# ── 多次采样 ───────────────────────────────────────────────────────
class MultiSampleClient:
    """按序返回不同答案，模拟采样抖动。"""

    def __init__(self, seq: list[dict]):
        self.seq = seq
        self.n = 0

    def judge(self, state, questions, model):
        ans = self.seq[min(self.n, len(self.seq) - 1)]
        self.n += 1
        return {
            "answers": ans, "id": f"id{self.n}", "model": f"{model}-20260917",
            "provider": "TypeSafe",
            "usage": {"input_tokens": 10, "output_tokens": 5, "cost": 0.00002},
        }


def test_aggregate_noul_averages():
    merged = js._aggregate_answers([
        {"answers": {"q": {"type": "noul", "noul": 0.9}}},
        {"answers": {"q": {"type": "noul", "noul": 0.3}}},
        {"answers": {"q": {"type": "noul", "noul": 0.6}}},
    ])
    assert abs(merged["q"]["noul"] - 0.6) < 1e-9
    assert merged["q"]["samples"] == 3


def test_aggregate_choice_takes_majority():
    merged = js._aggregate_answers([
        {"answers": {"q": {"type": "choice", "choice": "符合", "confidence": 0.9}}},
        {"answers": {"q": {"type": "choice", "choice": "不符合", "confidence": 0.9}}},
        {"answers": {"q": {"type": "choice", "choice": "符合", "confidence": 0.7}}},
    ])
    assert merged["q"]["choice"] == "符合", "取票数最多的那个"
    assert abs(merged["q"]["confidence"] - 0.8333) < 0.01, "置信度取均值"
    assert merged["q"]["agree"] == 2 / 3


def test_multi_sample_smooths_out_one_bad_sample():
    """单次采样时，一个坏样本无法被发现；多采几次投票能把它压掉。"""
    reg = js.load_registry(RULES_PATH)
    _, jev_rules = js.split_by_judge(reg["rules"])
    rules = [r for r in jev_rules if r["rule_id"] == "soul.1.simple"]
    client = MultiSampleClient([
        {"soul.1.simple": {"type": "noul", "noul": 0.05}},   # 坏样本
        {"soul.1.simple": {"type": "noul", "noul": 0.90}},
        {"soul.1.simple": {"type": "noul", "noul": 0.92}},
    ])
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=reg,
        rules_to_judge=rules, dry_run=True, samples=3,
    )
    row = result["results"][0]
    assert row["jev_primitive"] == "noul"
    assert 0.6 < row["jev_noul"] < 0.65, "均值应落在两个好样本附近"
    assert result["summary"]["total_cost"] > 0


def test_multi_sample_records_all_response_ids(registry):
    reg = js.load_registry(RULES_PATH)
    _, jev_rules = js.split_by_judge(reg["rules"])
    rules = [r for r in jev_rules if r["rule_id"] == "soul.1.simple"]
    client = MultiSampleClient([{"soul.1.simple": {"type": "noul", "noul": 0.9}}])
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=reg,
        rules_to_judge=rules, dry_run=True, samples=3,
    )
    ids = result["results"][0]["jev_response_id"]
    assert isinstance(ids, list) and len(ids) == 3, "多次采样要把每次的 id 都留档，才可复算"


# ── 判定单元 ───────────────────────────────────────────────────────
def test_delivery_rule_on_commit_unit_is_not_applicable(registry):
    """判定单元不匹配时应判「不适用」，不是「证据不足」也不是「不符合」。

    只给一个裸 commit 时，没有任何任务文档 ——
    「有没有 TDD 记录」这类规则本来就不适用于这个单元。
    """
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.05} for r in jev_rules}
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
        delivery={"available": False, "reason": "裸 commit"},
    )
    for row in result["results"]:
        rule = next(r for r in registry["rules"] if r["rule_id"] == row["rule_id"])
        if rule.get("requires") == "delivery":
            assert row["verdict"] == js.VERDICT_NA, row["rule_id"]
            assert "判定单元" in (row["fallback_reason"] or "")


def test_repo_context_reaches_state(registry):
    """上下文由主 LLM 收集，工具只负责把它传进 state。

    实测：同一 diff 不给上下文时 soul.1 判 0.54（中性），
    给一句「仓库已有同名实现」立刻掉到 0.07。
    """
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    client = FakeJevClient(answers)
    js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
        repo_context="仓库已有 carros_utils.now_iso()，13 个脚本在用",
    )
    assert "carros_utils.now_iso" in client.calls[0]["state"]["repo_context"]


def test_missing_repo_context_is_visible(registry):
    """没给上下文时要显式说明，不能让「判不准」被读成「判过」。"""
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    client = FakeJevClient(answers)
    js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
    )
    assert "未提供" in client.calls[0]["state"]["repo_context"]


def test_classify_change_kind():
    assert js.classify_change(["README.md", "docs/a.md"]) == "docs_only"
    assert js.classify_change(["src/a.tsx", "src/b.ts"]) == "code_only"
    assert js.classify_change(["README.md", "src/a.tsx"]) == "mixed"
    assert js.classify_change([]) == "unknown"


def test_change_kind_reaches_state(registry):
    """不告诉 Jev 改的是文档还是代码，它会把「不适用」误判成「不符合」。"""
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    client = FakeJevClient(answers)
    js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
        changed_paths=["README.md", "docs/x.md"],
    )
    assert client.calls[0]["state"]["change_kind"] == "docs_only"


# ── 10b. 交付物采集 ────────────────────────────────────────────────
def test_collect_delivery_reads_facts(tmp_path):
    d = tmp_path / "task"
    d.mkdir()
    (d / "research.md").write_text(
        "# Research\n\n## 依赖树\n\n## 影响范围清单\n\n## 风险\n", encoding="utf-8"
    )
    (d / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (d / "executor.md").write_text(
        "### EV-S1\n\n- type: test\n- exit_code: 0\n\n### EV-S2\n\n- type: review\n- exit_code: 0\n",
        encoding="utf-8",
    )
    info = js.collect_delivery(d)
    assert info["available"] is True
    assert info["docs_present"]["research.md"] is True
    assert info["executor_evidence_blocks"] == 2
    assert info["executor_test_blocks"] == 1
    assert info["executor_blocks_with_exit_code"] == 2
    # 章节标题被摘出来交给 Jev 判，不靠字符串硬匹配
    assert "依赖树" in info["research_sections"]
    assert "影响范围清单" in info["research_sections"]


def test_delivery_tolerates_synonym_section_titles(tmp_path):
    """同一个意思可能写成「依赖树」也可能写成「依赖结论」，硬匹配会误判成交付缺失。"""
    d = tmp_path / "task"
    d.mkdir()
    (d / "research.md").write_text("# R\n\n## 依赖结论\n\n## 已验证事实\n", encoding="utf-8")
    (d / "plan.md").write_text("# P\n", encoding="utf-8")
    (d / "executor.md").write_text("# E\n", encoding="utf-8")
    info = js.collect_delivery(d)
    assert "依赖结论" in info["research_sections"]
    assert info["research_sections"] == ["依赖结论", "已验证事实"]


def test_collect_delivery_without_task_dir():
    info = js.collect_delivery(None)
    assert info["available"] is False
    assert info["reason"]


def test_delivery_facts_reach_the_state(registry):
    """交付物事实必须进 state，否则文档/TDD/影响范围三条规则无从判定。"""
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    client = FakeJevClient(answers)
    js.run_sweep(
        task_dir=None, out_dir=None, client=client, registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
        delivery={"available": True, "research_has_dependency_tree": True},
    )
    assert client.calls, "应当发出了请求"
    assert client.calls[0]["state"]["delivery"]["available"] is True


def test_missing_evidence_source_cannot_be_judged_violation(registry):
    """看不到的东西不能判违规。

    交付物信息不可用时（例如只给了一个裸 commit），
    doc / tdd / 影响范围 三条规则不得判「不符合」。
    """
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {
        r["rule_id"]: {
            "type": "choice", "choice": "不符合", "confidence": 1.0,
            "probabilities": {"不符合": 1.0},
        }
        for r in jev_rules
    }
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
        delivery={"available": False, "reason": "未提供任务目录"},
    )
    for row in result["results"]:
        rule = next(r for r in registry["rules"] if r["rule_id"] == row["rule_id"])
        if rule.get("requires") == "delivery":
            assert row["verdict"] != js.VERDICT_BAD, row["rule_id"]


# ── 11. 零副作用（核心回归）────────────────────────────────────────
def test_no_side_effects(tmp_path):
    task_dir = tmp_path / "tasks" / "demo"
    task_dir.mkdir(parents=True)
    (task_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (task_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    (task_dir / "research.md").write_text("# Research\n", encoding="utf-8")

    watched = ["plan.md", "executor.md", "research.md"]
    before = {n: _sha(task_dir / n) for n in watched}

    registry = js.load_registry(RULES_PATH)
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    out_dir = tmp_path / "jev_out"

    js.run_sweep(
        task_dir=task_dir, out_dir=out_dir, client=FakeJevClient(answers),
        registry=registry, rules_to_judge=jev_rules,
    )

    after = {n: _sha(task_dir / n) for n in watched}
    assert before == after, "shadow 不得修改任务目录里的任何文件"
    assert out_dir.exists(), "应当产出清单目录"


# ── 12. 清单覆盖完整 ───────────────────────────────────────────────
def test_checklist_coverage_complete(registry):
    registry = dict(registry)
    registry["rules"] = registry["rules"] + [
        {"rule_id": "proj.unrelated", "source": "README.md:1", "text": "x",
         "rule_target": "code", "judge_by": "script", "criteria_true": "a",
         "criteria_false": "b", "failure_action": "c"},
    ]
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
    )
    covered = set(result["covered_rule_ids"])
    skipped = {s["rule_id"] for s in result["skipped_rule_ids"]}
    all_ids = {r["rule_id"] for r in registry["rules"]}
    assert covered | skipped == all_ids, "覆盖集与跳过集必须等于全部规则"
    assert covered & skipped == set(), "同一条规则不能既覆盖又跳过"
    for s in result["skipped_rule_ids"]:
        assert s.get("reason"), f"{s['rule_id']} 跳过时没写理由"


# ── 13. 「拿不到答案」不得冒充判定结果（跑几天无人值守的前提）────────────
def test_unavailable_rows_are_not_written_to_cases_ledger(tmp_path):
    """UNAVAILABLE 不含关于这次改动的任何信息，写进账本就是纯噪声。

    实测：一次「没钥匙」的空转往 cases.jsonl 写了 8 行 UNAVAILABLE。
    跑几天就是几千行，会把待复核队列和一致率统计一起淹掉。
    """
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (task_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    (task_dir / "research.md").write_text("# Research\n", encoding="utf-8")

    registry = js.load_registry(RULES_PATH)
    _, jev_rules = js.split_by_judge(registry["rules"])
    out_dir = tmp_path / "jev_out"

    # 客户端一条答案都不给 —— 模拟没钥匙/余额不足
    result = js.run_sweep(
        task_dir=task_dir, out_dir=out_dir, client=FakeJevClient({}),
        registry=registry, rules_to_judge=jev_rules,
    )

    assert result["summary"]["unavailable"], "这个场景应当整批拿不到答案"

    ledger = out_dir / "cases.jsonl"
    written = [
        json.loads(ln)
        for ln in ledger.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert all(r["verdict"] != js.VERDICT_UNAVAILABLE for r in written), (
        "拿不到答案的行不得写进账本"
    )


def test_warn_when_jev_rules_all_unavailable(capsys):
    """整批拿不到答案必须喊出来。

    否则「静默什么都没做」和「一切正常」在终端里长得一模一样 ——
    这正是无人值守跑几天时最危险的失败模式。
    """
    checklist = {
        "results": [
            {"rule_id": "soul.1.simple", "judge_by": "jev", "verdict": js.VERDICT_UNAVAILABLE},
            {"rule_id": "soul.7.gain", "judge_by": "jev", "verdict": js.VERDICT_UNAVAILABLE},
        ],
        "summary": {"unavailable": ["soul.1.simple", "soul.7.gain"]},
    }
    js._warn_if_unavailable(checklist)
    out = capsys.readouterr().out
    assert "拿不到答案" in out
    assert "钥匙" in out, "整批失败时必须指向连接问题，不能让人误以为是改动有问题"


def test_warn_does_not_blame_key_on_partial_failure(capsys):
    """只有部分拿不到答案时不许提钥匙 —— 报假警会让人不再相信警告。"""
    checklist = {
        "results": [
            {"rule_id": "a", "judge_by": "jev", "verdict": js.VERDICT_UNAVAILABLE},
            {"rule_id": "b", "judge_by": "jev", "verdict": js.VERDICT_OK},
            {"rule_id": "c", "judge_by": "script", "verdict": js.VERDICT_OK},
        ],
        "summary": {"unavailable": ["a"]},
    }
    js._warn_if_unavailable(checklist)
    out = capsys.readouterr().out
    assert "拿不到答案" in out
    assert "钥匙" not in out, "部分失败不能归因于钥匙"


def test_warn_ignores_rules_that_never_reached_the_model(capsys):
    """被 requires 闸门挡下的规则不该压低告警。

    实测踩到的坑：9 条 Jev 规则里 8 条拿不到答案、1 条因缺 repo_context 走了
    证据不足分支 —— 结果「整批拿不到答案」的告警被那一条挡住了，没响。
    可那一条压根没发过请求，不该算进分母。
    """
    checklist = {
        "results": [
            {"rule_id": "a", "judge_by": "jev", "verdict": js.VERDICT_UNAVAILABLE},
            {"rule_id": "b", "judge_by": "jev", "verdict": js.VERDICT_UNAVAILABLE},
            {"rule_id": "soul.1.reuse", "judge_by": "jev",
             "verdict": js.VERDICT_INSUFFICIENT, "gated_by_requires": "repo_context"},
        ],
        "summary": {"unavailable": ["a", "b"]},
    }
    js._warn_if_unavailable(checklist)
    out = capsys.readouterr().out
    assert "钥匙" in out, "被闸门挡下的规则不得掩盖「整批连不上」"


def test_warn_is_silent_when_nothing_is_missing(capsys):
    checklist = {
        "results": [
            {"rule_id": "soul.1.simple", "judge_by": "jev", "verdict": js.VERDICT_OK},
        ],
        "summary": {"unavailable": []},
    }
    js._warn_if_unavailable(checklist)
    assert capsys.readouterr().out == "", "没缺东西就不该出声"


# ── 13. 记录完整性 ─────────────────────────────────────────────────
def test_record_completeness(registry):
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
    )
    for row in result["results"]:
        if row["judge_by"] in ("jev", "hybrid") and row["verdict"] != js.VERDICT_UNAVAILABLE:
            assert row["jev_response_id"], row["rule_id"]
            assert row["jev_model_resolved"], row["rule_id"]
            assert row["jev_usage"], row["rule_id"]


# ── 14. 版本锁定 ───────────────────────────────────────────────────
def test_model_must_be_frozen_id():
    assert js.ensure_frozen_model(js.MODEL_FROZEN) == js.MODEL_FROZEN
    for alias in ("~typesafe/jev-latest", "typesafe/jev-latest", ""):
        with pytest.raises(ValueError):
            js.ensure_frozen_model(alias)


# ── 15. 密钥不落盘 ─────────────────────────────────────────────────
def test_no_key_leak_guard():
    with pytest.raises(ValueError):
        js.assert_no_secret("Authorization: Bearer sk-or-v1-deadbeef")
    js.assert_no_secret("Authorization: Bearer <redacted>")  # 不抛


def test_run_sweep_output_contains_no_key(registry):
    _, jev_rules = js.split_by_judge(registry["rules"])
    answers = {r["rule_id"]: {"type": "noul", "noul": 0.95} for r in jev_rules}
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=registry,
        rules_to_judge=jev_rules, dry_run=True,
    )
    js.assert_no_secret(json.dumps(result, ensure_ascii=False))


# ── 上下文闸门（P0）：缺输入必须说「判不了」，不许逃逸也不许放水 ──────
def test_missing_repo_context_is_insufficient_not_na():
    """缺上下文时判「证据不足」，不是「不适用」。

    「不适用」是逃逸（假装规则不管这事），「符合」是放水。
    规则适用、但缺了事实判不准 —— 只能老实说判不了。
    实测依据：同一提交弱上下文 0.18（误报）vs 强上下文 0.82（正确）。
    """
    reg = js.load_registry(RULES_PATH)
    rule = next(r for r in reg["rules"] if r["rule_id"] == "soul.1.reuse")
    assert rule.get("requires") == "repo_context"

    answers = {"soul.1.reuse": {"type": "noul", "noul": 0.95}}
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=reg,
        rules_to_judge=[rule], dry_run=True, repo_context="",
    )
    row = result["results"][0]
    assert row["verdict"] == js.VERDICT_INSUFFICIENT, "缺上下文不得给结论"
    assert "不给结论" in (row["fallback_reason"] or "")
    assert "repo_context" in (row["fallback_reason"] or "")
    assert "soul.1.reuse" in result["summary"]["blocked_by_missing_context"]


def test_with_repo_context_the_rule_actually_fires():
    """给了上下文，规则必须真的判 —— 修之前它永远被吞成「不适用」。"""
    reg = js.load_registry(RULES_PATH)
    rule = next(r for r in reg["rules"] if r["rule_id"] == "soul.1.reuse")
    answers = {"soul.1.reuse": {"type": "noul", "noul": 0.95}}
    result = js.run_sweep(
        task_dir=None, out_dir=None, client=FakeJevClient(answers), registry=reg,
        rules_to_judge=[rule], dry_run=True,
        repo_context="仓库已有 carros_utils.now_iso()，13 个脚本在用",
    )
    assert result["results"][0]["verdict"] == js.VERDICT_OK
    assert result["summary"]["blocked_by_missing_context"] == []


def test_requires_available_distinguishes_two_kinds():
    f = js._requires_available
    assert f("delivery", {"available": True}, False) is True
    assert f("delivery", {"available": False}, True) is False
    assert f("repo_context", {"available": False}, True) is True
    assert f("repo_context", {"available": True}, False) is False
