"""Red tests for Goal/JEV/hook hardening contracts."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def _temporary_env(name: str, value: str):
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_goal_init_accepts_l1_goal_level(tmp_path):
    carros = _load(ROOT / ".claude/scripts/carros_base.py", "hardening_carros_l1")
    carros.OMC_TOKENS = tmp_path / "tokens"
    with _temporary_env("CARROROS_TASK_MODE", "goal"):
        result = carros.cmd_init(
            task_id="goal-l1-contract",
            task_dir=str(tmp_path / "task"),
            level="L1",
            task_mode="goal",
        )
    assert result == 0


def test_ask_user_keeps_requested_l2_level():
    builder = _load(ROOT / ".claude/scripts/plan_builder.py", "hardening_plan_builder")
    plan = builder.build_plan(
        {"decision": "ASK_USER", "level": "L1", "requested_level": "L2",
         "required_confirmations": ["scope"], "risk_level": "high"},
        "goal",
        "task",
    )
    assert plan.level == "L2"


def test_l2_intake_cannot_remain_light():
    carros = _load(ROOT / ".claude/scripts/carros_base.py", "hardening_carros_light")
    token = {"session": {"level": "L2"}, "task": {"mode": "light"}}
    assert not carros._is_l2_nonlight(token)
    assert carros._is_l2_nonlight({"session": {"level": "L2"}, "task": {"mode": "goal"}})


def test_feedback_marks_unavailable_jev_for_review(tmp_path):
    feedback = _load(ROOT / ".claude/scripts/jev_feedback.py", "hardening_feedback")
    checklist = tmp_path / "checklist.json"
    checklist.write_text(json.dumps({"summary": {"unavailable": ["rule-x"]}}), encoding="utf-8")
    result = feedback.emit_feedback(checklist, tmp_path / "out", "task", "S1")
    assert result["needs_review"] is True


def test_hook_merge_uses_declared_pretool_event_and_tolerates_bad_output(monkeypatch):
    launcher = _load(ROOT / ".claude/hooks/hook-launcher.py", "hardening_launcher")
    monkeypatch.setenv("HOOK_EVENT_TYPE", "PreToolUse")
    merged = launcher._merge_hook_results([
        ("carroros-night-deny.py", (2, {"continue": True, "hookSpecificOutput": None})),
        ("other.py", (1, {"continue": False, "hookSpecificOutput": "bad"})),
    ])
    assert merged["hookSpecificOutput"]["permissionDecision"] == "deny"
