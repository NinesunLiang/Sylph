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


def test_hook_rc_is_visible_as_ask(monkeypatch):
    """D-033（2026-10-24 人类裁决）：钩子故障 rc≠0 不再 deny，改成 ask 让人选择。"""
    monkeypatch.setenv("HOOK_EVENT_TYPE", "PreToolUse")
    launcher = _load_launcher()
    merged = launcher._merge_hook_results([
        ("carroros-night-deny.py", (2, {
            "continue": True,
            "hookSpecificOutput": {"hookEventName": "PreToolUse"},
        }))
    ])
    assert merged["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert merged["continue"] is True


def test_missing_critical_hook_asks_instead_of_blocking(monkeypatch, tmp_path):
    """复现 2026-10-24 事故：找不到 hook-launcher 时 python 退出码 2 被当成阻断。

    D-033：基础设施故障必须 rc=0 + ask，绝不能让 CC 拦下用户输入。
    """
    monkeypatch.setenv("HOOK_EVENT_TYPE", "PreToolUse")
    launcher = _load_launcher("hook_launcher_missing")
    import os
    rc, payload = launcher._run_one_hook(
        "pretool-gate.py", "", str(tmp_path), str(tmp_path), os.environ.copy())
    assert rc == 0
    assert payload["hookSpecificOutput"]["permissionDecision"] == "ask"
