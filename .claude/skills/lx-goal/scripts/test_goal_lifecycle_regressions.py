import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py"
CONTRACTS = ROOT / ".claude/scripts/goal_contracts.py"
spec = importlib.util.spec_from_file_location("lx_goal_under_test", GOAL)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
contract_spec = importlib.util.spec_from_file_location("goal_contracts_under_test", CONTRACTS)
assert contract_spec is not None
contracts = importlib.util.module_from_spec(contract_spec)
assert contract_spec.loader is not None
contract_spec.loader.exec_module(contracts)
state_spec = importlib.util.spec_from_file_location(
    "goal_state_machine_under_test", ROOT / ".claude/scripts/goal_state_machine.py"
)
assert state_spec is not None and state_spec.loader is not None
state_machine = importlib.util.module_from_spec(state_spec)
state_spec.loader.exec_module(state_machine)


def test_goal_context_requires_explicit_task_dir(monkeypatch):
    monkeypatch.setattr(module, "CURRENT_PLAN_DIR", None)
    monkeypatch.delenv("CARROROS_TASK_DIR", raising=False)

    with pytest.raises(SystemExit):
        module._resolve_plan_dir()


def test_task_dir_cli_binding_selects_explicit_context(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    for name in ("plan.md", "research.md", "executor.md"):
        (plan_dir / name).write_text("# fixture\n", encoding="utf-8")
    monkeypatch.setattr(module, "CURRENT_PLAN_DIR", None)

    remaining = module._bind_task_dir_arg(["--task-dir", str(plan_dir), "report"])

    assert remaining == ["report"]
    assert module.CURRENT_PLAN_DIR == plan_dir.resolve()


def test_goal_step_verification_binds_token_context():
    text = GOAL.read_text(encoding="utf-8")
    assert 'env["CARROROS_TOKEN_PATH"]' in text
    assert 'env["CARROROS_TASK_ID"]' in text
    assert 'env["CARROROS_TASK_DIR"]' in text


def test_goal_context_fixture_is_hermetic(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "task"
    plan_dir.mkdir(parents=True)
    tokens = tmp_path / "tokens" / "20260811"
    tokens.mkdir(parents=True)
    token_path = tokens / "task.json"
    token_path.write_text(
        '{"session": {"id": "task"}, "task_dir": "' + str(plan_dir) + '"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")

    resolved, env = module._goal_context(plan_dir)

    assert resolved == token_path
    assert env["CARROROS_TASK_ID"] == "task"
    assert env["CARROROS_TASK_DIR"] == str(plan_dir.resolve())


def test_goal_context_missing_token_is_explicit(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")

    try:
        module._goal_context(plan_dir)
    except RuntimeError as exc:
        assert "goal token missing" in str(exc)
    else:
        raise AssertionError("missing goal token must fail closed")


def test_placeholder_contract_rejects_template_values():
    for value in ("TODO", "TBD", "待填写", "<pending-user-confirmation>", "..."):
        assert contracts.is_placeholder(value)


def test_placeholder_contract_does_not_match_embedded_marker_text():
    text = "runtime path segment n/audit is documented in the map"
    assert not contracts.is_placeholder(text)


def test_plan_builder_emits_acceptance_fields():
    plan = ROOT / ".omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/plan.md"
    text = plan.read_text(encoding="utf-8")
    assert "acceptance:" in text
    assert "scope:" in text
    assert "verify:" in text


def test_research_dependency_tree_requires_bullet():
    research = ROOT / ".omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/research.md"
    text = research.read_text(encoding="utf-8")
    section = text.split("## 依赖树", 1)[1].split("## 方案", 1)[0]
    assert any(line.startswith("-") for line in section.splitlines())


def test_default_goal_slug_is_unique_across_activations():
    first = module._goal_slug("same concurrent evaluation goal")
    second = module._goal_slug("same concurrent evaluation goal")

    assert first != second
    assert len(first) <= 64
    assert first.startswith("same-concurrent-evaluation-goal")
    assert second.startswith("same-concurrent-evaluation-goal")


def test_report_empty_plan_is_not_verified(monkeypatch, tmp_path):
    state_dir = tmp_path / "state"
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("# Plan\n\n## Gate\n- level: L2\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    mode_data = {"goal": {"description": "empty plan"}, "task_dir": str(plan_dir), "completed_tasks": []}

    monkeypatch.setattr(module, "STATE_DIR", state_dir)
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, str(plan_dir or plan_dir)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    module.cmd_report(plan_dir)

    report = (plan_dir / "state" / "goal-report.md").read_text(encoding="utf-8")
    assert "VERIFIED: 所有计划步骤已完成" not in report
    assert "IN_PROGRESS" in report or "BLOCKED" in report


def test_report_uses_plan_count_and_requires_ev_evidence(monkeypatch, tmp_path):
    state_dir = tmp_path / "state"
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [x] S1: forged\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    mode_data = {"goal": {"description": "forged checkbox"}, "task_dir": str(plan_dir), "completed_tasks": []}

    monkeypatch.setattr(module, "STATE_DIR", state_dir)
    monkeypatch.setattr(module, "_read_mode_file", lambda selected=None: (mode_data, str(selected or plan_dir)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    module.cmd_report(plan_dir)

    report = (plan_dir / "state" / "goal-report.md").read_text(encoding="utf-8")
    assert "已完成任务数: 1" in report
    assert "verified_evidence_missing" in report
    assert "VERIFIED: 所有计划步骤已完成" not in report


def test_report_missing_plan_dir_is_blocked(monkeypatch, tmp_path):
    mode_data = {"goal": {"description": "broken"}}
    monkeypatch.setattr(module, "_read_mode_file", lambda selected=None: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: None)

    with pytest.raises(SystemExit) as exc:
        module.cmd_report(tmp_path / "missing")

    assert exc.value.code == 2


def test_task_done_syncs_canonical_token_stats(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    token_dir = tmp_path / "tokens" / tmp_path.name
    token_dir.mkdir(parents=True)
    token_path = token_dir / f"{plan_dir.name}.json"
    token_path.write_text(json.dumps({"task_dir": str(plan_dir), "stats": {"done": 0, "total": 1}, "task": {"current_step": "S1"}}), encoding="utf-8")
    mode_data = {"completed_tasks": [], "rpe_plan_dir": str(plan_dir)}
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "_resolve_current_step", lambda path: None)
    monkeypatch.setattr(module, "_write_mode_file", lambda data, path: None)
    monkeypatch.setattr(module, "_ledger_append_block", lambda *args: None)
    monkeypatch.setattr(module, "_update_lock_counter", lambda *args: None)

    assert module.cmd_task_done("sync stats") == 0
    token = json.loads(token_path.read_text())
    assert token["stats"]["done"] == 1
    assert token["task"]["status"] == "completed"


def test_done_transitions_through_verifying(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text(
        "## Conditions\nfocused tests\n\n"
        "## Key Changes\ncanonical handoff\n\n"
        "## Decisions\nnone: bounded scope\n\n"
        "## Acceptance Checklist\n- [x] tests pass\n\n"
        "## TDD Evidence\ndependency TDD exit 0; regression TDD exit 0\n\n"
        "### EV-S1\n- step: S1\n- type: test\n- evidence_level: E3\n- source: test\n- exit_code: 0\n- assertion: done\n",
        encoding="utf-8",
    )
    module._start_phase(plan_dir, "EXECUTING")
    token_dir = tmp_path / "tokens" / tmp_path.name
    token_dir.mkdir(parents=True)
    token_path = token_dir / f"{plan_dir.name}.json"
    token_path.write_text(json.dumps({"mode": "goal", "task_dir": str(plan_dir), "stats": {"done": 1, "total": 1}, "goal": {"state": "EXECUTING"}}), encoding="utf-8")
    transitions = []
    class FakeGsm:
        def __init__(self, path): pass
        def transition(self, state, **kwargs): transitions.append(state)
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: ({"rpe_plan_dir": str(plan_dir)}, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "_verify_executor_checklist", lambda path: None)
    monkeypatch.setattr(module, "_GSM", FakeGsm)
    monkeypatch.setattr(module, "finalize_token", lambda *args, **kwargs: None)

    module.cmd_done(plan_dir)
    assert transitions == ["VERIFYING", "ARCHIVING", "ARCHIVED"]


def test_done_from_canonical_plan_reconciles_stats_and_completes_handoffs(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text(
        "## Conditions\nfocused tests\n\n"
        "## Key Changes\ncanonical handoff\n\n"
        "## Decisions\nnone: bounded scope\n\n"
        "## Acceptance Checklist\n- [x] tests pass\n\n"
        "## TDD Evidence\ndependency TDD exit 0; regression TDD exit 0\n\n"
        "### EV-S1\n- step: S1\n- type: test\n- evidence_level: E3\n- source: test\n- exit_code: 0\n- assertion: done\n",
        encoding="utf-8",
    )
    token_dir = tmp_path / "tokens" / tmp_path.name
    token_dir.mkdir(parents=True)
    token_path = token_dir / f"{plan_dir.name}.json"
    token_path.write_text(json.dumps({
        "mode": "goal",
        "task_dir": str(plan_dir),
        "stats": {"done": 0, "total": 1},
        "task": {"current_step": "S1"},
        "goal": {"state": "EXECUTING"},
        "revision": 0,
    }), encoding="utf-8")
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")

    module.cmd_done(plan_dir)

    token = json.loads(token_path.read_text())
    assert token["status"] == "archived"
    assert token["stats"]["done"] == 1
    assert token["stats"]["total"] == 1
    exec_handoff = json.loads((plan_dir / "state" / "phase-handoff-EXECUTING.json").read_text())
    assert exec_handoff["status"] == "ready"
    verify_handoff = json.loads((plan_dir / "state" / "phase-handoff-VERIFYING.json").read_text())
    assert verify_handoff["status"] == "ready"
    assert not token_path.with_suffix(token_path.suffix + ".lock").exists()


def test_done_rejects_incomplete_plan_without_archiving(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [ ] S1: pending\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text(
        "## Conditions\nfocused tests\n\n"
        "## Key Changes\nchange\n\n"
        "## Decisions\nnone: scope\n\n"
        "## Acceptance Checklist\n- [x] tests\n\n"
        "## TDD Evidence\ndependency TDD exit 0; regression TDD exit 0\n\n"
        "### EV-S1\n- exit_code: 0\n- assertion: passed\n",
        encoding="utf-8",
    )
    token_dir = tmp_path / "tokens" / tmp_path.name
    token_dir.mkdir(parents=True)
    token_path = token_dir / f"{plan_dir.name}.json"
    token_path.write_text(json.dumps({
        "mode": "goal",
        "task_dir": str(plan_dir),
        "stats": {"done": 0, "total": 1},
        "task": {"current_step": "S1"},
        "goal": {"state": "EXECUTING"},
        "revision": 0,
    }), encoding="utf-8")
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")

    with pytest.raises(SystemExit) as exc:
        module.cmd_done(plan_dir)

    assert exc.value.code == 1
    token = json.loads(token_path.read_text())
    assert token.get("status") != "archived"
    assert token.get("terminal_at") is None
    assert token["goal"]["state"] == "EXECUTING"


def test_update_lock_counter_ignores_list_fields(tmp_path, monkeypatch):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    token_dir = tmp_path / "tokens"
    (token_dir / tmp_path.name).mkdir(parents=True)
    token_path = token_dir / tmp_path.name / f"{plan_dir.name}.json"
    token_path.write_text(json.dumps({"completed_tasks": []}), encoding="utf-8")
    monkeypatch.setattr(module, "TOKENS_DIR", token_dir)

    module._update_lock_counter(plan_dir, "completed_tasks")

    assert json.loads(token_path.read_text())["completed_tasks"] == []


def test_task_done_accepts_already_verified_plan(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    mode_data = {"completed_tasks": [], "rpe_plan_dir": str(plan_dir)}
    writes = []

    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "_resolve_current_step", lambda path: None)
    monkeypatch.setattr(module, "_write_mode_file", lambda data, path: writes.append(data.copy()))
    monkeypatch.setattr(module, "_ledger_append_block", lambda *args: None)
    monkeypatch.setattr(module, "_update_lock_counter", lambda *args: None)

    assert module.cmd_task_done("already verified") == 0
    assert writes[-1]["completed_tasks"][0]["description"] == "already verified"


def test_goal_set_rejects_lifecycle_mutation(monkeypatch, tmp_path):
    mode_data = {"mode": "goal", "goal": {"state": "EXECUTING"}}
    token_path = tmp_path / "goal.json"
    token_path.write_text(json.dumps(mode_data), encoding="utf-8")
    monkeypatch.setattr(module, "_read_mode_file", lambda selected=None: (mode_data, str(token_path)))

    with pytest.raises(SystemExit) as exc:
        module.cmd_set("goal", '{"state":"ARCHIVED"}')

    assert exc.value.code == 2
    assert json.loads(token_path.read_text())["goal"]["state"] == "EXECUTING"


def test_goal_off_rejects_non_verifying_state(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("### EV-S1\n\n- exit_code: 0\n", encoding="utf-8")
    token_path = tmp_path / "tokens" / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token = {
        "mode": "goal",
        "session": {"id": "goal"},
        "task_dir": str(plan_dir),
        "status": "active",
        "goal": {"state": "EXECUTING"},
    }
    token_path.write_text(json.dumps(token), encoding="utf-8")
    mode_data = dict(token)
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda selected=None: (mode_data, str(token_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "cmd_report", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc:
        module.cmd_off(plan_dir)

    assert exc.value.code == 1
    assert json.loads(token_path.read_text())["status"] == "active"


def test_goal_report_blocks_unresolved_high_risk(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("### EV-S1\n\n- exit_code: 0\n", encoding="utf-8")
    mode_data = {
        "mode": "goal",
        "task_dir": str(plan_dir),
        "status": "active",
        "goal": {"description": "risk", "state": "VERIFYING"},
        "skipped_risks": [{"risk_level": "high", "description": "unverified isolation"}],
    }
    monkeypatch.setattr(module, "_read_mode_file", lambda selected=None: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    module.cmd_report(plan_dir)

    report = (plan_dir / "state" / "goal-report.md").read_text(encoding="utf-8")
    assert "VERIFIED: 所有计划步骤已完成" not in report
    assert "skip-risk.high" in report


def _write_valid_research(path: Path) -> None:
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


def _write_valid_plan(path: Path) -> None:
    path.write_text(
        "# Plan\n\n"
        "## Gate\n- level: L2\n\n"
        "## Phase 1\n"
        "- [ ] S1: lifecycle guard\n"
        "  - status: pending\n"
        "  - depends_on: none\n"
        "  - scope: lifecycle files\n"
        "  - acceptance: phase order is enforced\n"
        "  - verify: command:pytest\n",
        encoding="utf-8",
    )


def test_goal_machine_requires_research_then_plan_for_goal(tmp_path):
    token_path = tmp_path / "tokens" / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal", "level": "L2"},
                "task_dir": str(tmp_path),
                "status": "active",
                "goal": {"state": "CLARIFY"},
            }
        ),
        encoding="utf-8",
    )
    research = tmp_path / "research.md"
    plan = tmp_path / "plan.md"
    _write_valid_research(research)
    _write_valid_plan(plan)

    gm = state_machine.GoalMachine(token_path)
    with pytest.raises(state_machine.GoalError, match="research_path"):
        gm.transition("PLANNING")

    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "phase-handoff-CLARIFY.json").write_text(json.dumps({"schema_version": "carroros.phase_handoff.v1", "phase": "CLARIFY", "status": "ready"}), encoding="utf-8")
    gm.transition("PLANNING", research_path=research)
    (tmp_path / "state" / "phase-handoff-PLANNING.json").write_text(json.dumps({"schema_version": "carroros.phase_handoff.v1", "phase": "PLANNING", "status": "ready"}), encoding="utf-8")
    with pytest.raises(state_machine.GoalError, match="research_path and plan_path"):
        gm.transition("EXECUTING", plan_path=plan)

    gm.transition("EXECUTING", research_path=research, plan_path=plan)
    assert gm.current_state == "EXECUTING"


def test_phase0_and_plan_done_are_separate_transitions(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    research = plan_dir / "research.md"
    plan = plan_dir / "plan.md"
    (plan_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    _write_valid_research(research)
    _write_valid_plan(plan)

    token_path = tmp_path / "tokens" / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal", "level": "L2"},
                "task_dir": str(tmp_path),
                "status": "active",
                "goal": {"state": "CLARIFY"},
            }
        ),
        encoding="utf-8",
    )
    mode_data = {"task_dir": str(plan_dir), "goal": {"state": "CLARIFY"}}
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda selected=None: (mode_data, str(token_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    module.cmd_phase0_done()
    after_research = json.loads(token_path.read_text(encoding="utf-8"))
    assert after_research["goal"]["state"] == "PLANNING"
    assert "plan_passed_at" not in after_research["goal"]

    module.cmd_plan_done()
    after_plan = json.loads(token_path.read_text(encoding="utf-8"))
    assert after_plan["goal"]["state"] == "EXECUTING"
    assert "plan_passed_at" in after_plan["goal"]


def test_goal_tick_is_blocked_before_plan_done(monkeypatch, tmp_path):
    base_spec = importlib.util.spec_from_file_location(
        "carros_base_under_test", ROOT / ".claude/scripts/carros_base.py"
    )
    assert base_spec is not None and base_spec.loader is not None
    base = importlib.util.module_from_spec(base_spec)
    base_spec.loader.exec_module(base)

    task_dir = tmp_path / "task"
    task_dir.mkdir()
    token_path = task_dir / "token.json"
    plan_path = task_dir / "plan.md"
    executor_path = task_dir / "executor.md"
    _write_valid_plan(plan_path)
    executor_path.write_text("# Executor\n", encoding="utf-8")
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal", "level": "L2"},
                "task_dir": str(tmp_path),
                "status": "active",
                "stats": {"done": 0, "total": 1, "tick": 0},
                "goal": {"state": "PLANNING"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(base, "TOKEN_PATH", token_path)
    monkeypatch.setattr(base, "PLAN_PATH", plan_path)
    monkeypatch.setattr(base, "EXECUTOR_PATH", executor_path)

    assert base.cmd_tick("S1") == 2
    assert "- [ ] S1:" in plan_path.read_text(encoding="utf-8")
    assert executor_path.read_text(encoding="utf-8") == "# Executor\n"


def test_goal_rules_document_read_before_write_and_phase_order():
    skill = (ROOT / ".claude/skills/lx-goal/SKILL.md").read_text(encoding="utf-8")
    assert "File must be read first" in skill
    assert "plan-done" in skill
    assert "PLANNING" in skill and "EXECUTING" in skill


def test_goal_machine_fails_closed_when_research_gate_is_unavailable(monkeypatch, tmp_path):
    token_path = tmp_path / "goal.json"
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal"},
                "goal": {"state": "CLARIFY"},
            }
        ),
        encoding="utf-8",
    )
    research = tmp_path / "research.md"
    _write_valid_research(research)
    monkeypatch.setattr(state_machine, "ResearchGate", None)
    gm = state_machine.GoalMachine(token_path)

    with pytest.raises(state_machine.GoalError, match="ResearchGate unavailable"):
        gm.transition("PLANNING", research_path=research)


def test_phase0_done_preserves_state_machine_transition(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    research = plan_dir / "research.md"
    plan = plan_dir / "plan.md"
    (plan_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    _write_valid_research(research)
    _write_valid_plan(plan)
    token_path = tmp_path / "tokens" / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal", "level": "L2"},
                "task_dir": str(tmp_path),
                "status": "active",
                "goal": {"state": "CLARIFY"},
            }
        ),
        encoding="utf-8",
    )
    mode_data = json.loads(token_path.read_text(encoding="utf-8"))
    mode_data["task_dir"] = str(plan_dir)
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, str(token_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    module.cmd_phase0_done()

    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["goal"]["state"] == "PLANNING"


def test_plan_done_rolls_back_token_when_sidecar_commit_fails(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    research = plan_dir / "research.md"
    plan = plan_dir / "plan.md"
    (plan_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    _write_valid_research(research)
    _write_valid_plan(plan)
    token_path = tmp_path / "tokens" / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal", "level": "L2"},
                "task_dir": str(tmp_path),
                "status": "active",
                "goal": {"state": "PLANNING"},
            }
        ),
        encoding="utf-8",
    )
    original_token = token_path.read_bytes()
    mode_data = {"mode": "goal", "rpe_plan_dir": str(plan_dir)}

    def fail_sidecar(*args):
        raise OSError("sidecar unavailable")

    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "_write_mode_file", fail_sidecar)

    with pytest.raises(SystemExit) as exc:
        module.cmd_plan_done()
    assert exc.value.code == 2
    assert token_path.read_bytes() == original_token


def test_goal_execution_writer_gate_excludes_archiving(tmp_path):
    base_spec = importlib.util.spec_from_file_location(
        "carros_base_gate_under_test", ROOT / ".claude/scripts/carros_base.py"
    )
    assert base_spec is not None and base_spec.loader is not None
    base = importlib.util.module_from_spec(base_spec)
    base_spec.loader.exec_module(base)

    assert not base._require_goal_execution_state(
        {"mode": "goal", "goal": {"state": "ARCHIVING"}},
        "collect",
    )
    assert base._require_goal_execution_state(
        {"mode": "goal", "goal": {"state": "EXECUTING"}},
        "collect",
    )


def test_subagent_executor_seals_goal_parent_before_execution(monkeypatch, tmp_path):
    executor_spec = importlib.util.spec_from_file_location(
        "sub_agent_executor_under_test", ROOT / ".claude/scripts/sub_agent_executor.py"
    )
    assert executor_spec is not None and executor_spec.loader is not None
    executor_module = importlib.util.module_from_spec(executor_spec)
    executor_spec.loader.exec_module(executor_module)

    project = tmp_path / "project"
    fake_script = project / ".claude/scripts/sub_agent_executor.py"
    fake_script.parent.mkdir(parents=True)
    monkeypatch.setattr(executor_module, "__file__", str(fake_script))
    task_dir = project / ".omc/tasks/20260811/goal"
    sub_dir = task_dir / "sub_task/sub-S1"
    sub_dir.mkdir(parents=True)
    token_path = project / ".omc/tokens/20260811/goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal"},
                "goal": {"state": "PLANNING"},
            }
        ),
        encoding="utf-8",
    )

    executor = executor_module.SubAgentExecutor(sub_dir)
    with pytest.raises(RuntimeError, match="Goal state=PLANNING"):
        executor._goal_write_allowed()


def test_goal_done_does_not_archive_without_goal_machine(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("# Executor\n\n## Acceptance Checklist\n- [x] S1 complete\n\n### EV-S1\n\n- step: S1\n- exit_code: 0\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    token_path = tmp_path / "tokens" / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal"},
                "task_dir": str(plan_dir),
                "status": "active",
                "stats": {"done": 1, "total": 1},
                "goal": {"state": "VERIFYING"},
            }
        ),
        encoding="utf-8",
    )
    mode_path = tmp_path / "mode.json"
    mode_path.write_text("{}", encoding="utf-8")
    mode_data = {"mode": "goal", "rpe_plan_dir": str(plan_dir)}
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, str(mode_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "_GSM", None)

    with pytest.raises(SystemExit) as exc:
        module.cmd_done()
    assert exc.value.code == 1
    assert token_path.exists()


def test_goal_done_retains_archived_token_and_removes_sidecar(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text(
        "## Conditions\nfocused tests\n\n"
        "## Key Changes\ncanonical handoff\n\n"
        "## Decisions\nnone: bounded scope\n\n"
        "## Acceptance Checklist\n- [x] S1 complete\n\n"
        "## TDD Evidence\ndependency TDD exit 0; regression TDD exit 0\n\n"
        "### EV-S1\n\n- step: S1\n- exit_code: 0\n",
        encoding="utf-8",
    )
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    token_path = tmp_path / "tokens" / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps({
            "mode": "goal",
            "session": {"id": "goal"},
            "status": "active",
            "stats": {"done": 1, "total": 1},
            "goal": {"state": "VERIFYING"},
        }),
        encoding="utf-8",
    )
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    lock_path.touch()
    mode_path = tmp_path / "mode.json"
    mode_path.write_text("{}", encoding="utf-8")
    mode_data = {"mode": "goal", "rpe_plan_dir": str(plan_dir)}
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, str(mode_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    module.cmd_done()

    final_token = json.loads(token_path.read_text(encoding="utf-8"))
    assert final_token["status"] == "archived"
    assert token_path.exists()
    assert not lock_path.exists()


def test_goal_off_retains_completed_token_and_removes_sidecar(monkeypatch, tmp_path):
    project = tmp_path / "project"
    plan_dir = project / ".omc" / "tasks" / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("# Executor\n\n## Acceptance Checklist\n- [x] S1 complete\n\n### EV-S1\n\n- step: S1\n- exit_code: 0\n", encoding="utf-8")
    token_root = project / ".omc" / "tokens"
    token_path = token_root / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps({"session": {"id": "goal"}, "status": "active", "goal": {"state": "VERIFYING"}}),
        encoding="utf-8",
    )
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    lock_path.touch()
    state_dir = project / ".omc" / "state"
    mode_path = state_dir / "tokens" / "lx-goal.json"
    mode_path.parent.mkdir(parents=True)
    mode_path.write_text("{}", encoding="utf-8")
    signal = state_dir / "tokens" / "autonomous.active"
    signal.touch()
    mode_data = {"rpe_plan_dir": str(plan_dir), "completed_tasks": []}
    monkeypatch.setattr(module, "PROJECT_ROOT", project)
    monkeypatch.setattr(module, "STATE_DIR", state_dir)
    monkeypatch.setattr(module, "TOKENS_DIR", token_root)
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, str(mode_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "cmd_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "_lc_set_mode", lambda mode: None)

    module.cmd_off()

    final_token = json.loads(token_path.read_text(encoding="utf-8"))
    assert final_token["status"] == "completed"
    assert token_path.exists()
    assert not lock_path.exists()


def test_goal_off_preserves_archived_token(monkeypatch, tmp_path):
    project = tmp_path / "project"
    plan_dir = project / ".omc" / "tasks" / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("## Acceptance Checklist\n- [x] S1 complete\n\n### EV-S1\n\n- step: S1\n- exit_code: 0\n", encoding="utf-8")
    token_root = project / ".omc" / "tokens"
    token_path = token_root / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(json.dumps({"session": {"id": "goal"}, "status": "archived"}), encoding="utf-8")
    state_dir = project / ".omc" / "state"
    mode_path = state_dir / "tokens" / "lx-goal.json"
    mode_path.parent.mkdir(parents=True)
    mode_path.write_text("{}", encoding="utf-8")
    signal = state_dir / "tokens" / "autonomous.active"
    signal.touch()
    mode_data = {"rpe_plan_dir": str(plan_dir), "completed_tasks": []}

    monkeypatch.setattr(module, "PROJECT_ROOT", project)
    monkeypatch.setattr(module, "STATE_DIR", state_dir)
    monkeypatch.setattr(module, "TOKENS_DIR", token_root)
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, str(mode_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "cmd_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "_lc_set_mode", lambda mode: None)

    module.cmd_off()

    assert json.loads(token_path.read_text())["status"] == "archived"


def test_goal_off_rejects_empty_plan_without_finalizing(monkeypatch, tmp_path):
    project = tmp_path / "project"
    plan_dir = project / ".omc" / "tasks" / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    token_root = project / ".omc" / "tokens"
    token_path = token_root / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(json.dumps({"session": {"id": "goal"}, "status": "active"}), encoding="utf-8")
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    lock_path.touch()
    state_dir = project / ".omc" / "state"
    mode_path = state_dir / "tokens" / "lx-goal.json"
    mode_path.parent.mkdir(parents=True)
    mode_path.write_text("{}", encoding="utf-8")
    signal = state_dir / "tokens" / "autonomous.active"
    signal.touch()
    mode_data = {"rpe_plan_dir": str(plan_dir), "completed_tasks": []}

    monkeypatch.setattr(module, "PROJECT_ROOT", project)
    monkeypatch.setattr(module, "STATE_DIR", state_dir)
    monkeypatch.setattr(module, "TOKENS_DIR", token_root)
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, str(mode_path)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "cmd_report", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc:
        module.cmd_off()

    assert exc.value.code == 1
    assert json.loads(token_path.read_text())["status"] == "active"
    assert lock_path.exists()
    assert mode_path.exists()


def test_goal_poll_expiry_retains_token_and_removes_sidecar(monkeypatch, tmp_path):
    project = tmp_path / "project"
    plan_dir = project / ".omc" / "tasks" / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    for name in ("plan.md", "research.md", "executor.md"):
        (plan_dir / name).write_text("# fixture\n", encoding="utf-8")
    token_root = project / ".omc" / "tokens"
    token_path = token_root / "20260811" / "goal.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps({
            "mode": "goal",
            "session": {"id": "goal"},
            "task_dir": str(plan_dir),
            "status": "active",
            "goal": {"expires_at": "2000-01-01T00:00:00+00:00"},
        }),
        encoding="utf-8",
    )
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    lock_path.touch()
    monkeypatch.setattr(module, "TOKENS_DIR", token_root)
    monkeypatch.setattr(module, "cmd_report", lambda *args, **kwargs: None)

    module.cmd_poll(plan_dir)

    final_token = json.loads(token_path.read_text(encoding="utf-8"))
    assert final_token["status"] == "expired"
    assert token_path.exists()
    assert not lock_path.exists()


def test_phase0_rolls_back_token_when_mode_sidecar_commit_fails(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    research = plan_dir / "research.md"
    _write_valid_research(research)
    token_dir = tmp_path / "tokens" / "20260811"
    token_dir.mkdir(parents=True)
    token_path = token_dir / "goal.json"
    token_path.write_text(
        json.dumps({
            "mode": "goal",
            "session": {"id": "goal", "level": "L2"},
            "task_dir": str(plan_dir),
            "goal": {"state": "CLARIFY"},
        }),
        encoding="utf-8",
    )
    before = token_path.read_bytes()
    mode_data = {"mode": "goal", "rpe_plan_dir": str(plan_dir)}

    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    def fail_sidecar(*args):
        raise OSError("mode sidecar unavailable")

    monkeypatch.setattr(module, "_write_mode_file", fail_sidecar)
    with pytest.raises(SystemExit) as exc:
        module.cmd_phase0_done()
    assert exc.value.code == 2

    assert token_path.read_bytes() == before


def test_goal_verify_step_skips_tick_when_already_verifying(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "goal"
    plan_dir.mkdir(parents=True)
    token_dir = tmp_path / "tokens" / "20260811"
    token_dir.mkdir(parents=True)
    token_path = token_dir / "goal.json"
    token_path.write_text(
        json.dumps({
            "mode": "goal",
            "session": {"id": "goal", "level": "L2"},
            "task_dir": str(plan_dir),
            "goal": {"state": "VERIFYING"},
        }),
        encoding="utf-8",
    )
    mode_data = {"mode": "goal", "rpe_plan_dir": str(plan_dir)}
    calls = []

    class Result:
        returncode = 0
        stdout = "verified"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "_read_mode_file", lambda plan_dir=None: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._verify_goal_step("S1") == 0
    assert len(calls) == 1
    assert calls[0][-2:] == ["verify", "--step"] or "verify" in calls[0]


# ── missing_verified_evidence: VerifyGate marker for red-TDD steps ──

def _mk_plan_dir(tmp_path, executor_text, plan_text="- [x] S1: done\n"):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text(plan_text, encoding="utf-8")
    (plan_dir / "executor.md").write_text(executor_text, encoding="utf-8")
    return plan_dir


def test_missing_verified_evidence_accepts_verifygate_marker(tmp_path):
    """A red-TDD step (EV exit_code 1) with the VerifyGate marker is verified."""
    plan_dir = _mk_plan_dir(
        tmp_path,
        "### EV-S1\n\n- step: S1\n- exit_code: 1\n- assertion: pytest 红测失败于缺失实现\n\n"
        "### EV-S1-VERIFIED\n\n- step: S1\n- exit_code: 0\n- source: VerifyGate\n",
    )
    assert module.missing_verified_evidence(plan_dir) == []


def test_missing_verified_evidence_flags_red_test_without_marker(tmp_path):
    """Without the VerifyGate marker, a red-test EV block alone is not verified."""
    plan_dir = _mk_plan_dir(
        tmp_path,
        "### EV-S1\n\n- step: S1\n- exit_code: 1\n- assertion: pytest 红测失败于缺失实现\n",
    )
    assert module.missing_verified_evidence(plan_dir) == ["S1"]


def test_report_accepts_verifygate_marker_for_red_test_step(monkeypatch, tmp_path):
    """cmd_report must emit VERIFIED when a red-TDD step carries the marker."""
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text(
        "# Executor\n\n### EV-S1\n\n- step: S1\n- exit_code: 1\n- assertion: pytest 红测失败于缺失实现\n\n"
        "### EV-S1-VERIFIED\n\n- step: S1\n- exit_code: 0\n- source: VerifyGate\n",
        encoding="utf-8",
    )
    mode_data = {"goal": {"description": "red tdd"}, "task_dir": str(plan_dir), "completed_tasks": []}
    monkeypatch.setattr(module, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(module, "_read_mode_file", lambda selected=None: (mode_data, str(selected or plan_dir)))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)

    module.cmd_report(plan_dir)

    report = (plan_dir / "state" / "goal-report.md").read_text(encoding="utf-8")
    assert "verified_evidence_missing" not in report
    assert "VERIFIED: 所有计划步骤已完成" in report
