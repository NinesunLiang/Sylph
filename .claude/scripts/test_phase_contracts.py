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
    assert "S1.conditions" in contract["outputs"]["required"]
    assert "S1.key_changes" in contract["outputs"]["required"]
    assert "S1.decisions" in contract["outputs"]["required"]
    assert "S1.acceptance_checklist" in contract["outputs"]["required"]
    assert "S1.tdd_evidence" in contract["outputs"]["required"]
    assert "S1.evidence" in contract["outputs"]["required"]


def test_missing_fields_are_reported_before_next_gate():
    contract = phase_contract("EXECUTING")
    missing = missing_contract_fields(contract, {"step.conditions": "ready"})
    assert "step.key_changes" in missing


def test_handoff_round_trip_and_ready_validation(tmp_path):
    contract = phase_contract("PLANNING")
    path = write_contract(tmp_path, contract, "phase-handoff-PLANNING.json")
    assert path == tmp_path / "state" / "phase-handoff-PLANNING.json"
    assert read_contract(tmp_path, "phase-handoff-PLANNING.json")["phase"] == "PLANNING"
    values = {key: "ready" for key in contract["outputs"]["required"]}
    complete_phase(tmp_path, "PLANNING", values)
    assert validate_contract_ready(tmp_path, "PLANNING", values)["phase"] == "PLANNING"


def test_ready_validation_rejects_pending_handoff(tmp_path):
    write_contract(tmp_path, phase_contract("CLARIFY"), "phase-handoff-CLARIFY.json")
    with pytest.raises(ValueError, match="schema not ready"):
        validate_contract_ready(tmp_path, "CLARIFY", filename="phase-handoff-CLARIFY.json")


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
