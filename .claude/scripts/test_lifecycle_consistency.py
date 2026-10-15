"""Regression tests for the L1/L2 lifecycle contract."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_carros(name: str = "carros_lifecycle_consistency"):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / ".claude/scripts/carros_base.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_level_normalization_rejects_unknown_values():
    carros = _load_carros("carros_level_contract")
    with pytest.raises(ValueError, match="level"):
        carros.cmd_init(task_id="bad-level", level="L2_ENHANCE")


def test_goal_requires_l2_and_cannot_be_light(tmp_path):
    carros = _load_carros("carros_goal_contract")
    carros.OMC_TOKENS = tmp_path / "tokens"  # type: ignore[attr-defined]
    task_dir = tmp_path / "task"
    with pytest.raises(ValueError, match="L2"):
        carros.cmd_init(
            task_id="goal-l1",
            task_dir=str(task_dir),
            level="L1",
            task_mode="goal",
        )

    with pytest.raises(ValueError, match="light"):
        carros.cmd_init(
            task_id="goal-light",
            task_dir=str(tmp_path / "task-light"),
            level="L2",
            task_mode="goal",
            light=True,
        )


def test_l2_nonlight_accepts_only_verified():
    carros = _load_carros("carros_verify_contract")
    assert carros._verify_decision_allowed("L2", None, "VERIFIED")
    assert not carros._verify_decision_allowed("L2", None, "WARN")
    assert carros._verify_decision_allowed("L1", "light", "WARN")


def test_default_plan_contains_dependency_tree(tmp_path):
    carros = _load_carros("carros_plan_contract")
    carros.PLAN_PATH = tmp_path / "plan.md"  # type: ignore[attr-defined]
    carros._write_default_plan(["S1"])
    assert "## 依赖树" in carros.PLAN_PATH.read_text(encoding="utf-8")  # type: ignore[attr-defined]
