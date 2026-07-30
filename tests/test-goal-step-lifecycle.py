#!/usr/bin/env python3
"""Behavior contracts for Goal serial lifecycle and Step atomic evidence."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
GSM_PATH = ROOT / ".claude" / "scripts" / "goal_state_machine.py"
STEP_PATH = ROOT / ".claude" / "scripts" / "step_contracts.py"


def load_module(name: str, path: Path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def valid_evidence(step_id: str) -> str:
    return (
        "# Executor\n\n"
        "## Conditions\n- status: active\n\n"
        "## Key Changes\n- file: src/main.py changed\n\n"
        "## Decisions\n- decision: approach A\n- rationale: deterministic\n\n"
        "## Acceptance Checklist\n- [x] AC1: passes\n\n"
        "## TDD Evidence\n"
        "- dependency TDD: pytest tests/test_dep.py -> exit 0\n"
        "- regression TDD: pytest tests/ -> exit 0\n\n"
        f"### EV-{step_id}\n"
        f"- step: {step_id}\n"
        "- type: command\n"
        "- source: pytest tests/\n"
        "- exit_code: 0\n"
        "- evidence_level: E3\n"
    )


def test_transition_blocks_verifying_when_steps_incomplete(tmp_path: Path):
    gsm = load_module("_goal_stats_gate_test", GSM_PATH)
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps({
        "goal": {"state": "EXECUTING"},
        "stats": {"done": 1, "total": 2},
    }), encoding="utf-8")

    machine = gsm.GoalMachine(token_path)
    assert machine.can_transition(gsm.VERIFYING) is False
    with pytest.raises(gsm.GoalError, match="not all steps"):
        machine.transition(gsm.VERIFYING)
    assert machine.current_state == gsm.EXECUTING


def test_auto_progress_stops_at_verifying_until_verify_results(tmp_path: Path):
    gsm = load_module("_goal_auto_progress_test", GSM_PATH)
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps({
        "goal": {"state": "VERIFYING"},
        "stats": {"done": 2, "total": 2},
    }), encoding="utf-8")

    machine = gsm.GoalMachine(token_path)
    assert machine.auto_progress() == []
    assert machine.current_state == gsm.VERIFYING


def test_complete_step_requires_prior_activation(tmp_path: Path):
    step = load_module("_step_requires_active_test", STEP_PATH)
    token_path = tmp_path / "token.json"
    plan_path = tmp_path / "plan.md"
    executor_path = tmp_path / "executor.md"
    token_path.write_text(json.dumps({
        "task": {"current_step": "S1", "status": "active"},
        "stats": {"done": 0, "total": 1},
    }), encoding="utf-8")
    plan_path.write_text(
        "# Plan\n## Phase 1\n- [ ] S1: first\n"
        "  - status: pending\n  - depends_on: none\n",
        encoding="utf-8",
    )
    executor_path.write_text(valid_evidence("S1"), encoding="utf-8")

    with pytest.raises(ValueError, match="expected active"):
        step.complete_step_atomic(token_path, plan_path, executor_path, "S1")


def test_partial_step_completion_keeps_task_active(tmp_path: Path):
    step = load_module("_step_partial_status_test", STEP_PATH)
    token_path = tmp_path / "token.json"
    plan_path = tmp_path / "plan.md"
    executor_path = tmp_path / "executor.md"
    token_path.write_text(json.dumps({
        "task": {"current_step": "S1", "status": "active"},
        "stats": {"done": 0, "total": 2},
    }), encoding="utf-8")
    plan_path.write_text(
        "# Plan\n## Phase 1\n"
        "- [a] S1: first\n  - status: active\n  - depends_on: none\n"
        "- [ ] S2: second\n  - status: pending\n  - depends_on: S1\n",
        encoding="utf-8",
    )
    executor_path.write_text(valid_evidence("S1"), encoding="utf-8")

    step.complete_step_atomic(token_path, plan_path, executor_path, "S1")
    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["stats"]["done"] == 1
    assert token["task"]["status"] == "active"


def test_start_step_rolls_back_all_files_when_replace_fails(tmp_path: Path):
    step = load_module("_step_rollback_test", STEP_PATH)
    token_path = tmp_path / "token.json"
    plan_path = tmp_path / "plan.md"
    executor_path = tmp_path / "executor.md"
    token_path.write_text(json.dumps({
        "task": {"current_step": "S1", "status": "active"},
        "stats": {"done": 0, "total": 1},
    }), encoding="utf-8")
    plan_path.write_text(
        "# Plan\n## Phase 1\n- [ ] S1: first\n"
        "  - status: pending\n  - depends_on: none\n",
        encoding="utf-8",
    )
    executor_path.write_text("# Executor\n", encoding="utf-8")
    before = {
        plan_path: plan_path.read_bytes(),
        token_path: token_path.read_bytes(),
        executor_path: executor_path.read_bytes(),
    }
    calls = 0

    def fail_second_replace(src: Path, dst: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        os.replace(src, dst)

    with patch.object(step, "_atomic_replace", side_effect=fail_second_replace):
        with pytest.raises(OSError, match="injected replace failure"):
            step.start_step_atomic(token_path, plan_path, executor_path, "S1")

    for path, original in before.items():
        assert path.read_bytes() == original, f"partial transaction left in {path.name}"
