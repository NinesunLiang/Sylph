"""Regression tests for night-deny result propagation."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / ".claude/hooks/hook-launcher.py"


def _load_launcher(name: str = "hook_launcher_night_result"):
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_night_deny_rc_is_visible_as_deny(monkeypatch):
    monkeypatch.setenv("HOOK_EVENT_TYPE", "PreToolUse")
    launcher = _load_launcher()
    merged = launcher._merge_hook_results([
        ("carroros-night-deny.py", (2, {
            "continue": True,
            "hookSpecificOutput": {"hookEventName": "PreToolUse"},
        }))
    ])
    # This is a pure contract test. It is expected to fail until the launcher
    # maps the night hook's exit-2 result to a tool-level deny.
    assert merged["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert merged["continue"] is True
