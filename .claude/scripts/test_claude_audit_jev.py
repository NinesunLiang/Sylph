"""claude_audit_jev.py 的依赖 TDD —— 存量资源体检。

体检的价值全在「判读对不对」上：判读错了，Jev 答得再确定也是错的。
所以这里把判读合并、事实组装、动作建议三条路径测死。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import claude_audit_jev as ca  # noqa: E402
import jev_sweep as js  # noqa: E402


# ── 判读合并 ───────────────────────────────────────────────────────
def test_merged_rules_overrides_criteria_but_keeps_source_of_truth():
    """覆盖型条目只改判读；哲学原文必须仍来自主表，不能有两份。"""
    main = {r["rule_id"]: r for r in js.load_registry(ca.MAIN_RULES)["rules"]}
    overrides = [r for r in ca.merged_rules() if r["rule_id"] in main]
    assert overrides, "应当有覆盖型条目"

    for r in overrides:
        rid = r["rule_id"]
        assert r["text"] == main[rid]["text"], f"{rid} 的规则原文被改写了，应只覆盖判读"
        assert r["source"] == main[rid]["source"], f"{rid} 的来源被改写了"


def test_every_rule_is_grounded_in_some_carroros_rule():
    """每条体检规则都得有出处：要么主表本来就有，要么写明派生自哪条。

    「凭空发明规则」是这个设计最容易走偏的地方 —— Jev 判得再对，
    规则没有 CarrorOS 出处就没有治理意义。
    """
    main = {r["rule_id"]: r for r in js.load_registry(ca.MAIN_RULES)["rules"]}
    for r in ca.merged_rules():
        rid = r["rule_id"]
        if rid in main:
            continue
        derives = r.get("derived_from_rule")
        assert derives, f"{rid} 不在主表又没标 derived_from_rule"
        assert derives in main, f"{rid} 声称派生自 {derives}，但主表没有这条"


def test_merged_rules_covers_the_five_asked_checks():
    """人类点名要的 5 条：最简 / 复用 / 增益 / 过时 / 无价值。"""
    ids = {r["rule_id"] for r in ca.merged_rules()}
    assert ids == {
        "soul.1.simple", "soul.1.reuse", "soul.7.gain",
        "soul.7.stale", "soul.7.worthless",
    }, f"体检规则集与人类要求不符: {sorted(ids)}"


def test_derived_rule_without_derives_from_is_rejected(tmp_path, monkeypatch):
    """主表没有、又没写出处的规则条目，必须当场拒绝。"""
    bogus = tmp_path / "audit.yaml"
    bogus.write_text(
        "schema_version: x\nregistry_version: t\nrules:\n"
        "  - rule_id: invented.rule\n    criteria_true: a\n    criteria_false: b\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ca, "AUDIT_RULES", bogus)
    with pytest.raises(SystemExit) as exc:
        ca.merged_rules()
    assert "凭空发明" in str(exc.value)


def test_derived_rule_must_point_at_a_real_carroros_rule(tmp_path, monkeypatch):
    """derives_from 指向不存在的规则，也要拒绝。"""
    bogus = tmp_path / "audit.yaml"
    bogus.write_text(
        "schema_version: x\nregistry_version: t\nrules:\n"
        "  - rule_id: invented.rule\n    derives_from: no.such.rule\n"
        "    criteria_true: a\n    criteria_false: b\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ca, "AUDIT_RULES", bogus)
    with pytest.raises(SystemExit) as exc:
        ca.merged_rules()
    assert "不存在" in str(exc.value)


def test_merged_rules_use_audit_wording_not_change_wording():
    """体检判读不得再用「本次改动」的说法 —— 那是判 commit 的语言。

    实测教训：soul.7.gain 的判据原文就写着「本次改动是在消除冗余」，
    直接拿去判存量文件等于问 Jev 一个不存在的改动。
    """
    rules = ca.merged_rules()
    for r in rules:
        blob = r["criteria_true"] + r["criteria_false"]
        assert "本次改动" not in blob, f"{r['rule_id']} 的体检判读还在说「本次改动」"


def test_override_rules_keep_thresholds_from_main():
    """覆盖型条目沿用主表阈值 —— 体检不该偷偷换一套阈值。"""
    main = {r["rule_id"]: r for r in js.load_registry(ca.MAIN_RULES)["rules"]}
    for r in ca.merged_rules():
        rid = r["rule_id"]
        if rid not in main:
            continue
        assert r.get("accept_at") == main[rid].get("accept_at")
        assert r.get("reject_at") == main[rid].get("reject_at")


def test_derived_rules_declare_their_own_thresholds():
    """派生规则必须自带阈值 —— 主表没有它，别的地方给不了。"""
    main = {r["rule_id"]: r for r in js.load_registry(ca.MAIN_RULES)["rules"]}
    for r in ca.merged_rules():
        if r["rule_id"] in main:
            continue
        assert isinstance(r.get("accept_at"), (int, float)), f"{r['rule_id']} 缺 accept_at"
        assert isinstance(r.get("reject_at"), (int, float)), f"{r['rule_id']} 缺 reject_at"
        assert r["reject_at"] < r["accept_at"], f"{r['rule_id']} 阈值反了"


def test_merged_rules_raises_when_nothing_matches(tmp_path, monkeypatch):
    """体检表 rule_id 全对不上时必须炸，不能静默判 0 条。"""
    bogus = tmp_path / "audit.yaml"
    bogus.write_text(
        "schema_version: x\nregistry_version: t\nrules:\n"
        "  - rule_id: no.such.rule\n    criteria_true: a\n    criteria_false: b\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ca, "AUDIT_RULES", bogus)
    with pytest.raises(SystemExit):
        ca.merged_rules()


def test_audit_registry_is_valid_per_sweep_rules():
    """体检表本身要过主校验器 —— 免得写出个格式不对的表还去跑。"""
    audit = js.load_registry(ca.AUDIT_RULES)
    assert audit.get("scope") == "repo_audit"
    assert audit.get("registry_version")


# ── 事实组装 ───────────────────────────────────────────────────────
def test_build_facts_includes_caller_list():
    """调用方清单是 soul.7.gain 唯一的判据来源，不能漏。"""
    facts = ca.build_facts({
        "path": ".claude/scripts/x.py", "bytes": 123,
        "last_commit": "2026-01-02T03:04:05+00:00",
        "callers": [".claude/scripts/a.py", ".claude/scripts/b.py"],
    })
    assert ".claude/scripts/a.py" in facts
    assert ".claude/scripts/b.py" in facts
    assert "调用方数量: 2" in facts


def test_dead_refs_finds_nonexistent_repo_paths(tmp_path, monkeypatch):
    """「过时」这条判据不能是空话 —— 依赖存不存在必须实际查过再喂给 Jev。"""
    (tmp_path / ".claude" / "scripts").mkdir(parents=True)
    (tmp_path / ".claude" / "scripts" / "alive.py").write_text("x", encoding="utf-8")
    (tmp_path / "x.py").write_text(
        "# 引用了 .claude/scripts/gone.py —— 这个不存在\n"
        "# 也引用了 .claude/scripts/alive.py —— 这个在\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ca, "ROOT", tmp_path)
    dead = ca._dead_refs("x.py")
    assert ".claude/scripts/gone.py" in dead
    assert ".claude/scripts/alive.py" not in dead, "存在的路径不能算失效"


def test_registration_names_the_owning_unit():
    """归属必须说清楚，不能只说「某个祖先目录被提到过」。

    实测踩过：早期版本按「祖先路径子串」匹配，结果 `.claude/index.md` 里的
    `.claude/workflows/` 让每个工作流文件都显示「已登记」—— 那等于没有信号。
    """
    facts = ca._registration(
        ".claude/workflows/frontend-overnight/scripts/ui_autopilot/token_bootstrap.py")
    assert "frontend-overnight" in facts
    assert "workflow" in facts


def test_registration_reports_unowned_scripts_honestly():
    """不属于任何已登记单元的文件，必须直说，不能含糊。"""
    facts = ca._registration(".claude/scripts/run-regression.sh")
    assert "不属于任何已登记" in facts


def test_build_facts_reports_dead_refs_explicitly():
    """即使一条失效引用都没有，也要显式说「查过了，没有」，不能留空。"""
    facts = ca.build_facts({
        "path": ".claude/scripts/jev_sweep.py", "bytes": 1,
        "last_commit": "?", "callers": [],
    })
    assert "失效引用" in facts
    assert "都还在" in facts or "不存在" in facts


def test_build_facts_says_so_when_nothing_calls_it():
    """0 调用方必须显式说出来，不能留空 —— 留空 Jev 会以为自己没看到而已。"""
    facts = ca.build_facts({
        "path": ".claude/scripts/dead.py", "bytes": 10,
        "last_commit": "?", "callers": [],
    })
    assert "没有任何文件" in facts
    assert "调用方数量: 0" in facts


# ── 动作建议 ───────────────────────────────────────────────────────
def _row(**verdicts):
    return {"path": "x", "callers": [], "error": None,
            "verdicts": {k: {"verdict": v} for k, v in verdicts.items()}}


def test_suggest_delete_on_any_violation():
    s = ca.suggest(_row(**{"soul.1.reuse": js.VERDICT_BAD, "soul.7.gain": js.VERDICT_OK}))
    assert "删除" in s


def test_suggest_review_on_undecided():
    """拿不准时不能直接说删 —— 要说「规则可能有问题，人来看」。"""
    s = ca.suggest(_row(**{"soul.7.gain": js.VERDICT_UNDECIDED}))
    assert "复核" in s
    assert "删除" not in s


def test_suggest_keep_only_when_all_clear():
    s = ca.suggest(_row(**{"soul.1.simple": js.VERDICT_OK,
                           "soul.1.reuse": js.VERDICT_OK,
                           "soul.7.gain": js.VERDICT_OK}))
    assert s == "保留"


def test_suggest_defers_when_no_verdicts():
    """一条结论都没有（比如没钥匙）不能说「保留」—— 那是把「没看」报成「没问题」。"""
    s = ca.suggest({"path": "x", "callers": [], "error": "missing_key", "verdicts": {}})
    assert "保留" not in s


# ── 候选收集 ───────────────────────────────────────────────────────
def test_collect_candidates_finds_full_mechanism_set():
    cands, stats = ca.collect_candidates(suspects_only=False)
    assert stats["mech_total"] > 0
    assert stats["test_total"] > 0
    assert len(cands) == stats["mech_total"]
    assert stats["suspects"] >= 1
    assert stats["unwired"] >= 1, "这个仓库已知存在 0 接线文件"


def test_collect_candidates_can_limit_to_suspects():
    cands, stats = ca.collect_candidates(suspects_only=True)
    assert len(cands) == stats["suspects"]
    assert all(len(c["callers"]) <= 1 for c in cands)


def test_collect_candidates_excludes_requested_boundaries():
    cands, _ = ca.collect_candidates(suspects_only=False)
    for c in cands:
        path = c["path"]
        assert path.endswith((".py", ".sh")), f"{path} 不是机制文件"
        assert "/workflows/" not in path
        assert "/worktrees/" not in path
        assert not Path(path).name.startswith("settings")
        assert not Path(path).name.startswith("test_")


def test_scope_includes_archived_mechanisms_but_excludes_settings():
    assert ca._in_audit_scope(".claude/scripts/archived/fallback_matrix.py")
    assert not ca._in_audit_scope(".claude/workflows/frontend-overnight/runner.py")
    assert not ca._in_audit_scope(".claude/worktrees/task-isolated-demo/runner.py")
    assert not ca._in_audit_scope(".claude/settings.local.json")
    assert not ca._in_audit_scope(".claude/settings.permissions.json")


def test_settings_are_evidence_for_registered_hooks():
    facts = ca._registration(".claude/hooks/pretool-gate.py")
    assert "settings.json" in facts
    assert "间接注册" in facts


def test_archived_skill_is_not_reported_as_active_owner():
    facts = ca._registration(
        ".claude/skills/archived/lx-oracle-legacy/runtime_oracle_agent.py")
    assert "已登记的工作流/技能" in facts


def test_evidence_scope_keeps_settings_but_excludes_runtime_boundaries():
    assert ca._in_evidence_scope(".claude/settings.json")
    assert ca._in_evidence_scope(".claude/hooks/pretool-gate.py")
    assert not ca._in_evidence_scope(".claude/workflows/frontend-overnight/runner.py")
    assert not ca._in_evidence_scope(".claude/worktrees/task-isolated-demo/runner.py")


def test_dry_run_does_not_load_rules(monkeypatch):
    monkeypatch.setattr(ca, "merged_rules", lambda: (_ for _ in ()).throw(
        AssertionError("dry-run must not load Jev rules")))
    assert ca.main(["--dry-run"]) == 0
