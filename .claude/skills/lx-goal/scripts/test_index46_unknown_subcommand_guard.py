"""index46 S5 / PE-001 回归：未知子命令不得静默创建垃圾任务。

现象（2026-09-10 实证）：执行 `lx-goal.py tick --task-dir <path>` 时，`tick` 不是
已注册子命令，脚本不报错，而是把 `tick --task-dir <path>` 整串当作目标描述调用
`cmd_on`，静默创建了垃圾任务目录与带 lock 的活跃 token。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SKILL_DIR = Path(__file__).resolve().parent


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lx_goal_mod", SKILL_DIR / "lx-goal.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bare_ascii_word_is_rejected_as_command(monkeypatch):
    """裸 ASCII 词（tick/verify/resume…）应报错退出，绝不建任务。"""
    mod = _load_module()
    called: list[tuple] = []
    monkeypatch.setattr(mod, "cmd_on", lambda *a, **k: called.append(a))
    monkeypatch.setattr(sys, "argv", ["lx-goal.py", "tick", "--task-dir", "/tmp/x"])

    with pytest.raises(SystemExit) as exc:
        mod.main()

    assert exc.value.code == 2
    assert called == [], "未知裸词不得触发 cmd_on"


def test_unknown_bare_word_prints_usage_and_exits_2(capsys, monkeypatch):
    """未知裸词：退出码 2 + stderr 给出用法指引；且不触碰任何建任务路径。"""
    mod = _load_module()
    called: list[tuple] = []
    monkeypatch.setattr(mod, "cmd_on", lambda *a, **k: called.append(a))
    monkeypatch.setattr(sys, "argv", ["lx-goal.py", "definitely-not-a-command"])

    with pytest.raises(SystemExit) as exc:
        mod.main()

    err = capsys.readouterr().err
    assert exc.value.code == 2
    assert called == []
    assert "on " in err, "应提示用 `on \"<目标描述>\"` 显式激活"


def test_multi_token_description_still_activates(monkeypatch):
    """保留自然语言入口：多词描述仍可自动激活（不破坏既有便利）。"""
    mod = _load_module()
    called: list[tuple] = []
    monkeypatch.setattr(mod, "cmd_on", lambda *a, **k: called.append(a))
    monkeypatch.setattr(sys, "argv", ["lx-goal.py", "帮我", "优化", "性能"])

    mod.main()

    assert len(called) == 1, "多词目标描述应仍走自动激活"


def test_cjk_single_word_still_activates(monkeypatch):
    """单个中文词（如「重构」）视为目标描述，不受裸词守卫影响。"""
    mod = _load_module()
    called: list[tuple] = []
    monkeypatch.setattr(mod, "cmd_on", lambda *a, **k: called.append(a))
    monkeypatch.setattr(sys, "argv", ["lx-goal.py", "重构"])

    mod.main()

    assert len(called) == 1
