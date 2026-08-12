import importlib.util
from pathlib import Path

import pytest

from phase_contracts import (
    complete_phase,
    SCHEMA_VERSION,
    missing_contract_fields,
    phase_contract,
    read_contract,
    step_contract,
    validate_contract_ready,
    write_contract,
)


def load_goal_contracts():
    path = Path(__file__).resolve().parent / "goal_contracts.py"
    spec = importlib.util.spec_from_file_location("phase_goal_contracts", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase_contract_declares_next_gate_and_required_outputs():
    contract = phase_contract("PLANNING")
    assert contract["schema_version"] == SCHEMA_VERSION
    assert contract["outputs"]["required"]
    assert contract["next_gate"]["target_phase"] == "EXECUTING"
    assert "plan.md" in contract["outputs"]["artifacts"]


def test_step_contract_declares_all_completion_sections_before_execution():
    contract = step_contract({"id": "S1", "scope": "src", "acceptance": "works", "verify": "command:pytest"})
    assert "S1.key_changes" in contract["outputs"]["required"]
    assert "S1.tdd_evidence" in contract["outputs"]["required"]
    assert "S1.evidence" in contract["outputs"]["required"]
    # 契约精简（6→3，还债项）：Conditions/Decisions/Acceptance Checklist 不再要求
    assert "S1.conditions" not in contract["outputs"]["required"]
    assert "S1.decisions" not in contract["outputs"]["required"]
    assert "S1.acceptance_checklist" not in contract["outputs"]["required"]


def test_missing_fields_are_reported_before_next_gate():
    contract = phase_contract("EXECUTING")
    missing = missing_contract_fields(contract, {"step.key_changes": "ready"})
    assert "step.tdd_evidence" in missing


def test_handoff_round_trip_and_ready_validation(tmp_path):
    contract = phase_contract("PLANNING")
    path = write_contract(tmp_path, contract, "phase-handoff-PLANNING.json")
    assert path == tmp_path / "state" / "phase-handoff-PLANNING.json"
    assert read_contract(tmp_path, "phase-handoff-PLANNING.json")["phase"] == "PLANNING"
    values = {key: "ready" for key in contract["outputs"]["required"]}
    complete_phase(tmp_path, "PLANNING", values)
    assert validate_contract_ready(tmp_path, "PLANNING", values)["phase"] == "PLANNING"


def test_complete_phase_from_artifacts_derives_execution_outputs(tmp_path):
    from phase_contracts import complete_phase_from_artifacts, start_phase

    (tmp_path / "executor.md").write_text(
        "## Key Changes\ncanonical handoff\n\n"
        "## TDD Evidence\ndependency TDD exit 0; regression TDD exit 0\n\n"
        "### EV-S1\n- exit_code: 0\n- assertion: passed\n",
        encoding="utf-8",
    )
    (tmp_path / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (tmp_path / "state").mkdir()
    start_phase(tmp_path, "EXECUTING")

    complete_phase_from_artifacts(tmp_path, "EXECUTING")

    contract = read_contract(tmp_path, "phase-handoff-EXECUTING.json")
    assert contract["status"] == "ready"
    assert all(contract["values"][key] for key in contract["outputs"]["required"])


def test_complete_phase_from_artifacts_rejects_missing_evidence(tmp_path):
    from phase_contracts import complete_phase_from_artifacts, start_phase

    (tmp_path / "executor.md").write_text("## Conditions\nplaceholder\n", encoding="utf-8")
    (tmp_path / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    start_phase(tmp_path, "EXECUTING")

    with pytest.raises(ValueError, match="artifacts incomplete"):
        complete_phase_from_artifacts(tmp_path, "EXECUTING")


def test_complete_step_from_artifacts_derives_step_outputs(tmp_path):
    from phase_contracts import complete_step_from_artifacts, start_step

    (tmp_path / "executor.md").write_text(
        "## Key Changes\nchange\n\n"
        "## TDD Evidence\ndependency TDD exit 0; regression TDD exit 0\n\n"
        "### EV-S1\n- exit_code: 0\n- assertion: passed\n",
        encoding="utf-8",
    )
    (tmp_path / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    start_step(tmp_path, {"id": "S1"})

    complete_step_from_artifacts(tmp_path, "S1")

    assert read_contract(tmp_path, "step-handoff-S1.json")["status"] == "ready"
def test_plan_gate_accepts_uppercase_checkbox(tmp_path):
    contracts = load_goal_contracts()
    plan = tmp_path / "plan.md"
    plan.write_text(
        "# Plan\n\n## Gate\n- level: L2\n\n## Phase 1\n"
        "- [X] S1: done\n"
        "  - status: completed\n"
        "  - depends_on: none\n"
        "  - scope: lifecycle\n"
        "  - acceptance: done\n"
        "  - verify: assertion: done\n",
        encoding="utf-8",
    )
    assert contracts.PlanGate.validate(plan)["steps"] == 1



def test_auto_progress_ignores_zero_total_stats(tmp_path):
    state_path = tmp_path / "tokens" / "20260812" / "auto.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text('{"stats":{"done":0,"total":0},"goal":{"state":"EXECUTING"}}', encoding="utf-8")
    state_machine_path = Path(__file__).resolve().parent / "goal_state_machine.py"
    spec = importlib.util.spec_from_file_location("zero_total_auto_progress", state_machine_path)
    assert spec and spec.loader
    state_machine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state_machine)
    assert state_machine.GoalMachine(state_path).auto_progress() == []


def test_goal_transition_rejects_zero_total_stats(tmp_path):
    state_path = tmp_path / "tokens" / "20260812" / "goal.json"
    task_dir = tmp_path / "tasks" / "20260812" / "goal"
    task_dir.mkdir(parents=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text('{"mode":"goal","task_dir":"' + str(task_dir) + '","stats":{"done":0,"total":0},"goal":{"state":"EXECUTING"}}', encoding="utf-8")
    state_machine_path = Path(__file__).resolve().parent / "goal_state_machine.py"
    spec = importlib.util.spec_from_file_location("zero_total_state_machine", state_machine_path)
    assert spec and spec.loader
    state_machine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state_machine)
    machine = state_machine.GoalMachine(state_path)
    with pytest.raises(state_machine.GoalError, match="not all steps done"):
        machine.transition("VERIFYING")


def test_goal_transition_consumes_pending_phase_handoff(tmp_path):
    state_path = tmp_path / "tokens" / "20260812" / "goal.json"
    task_dir = tmp_path / "tasks" / "20260812" / "goal"
    task_dir.mkdir(parents=True)
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        '{"mode":"goal","task_dir":"' + str(task_dir) + '","goal":{"state":"CLARIFY"}}',
        encoding="utf-8",
    )
    write_contract(task_dir, phase_contract("CLARIFY"), "phase-handoff-CLARIFY.json")
    state_machine_path = Path(__file__).resolve().parent / "goal_state_machine.py"
    spec = importlib.util.spec_from_file_location("phase_goal_state_machine", state_machine_path)
    assert spec and spec.loader
    state_machine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state_machine)
    machine = state_machine.GoalMachine(state_path)
    with pytest.raises(state_machine.GoalError, match="phase handoff blocked"):
        machine.transition("PLANNING", research_path=tmp_path / "research.md")


def test_plan_gate_rejects_unknown_checkbox(tmp_path):
    contracts = load_goal_contracts()
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\n## Gate\n- level: L2\n\n## Phase 1\n- [?] S1: malformed\n", encoding="utf-8")
    with pytest.raises(contracts.PlanGateError, match="at least 1 Step"):
        contracts.PlanGate.validate(plan)


def test_plan_gate_rejects_phase_orphan_step(tmp_path):
    contracts = load_goal_contracts()
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\n## Gate\n- level: L2\n\n- [ ] S1: orphan\n", encoding="utf-8")
    with pytest.raises(contracts.PlanGateError, match="Phase"):
        contracts.PlanGate.validate(plan)


def test_plan_gate_rejects_unprefixed_verify_before_execution(tmp_path):
    contracts = load_goal_contracts()
    plan = tmp_path / "plan.md"
    plan.write_text(
        "# Plan\n\n## Gate\n- level: L2\n\n## Phase 1\n"
        "- [ ] S1: malformed\n"
        "  - status: pending\n"
        "  - depends_on: none\n"
        "  - scope: src\n"
        "  - acceptance: works\n"
        "  - verify: run tests later\n",
        encoding="utf-8",
    )
    with pytest.raises(contracts.PlanGateError, match="Invalid verify rules"):
        contracts.PlanGate.validate(plan)


def test_is_placeholder_does_not_flag_common_word_in_long_prose():
    """'todo'/'n/a' as a normal word in a long decision line is real content,
    not a placeholder stub (E-ISO-001 fix for decisions_missing_rationale)."""
    contracts = load_goal_contracts()
    long_prose = "- 决策: 删除全局标记；handoff 无损字段 = goal + next_action + todo + decisions + 文档路径"
    assert contracts.is_placeholder(long_prose) is False


def test_is_placeholder_still_flags_short_stub():
    contracts = load_goal_contracts()
    assert contracts.is_placeholder("- todo") is True
    assert contracts.is_placeholder("- n/a") is True
    assert contracts.is_placeholder("- [ ] tbd") is True
    assert contracts.is_placeholder("- 待填写") is True


def test_is_placeholder_flags_distinctive_phrase_anywhere():
    contracts = load_goal_contracts()
    assert contracts.is_placeholder("still needs expected update in this block") is True
