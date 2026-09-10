"""index49 S3：goal 分级入口（L1 简易 / L2 完备）。

人类要求：
  - L1 走**简易模式**：只需必要项（现状轻量化路径）
  - L2 走**完备模式**：worktree 隔离 + 依赖树 + 前置/后置 TDD 门 + 双法官验收

变更点：`lx-goal.py` 原先把 `--level L2` **写死**传给 carros_base（见 cmd_on），
无分级入口。本步引入 `on --level L1|L2`，默认 L1（与「默认 L1」的既有裁决一致），
并给出可测的纯函数契约。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("lx_goal_l49", SKILL_DIR / "lx-goal.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("lx_goal_l49", mod)
    spec.loader.exec_module(mod)
    return mod


def test_default_level_is_l1():
    mod = _load()
    goal, expiry, task_id, level = mod.parse_on_args(["帮我优化性能"])
    assert level == "L1", f"缺省应为 L1（简易），实际 {level}"


def test_explicit_l2_is_honored():
    mod = _load()
    goal, expiry, task_id, level = mod.parse_on_args(["做一件复杂的事", "--level", "L2"])
    assert level == "L2"
    assert goal == "做一件复杂的事"


def test_explicit_l1_is_honored():
    mod = _load()
    _g, _e, _t, level = mod.parse_on_args(["小修一下", "--level", "L1"])
    assert level == "L1"


def test_unknown_level_is_rejected():
    mod = _load()
    with pytest.raises(ValueError):
        mod.parse_on_args(["做事", "--level", "L9"])


def test_level_without_value_is_rejected():
    mod = _load()
    with pytest.raises(ValueError):
        mod.parse_on_args(["做事", "--level"])


def test_existing_options_still_parse():
    mod = _load()
    goal, expiry, task_id, level = mod.parse_on_args(
        ["目标描述", "--task-id", "my-task", "--expiry", "3", "--level", "L2"])
    assert (goal, expiry, task_id, level) == ("目标描述", 3, "my-task", "L2")


def test_complete_mode_predicate():
    """完备模式判定是唯一真源，供 worktree/门禁统一引用。"""
    mod = _load()
    assert mod.is_complete_mode("L2") is True
    assert mod.is_complete_mode("L1") is False
    assert mod.is_complete_mode("") is False


# ── worktree 接线（完备模式一定在 worktree 下）──

def test_l1_does_not_create_worktree(tmp_path):
    mod = _load()
    called = []
    out = mod.enter_isolation_if_complete(
        {"session": {"level": "L1"}}, tmp_path, create_worktree=lambda tid: called.append(tid))
    assert out == {}, f"简易模式不得建 worktree: {out}"
    assert called == []


def test_l2_creates_worktree_and_records(tmp_path):
    mod = _load()
    out = mod.enter_isolation_if_complete(
        {"session": {"level": "L2"}}, tmp_path,
        create_worktree=lambda tid: (tmp_path / f"wt-{tid}", f"branch-{tid}"))
    assert "worktree" in out and "worktree_branch" in out, out
    assert out["worktree_branch"].startswith("branch-")


def test_l2_idempotent_when_worktree_exists(tmp_path):
    mod = _load()
    called = []
    out = mod.enter_isolation_if_complete(
        {"session": {"level": "L2"}, "worktree": "/already/there", "worktree_branch": "b"},
        tmp_path, create_worktree=lambda tid: called.append(tid))
    assert out["worktree"] == "/already/there"
    assert called == [], "已有 worktree 时不得重复创建"


def test_level_reads_from_session_level_field(tmp_path):
    """level 来自 token.session.level（carros_base init --level 的落点）。"""
    mod = _load()
    out = mod.enter_isolation_if_complete(
        {"session": {"level": "l2"}}, tmp_path,
        create_worktree=lambda tid: (tmp_path / "w", "b"))
    assert out != {}, "小写 l2 也应判为完备模式"
