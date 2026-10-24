"""下一步入参契约：每步完成后主动告知下一步要准备什么。

人类要求（2026-10-24）："每个 step 事前强调流程，代替事后报错；
每步前都告诉 AI，下一步的入参是什么，要提前准备好，整个过程流畅。"

因此每个生命周期命令结束时必须打印下一命令的入参清单，
而不是等 AI 撞到门禁才报错。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("lx_goal_next", SKILL_DIR / "lx-goal.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("lx_goal_next", mod)
    spec.loader.exec_module(mod)
    return mod


def _out(capsys) -> str:
    return capsys.readouterr().out


def test_after_on_points_to_research_not_task_done(capsys):
    """激活后必须先做 research；不能提前让 AI 去 task-done。"""
    mod = _load()
    mod._print_next_contract("after-on", "L1")
    out = _out(capsys)
    assert "下一步：phase0-done" in out
    assert "research.md" in out
    for section in ("背景", "约束", "已知信息", "不确定性", "全貌", "依赖树", "方案", "Dependency TDD"):
        assert section in out, section
    assert "task-done" not in out


def test_after_phase0_l2_spells_out_tdd_commands(capsys):
    mod = _load()
    mod._print_next_contract("after-phase0", "L2")
    out = _out(capsys)
    assert "下一步：plan-done" in out
    assert "dep_tdd_cmd" in out and "feature_tdd_cmd" in out
    assert "exit 0" in out and "非 0" in out
    assert "worktree" in out


def test_after_phase0_l1_omits_l2_extras(capsys):
    mod = _load()
    mod._print_next_contract("after-phase0", "L1")
    out = _out(capsys)
    assert "dep_tdd_cmd" not in out
    assert "worktree" not in out


def test_after_plan_names_evidence_inputs(capsys):
    mod = _load()
    mod._print_next_contract("after-plan", "L2")
    out = _out(capsys)
    assert "下一步：task-done" in out
    assert "EV-<step_id>" in out
    assert "assertion" in out


def test_after_task_continues_while_steps_remain(capsys, tmp_path):
    mod = _load()
    (tmp_path / "plan.md").write_text(
        "## Phase 1\n- [x] S1: done\n- [ ] S2: pending\n", encoding="utf-8"
    )
    mod._print_next_contract("after-task", "L1", tmp_path)
    out = _out(capsys)
    assert "继续 task-done" in out
    assert "1/2" in out


def test_after_task_hands_off_to_closeout_when_all_done(capsys, tmp_path):
    mod = _load()
    (tmp_path / "plan.md").write_text("## Phase 1\n- [x] S1: done\n", encoding="utf-8")
    mod._print_next_contract("after-task", "L2", tmp_path)
    out = _out(capsys)
    assert "收尾三连" in out
    assert "report" in out and "accept" in out and "done" in out
    assert "Acceptance Checklist" in out


def test_after_report_requires_checklist_and_verdict(capsys):
    mod = _load()
    mod._print_next_contract("after-report", "L2")
    out = _out(capsys)
    assert "accept" in out and "done" in out
    assert "Acceptance Checklist" in out
    assert "**status**" in out and "**confidence**" in out


def test_after_accept_points_to_done(capsys):
    mod = _load()
    mod._print_next_contract("after-accept", "L2")
    out = _out(capsys)
    assert "下一步：done" in out
    assert "checklist" in out
