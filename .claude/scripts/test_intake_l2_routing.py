"""Regression tests for risk requests entering the L2 route."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_intake(name: str = "intake_l2_routing"):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".claude/scripts/intake_gate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_medium_risk_uses_l2_when_enhancement_is_available():
    intake = _load_intake()
    result = intake.run_intake("跨模块重构代码", enhance_available=True)
    assert result.decision == "L2"
    assert result.risk_level == "medium"


def test_high_risk_without_confirmation_uses_l2():
    intake = _load_intake("intake_high_risk")
    result = intake.run_intake("对外发布新版本", enhance_available=True)
    assert result.decision == "L2"
    assert result.risk_level == "high"
