"""Red contracts for the final Goal/archive/hook hardening pass."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_jev_level_advisor_promotes_high_risk_and_falls_back_safely():
    carros = _load(ROOT / ".claude/scripts/carros_base.py", "final_goal_carros")
    assert carros._goal_level_from_intake("L2", "low", jev_verdict="ACCEPT") == "L2"
    assert carros._goal_level_from_intake("L1", "high", jev_verdict="UNAVAILABLE") == "L2"
    assert carros._goal_level_from_intake("L1", "low", jev_verdict="UNAVAILABLE") == "L1"


def test_archive_does_not_auto_complete_goal_terminal_step():
    text = (ROOT / ".claude/scripts/carros_base.py").read_text(encoding="utf-8")
    assert "archive_auto_completed_terminal_step" not in text
    assert "archive requires VERIFYING" in text or "Goal archive requires VERIFYING" in text


def test_deny_hook_timeout_and_spawn_errors_remain_nonzero(monkeypatch):
    launcher = _load(ROOT / ".claude/hooks/hook-launcher.py", "final_goal_launcher")
    monkeypatch.setenv("HOOK_EVENT_TYPE", "PreToolUse")
    hook_path = ROOT / ".claude/hooks/carroros-night-deny.py"
    monkeypatch.setattr(launcher.os.path, "isfile", lambda path: str(path) == str(hook_path))
    monkeypatch.setattr(launcher.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(launcher.subprocess.TimeoutExpired("x", 1)))
    rc, parsed = launcher._run_one_hook("carroros-night-deny.py", "", str(ROOT / ".claude/hooks"), str(ROOT), os.environ.copy())
    assert rc != 0 and parsed is None


def test_active_level_guards_have_no_l2_enhance_semantics():
    for path in (
        ROOT / ".claude/scripts/lib/oracle_gate_light.py",
        ROOT / ".claude/hooks/pretool_gates/checks.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "L2_ENHANCE" not in text
