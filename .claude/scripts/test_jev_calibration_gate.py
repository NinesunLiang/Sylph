"""test_jev_calibration_gate.py — 校准分级门（TDD / RED 先行）。

纪律（jev-eval 官方口径 + 零信任）：
  · 样本 <50（refuse）或 50–200（provisional）→ 判官只能给建议，**不得硬阻断**。
  · 只有 ≥200（ok）才允许在置信度达标时硬阻断。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

from jev_verify_loop import gate_decision  # noqa: E402


def test_refused_rule_never_blocks():
    assert gate_decision("不符合", 0.99, 0.85, "refuse") == "advice"


def test_provisional_rule_never_blocks():
    assert gate_decision("不符合", 0.99, 0.85, "provisional") == "advice"


def test_calibrated_rule_blocks_when_confident():
    assert gate_decision("不符合", 0.90, 0.85, "ok") == "block"


def test_calibrated_rule_advises_when_not_confident():
    assert gate_decision("不符合", 0.60, 0.85, "ok") == "advice"


def test_non_violation_always_passes():
    assert gate_decision("符合", 0.10, 0.85, "ok") == "pass"
    assert gate_decision("不适用", 0.10, 0.85, "refuse") == "pass"


def test_unknown_tier_is_conservative():
    assert gate_decision("不符合", 0.99, 0.85, "unknown") == "advice"
