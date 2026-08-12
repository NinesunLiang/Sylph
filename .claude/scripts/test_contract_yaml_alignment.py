"""Contract-first 真源对齐测试（ADR 0015）。

YAML 是唯一真源：代码行为必须与 schemas/contract/*.yaml 一致。
期望值固化了原 phase_contracts.PHASE_CONTRACTS dict 的语义（行为不变基线）。
"""
from pathlib import Path

import pytest
import yaml

from phase_contracts import phase_contract, SCHEMA_VERSION
from step_contracts import parse_plan_steps, STEP_STATUSES, EVIDENCE_REQUIRED_SECTIONS

SCRIPTS = Path(__file__).resolve().parent
CONTRACT_DIR = SCRIPTS.parent / "schemas" / "contract"


def load_phase_contracts_yaml():
    with open(CONTRACT_DIR / "phase_handoff.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_step_contract_yaml():
    with open(CONTRACT_DIR / "step_contract.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 期望基线：由原 PHASE_CONTRACTS dict 固化（行为不变） ──────────────

EXPECTED_PHASES = {
    "CLARIFY": {
        "inputs": {"required": ["goal.description", "task_dir"], "inherited": []},
        "outputs": {"required": ["research.sections", "research.dependency_tree"], "artifacts": ["research.md"]},
        "evidence": {"required": ["research_gate.result", "research_gate.errors"]},
        "next_gate": {"target_phase": "PLANNING", "checks": ["ResearchGate.validate(research.md)"]},
    },
    "PLANNING": {
        "inputs": {"required": ["research.md", "research_gate.result"], "inherited": ["goal.description", "task_dir"]},
        "outputs": {"required": ["plan.phases", "plan.steps", "step.acceptance", "step.verify"], "artifacts": ["plan.md"]},
        "evidence": {"required": ["plan_gate.result", "plan_gate.errors"]},
        "next_gate": {"target_phase": "EXECUTING", "checks": ["ResearchGate.validate(research.md)", "PlanGate.validate(plan.md)"]},
    },
    "EXECUTING": {
        "inputs": {"required": ["plan.md", "plan_gate.result", "current_step.schema"], "inherited": ["research.md", "task_dir"]},
        "outputs": {"required": ["step.key_changes", "step.tdd_evidence", "step.evidence"], "artifacts": ["executor.md", "state/step-handoff-<step>.json"]},
        "evidence": {"required": ["step_start.result", "dependency_tdd", "regression_tdd"]},
        "next_gate": {"target_phase": "VERIFYING", "checks": ["all steps completed", "step handoff ready"]},
    },
    "VERIFYING": {
        "inputs": {"required": ["executor.md", "all step handoffs", "verify rules"], "inherited": ["plan.md", "research.md"]},
        "outputs": {"required": ["verify.decisions", "verify.evidence_summary", "verify.next_actions"], "artifacts": ["state/verify-results.json"]},
        "evidence": {"required": ["VerifyGate.result", "audit event"]},
        "next_gate": {"target_phase": "ARCHIVING", "checks": ["all VerifyGate decisions are VERIFIED or WARN", "no unresolved blockers"]},
    },
    "ARCHIVING": {
        "inputs": {"required": ["verify-results", "final-report"], "inherited": ["plan.md", "executor.md", "research.md"]},
        "outputs": {"required": ["archive.manifest", "archive.verdict"], "artifacts": [".omc/archive/<task>"]},
        "evidence": {"required": ["lint.result", "archive.result"]},
        "next_gate": {"target_phase": "ARCHIVED", "checks": ["archive completed", "token lock removed"]},
    },
}


# ── phase_handoff.yaml 真源 ─────────────────────────────────────────

def test_yaml_contains_all_five_phases():
    data = load_phase_contracts_yaml()
    phases = data.get("phases", {})
    assert set(phases.keys()) == set(EXPECTED_PHASES.keys())


def test_yaml_schema_version_constant():
    data = load_phase_contracts_yaml()
    assert data["schema_version"]["const"] == SCHEMA_VERSION


def test_phase_contract_matches_yaml_semantics():
    """phase_contract 返回值与 YAML phases 段逐字段一致（行为不变基线）。"""
    data = load_phase_contracts_yaml()
    for phase, expected in data["phases"].items():
        contract = phase_contract(phase)
        assert contract["inputs"]["required"] == expected["inputs"]["required"]
        assert contract["inputs"]["inherited"] == expected["inputs"]["inherited"]
        assert contract["outputs"]["required"] == expected["outputs"]["required"]
        assert contract["outputs"]["artifacts"] == expected["outputs"]["artifacts"]
        assert contract["evidence"]["required"] == expected["evidence"]["required"]
        assert contract["next_gate"]["target_phase"] == expected["next_gate"]["target_phase"]
        assert contract["next_gate"]["checks"] == expected["next_gate"]["checks"]


def test_phase_contract_unknown_phase_raises():
    with pytest.raises(ValueError):
        phase_contract("NOPE")


# ── step_contract.yaml 真源 ─────────────────────────────────────────

def test_step_contract_yaml_exists_and_versioned():
    data = load_step_contract_yaml()
    assert data["schema_version"] == "carroros.step_contract.v1"


def test_step_statuses_match_yaml():
    data = load_step_contract_yaml()
    assert STEP_STATUSES == set(data["step"]["status"]["values"])


def test_evidence_sections_match_yaml():
    data = load_step_contract_yaml()
    assert EVIDENCE_REQUIRED_SECTIONS == data["evidence"]["required_sections"]


def test_parse_plan_steps_fields_subset_of_yaml():
    data = load_step_contract_yaml()
    declared = set(data["step"]["fields"].keys())
    plan = "- [ ] S1:x\n  - depends_on: none\n  - acceptance: a\n  - verify: v\n  - scope: s"
    step = parse_plan_steps(plan)[0]
    assert set(step.keys()) <= declared


def test_step_contract_yaml_declares_step_statuses_in_contract():
    """YAML 必须显式声明 step 状态机，杜绝隐式硬编码。"""
    data = load_step_contract_yaml()
    assert set(data["step"]["status"]["values"]) == {"pending", "active", "completed", "blocked"}


# ── state_transitions.yaml 强制真源 ────────────────────────────────

from state_transitions import is_legal, require_transition, states  # noqa: E402


def test_state_transitions_loads_declared_states():
    assert set(states()) == {
        "need_clarification", "ready", "planning", "spec_review",
        "executing", "fallback_exploring", "blocked", "done",
    }


def test_state_transitions_legal_paths():
    assert is_legal("executing", "done")
    assert is_legal("planning", "spec_review")
    assert is_legal("executing", "fallback_exploring")
    assert is_legal("blocked", "executing")  # Half-Open 试探


def test_state_transitions_illegal_paths_rejected():
    assert not is_legal("need_clarification", "done")
    assert not is_legal("spec_review", "done")  # 跳过执行直接完成被禁
    assert not is_legal("ready", "blocked")


def test_require_transition_raises_on_illegal():
    with pytest.raises(ValueError):
        require_transition("need_clarification", "done")
    require_transition("executing", "done")  # 合法转换不抛


def test_state_transitions_yaml_marks_executing_to_done_guarded():
    """executing→done 必须带「验收 100% 通过」约束（防御未全绿即完成）。"""
    with open(CONTRACT_DIR / "state_transitions.yaml", encoding="utf-8") as f:
        st = yaml.safe_load(f)
    illegal = st["illegal_transitions"]
    assert any(
        t["from"] == "executing" and t["to"] == "done"
        for t in illegal
    )
