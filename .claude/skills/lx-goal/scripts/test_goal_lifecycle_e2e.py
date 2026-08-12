"""Goal lifecycle end-to-end fixture (P0-1).

Chains the real gates and state machine through the full lifecycle in a
hermetic tmp environment: plan -> token -> handoff -> task-done -> report ->
done -> off, plus a resume check. Eliminates the `goal.e2e.missing` blocker
reported across Benchmarking index6-10.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py"
spec = importlib.util.spec_from_file_location("lx_goal_e2e", GOAL)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def _valid_research(path: Path) -> None:
    path.write_text(
        "# Research\n\n"
        "## 背景\n真实背景。\n\n"
        "## 约束\n本地约束。\n\n"
        "## 已知信息\n已知事实。\n\n"
        "## 不确定性\n待验证边界。\n\n"
        "## 全貌\n完整调用链。\n\n"
        "## 依赖树\n- research → plan\n\n"
        "## 方案\n最小修复方案。\n\n"
        "## Dependency TDD\ncommand: pytest; exit_code: 0\n",
        encoding="utf-8",
    )


def _valid_plan(path: Path) -> None:
    path.write_text(
        "# Plan\n\n"
        "## Gate\n- level: L2\n\n"
        "## Phase 1\n"
        "- [x] S1: lifecycle e2e step\n"
        "  - status: completed\n"
        "  - depends_on: none\n"
        "  - scope: lifecycle files\n"
        "  - acceptance: phase order is enforced\n"
        "  - verify: command:pytest\n",
        encoding="utf-8",
    )


def _valid_executor(path: Path) -> None:
    path.write_text(
        "# Executor\n\n"
        "## Conditions\n- tmp hermetic env\n\n"
        "## Key Changes\n- lifecycle chain\n\n"
        "## Decisions\n- Rationale: e2e fixture\n\n"
        "## Acceptance Checklist\n- [x] chain completes\n\n"
        "## TDD Evidence\n- Dependency TDD command: pytest -> exit 0\n"
        "- Regression TDD command: pytest -> exit 0\n\n"
        "### EV-S1\n- step: S1\n- type: test\n- evidence_level: E3\n- source: e2e\n- exit_code: 0\n- assertion: done\n",
        encoding="utf-8",
    )


@pytest.fixture
def goal_ctx(tmp_path, monkeypatch):
    date = "20260812"
    plan_dir = tmp_path / "tasks" / date / "e2e-task"
    plan_dir.mkdir(parents=True)
    _valid_research(plan_dir / "research.md")
    _valid_plan(plan_dir / "plan.md")
    _valid_executor(plan_dir / "executor.md")

    tokens = tmp_path / "tokens"
    token_path = tokens / date / "e2e-task.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps({
            "schema_version": "v1.0",
            "revision": 0,
            "mode": "goal",
            "session": {"id": "e2e-task", "level": "L2"},
            "task_dir": str(plan_dir.resolve()),
            "status": "active",
            "goal": {"state": "CLARIFY", "description": "e2e chain"},
            "stats": {"done": 0, "total": 1},
            "task": {"current_step": None, "status": "planning"},
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "TOKENS_DIR", tokens)
    monkeypatch.setattr(module, "TASKS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(module, "PLANS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(module, "CURRENT_PLAN_DIR", plan_dir.resolve())

    ctx = {"plan_dir": plan_dir, "token_path": token_path, "tokens": tokens}
    return ctx


def _state(token_path):
    return json.loads(token_path.read_text(encoding="utf-8"))["goal"]["state"]


def test_goal_lifecycle_plan_to_done_chain(goal_ctx):
    plan_dir = goal_ctx["plan_dir"]
    token_path = goal_ctx["token_path"]

    # Phase 0: research validated -> PLANNING
    module.cmd_phase0_done()
    assert _state(token_path) == "PLANNING"

    # Plan: validated -> EXECUTING
    module.cmd_plan_done()
    assert _state(token_path) == "EXECUTING"

    # task-done: records completion + reconciles canonical stats
    module.cmd_task_done("E2E 步骤完成")
    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["stats"]["done"] == 1
    assert token["stats"]["total"] == 1

    # report: VERIFIED path (all steps [x] + evidence)
    module.cmd_report(plan_dir)
    report = (plan_dir / "state" / "goal-report.md").read_text(encoding="utf-8")
    assert "VERIFIED: 所有计划步骤已完成" in report

    # done: EXECUTING -> VERIFYING -> ARCHIVING -> ARCHIVED, lock removed
    module.cmd_done(plan_dir)
    assert _state(token_path) == "ARCHIVED"
    assert json.loads(token_path.read_text(encoding="utf-8"))["status"] == "archived"
    assert not token_path.with_suffix(token_path.suffix + ".lock").exists()


def test_goal_lifecycle_writes_durable_handoffs(goal_ctx):
    plan_dir = goal_ctx["plan_dir"]
    module.cmd_phase0_done()
    module.cmd_plan_done()
    module.cmd_task_done("步骤完成")
    module.cmd_done(plan_dir)

    state_dir = plan_dir / "state"
    # EXECUTING and VERIFYING are resumable phases with durable handoffs.
    # ARCHIVING is a terminal transition straight to ARCHIVED and needs no
    # resumable handoff.
    for phase in ("EXECUTING", "VERIFYING"):
        handoff = state_dir / f"phase-handoff-{phase}.json"
        assert handoff.exists(), f"missing phase-handoff-{phase}.json"
        assert json.loads(handoff.read_text(encoding="utf-8"))["status"] == "ready"


def test_goal_lifecycle_off_completes_and_removes_lock(goal_ctx):
    plan_dir = goal_ctx["plan_dir"]
    token_path = goal_ctx["token_path"]
    # Advance to VERIFYING so off is allowed.
    module.cmd_phase0_done()
    module.cmd_plan_done()
    module.cmd_task_done("步骤完成")
    module.cmd_done(plan_dir)
    assert _state(token_path) == "ARCHIVED"

    # off on an already-archived task finalizes without error.
    module.cmd_off(plan_dir)
    assert not token_path.with_suffix(token_path.suffix + ".lock").exists()


def test_goal_lifecycle_token_is_resume_source(goal_ctx):
    """After the chain, the canonical token + handoffs must be the recovery source."""
    plan_dir = goal_ctx["plan_dir"]
    module.cmd_phase0_done()
    module.cmd_plan_done()
    module.cmd_task_done("步骤完成")
    module.cmd_done(plan_dir)

    # A fresh context can recover from the token via task_dir binding.
    assert module._goal_state(plan_dir) == "ARCHIVED"
    assert (plan_dir / "state" / "phase-handoff-VERIFYING.json").exists()
