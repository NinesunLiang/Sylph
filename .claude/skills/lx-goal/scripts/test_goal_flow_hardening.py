"""Goal 执行链硬化（2026-10-24）。

1. L2 收尾必须跑开发后 TDD（依赖 + 特性全绿）；双法官（accept）保持可选。
2. TDD 命令在项目根/worktree 执行，不再在任务文档目录内执行。
3. 无人值守防中断：剩余不足 1 小时且仍有 step 成功推进时顺延过期时间。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("lx_goal_hardening", SKILL_DIR / "lx-goal.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("lx_goal_hardening", mod)
    spec.loader.exec_module(mod)
    return mod


PLAN_TMPL = """# Plan

## 依赖树
- probe fixture

## TDD 判据
- dep_tdd_cmd: exit 0
- feature_tdd_cmd: {feature}

## Phase 1
- [x] S1: probe step
  - status: completed
  - depends_on: none
  - scope: probe
  - acceptance: probe passes
  - verify: command:pytest
"""

EXECUTOR_OK = """# Executor

## Conditions
- tmp env

## Key Changes
- probe

## Decisions
- Rationale: probe

## Acceptance Checklist
- [x] probe done

## TDD Evidence
- Dependency TDD command: pytest -> exit 0
- Regression TDD command: pytest -> exit 0

### EV-S1
- step: S1
- type: test
- evidence_level: E3
- source: probe
- exit_code: 0
- assertion: done
"""


def _done_ctx(tmp_path, monkeypatch, feature_cmd: str):
    mod = _load()
    date = "20260812"
    plan_dir = tmp_path / "tasks" / date / "probe-task"
    plan_dir.mkdir(parents=True)
    (plan_dir / "research.md").write_text("# Research\n\n## 依赖树\n- x\n", encoding="utf-8")
    (plan_dir / "plan.md").write_text(PLAN_TMPL.format(feature=feature_cmd), encoding="utf-8")
    (plan_dir / "executor.md").write_text(EXECUTOR_OK, encoding="utf-8")

    tokens = tmp_path / "tokens"
    token_path = tokens / date / "probe-task.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps({
            "schema_version": "v1.0",
            "revision": 0,
            "mode": "goal",
            "session": {"id": "probe-task", "level": "L2"},
            "task_dir": str(plan_dir.resolve()),
            "status": "active",
            "goal": {"state": "EXECUTING"},
            "stats": {"done": 1, "total": 1},
            "task": {"current_step": None, "status": "completed"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "TOKENS_DIR", tokens)
    monkeypatch.setattr(mod, "CURRENT_PLAN_DIR", plan_dir.resolve())
    return mod, plan_dir, token_path


def test_done_rejects_red_feature_tdd_for_l2(tmp_path, monkeypatch):
    """L2：特性测试仍红 = 实现没完成，拒绝归档。"""
    mod, plan_dir, token_path = _done_ctx(tmp_path, monkeypatch, "exit 1")
    with pytest.raises(SystemExit) as exc:
        mod.cmd_done(plan_dir)
    assert exc.value.code == 1
    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["goal"]["state"] == "EXECUTING"
    assert token.get("status") != "archived"


def test_done_archives_l2_when_tdd_green_without_accept(tmp_path, monkeypatch):
    """L2：两条 TDD 全绿即可归档；双法官（accept）不是必要条件。"""
    mod, plan_dir, token_path = _done_ctx(tmp_path, monkeypatch, "exit 0")
    mod.cmd_done(plan_dir)
    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["goal"]["state"] == "ARCHIVED"
    assert token["status"] == "archived"
    assert not (plan_dir / "state" / "judge-verdict.json").exists()


def _plan_dir_for_run(tmp_path: Path) -> Path:
    plan_dir = tmp_path / "tasks" / "20260812" / "run-dir"
    plan_dir.mkdir(parents=True)
    for name in ("plan.md", "research.md", "executor.md"):
        (plan_dir / name).write_text("# x\n", encoding="utf-8")
    return plan_dir


def test_tdd_commands_run_from_project_root(tmp_path, monkeypatch):
    """没有 worktree 时，TDD 命令必须在项目根目录执行（不是在任务文档目录）。"""
    mod = _load()
    seen: list[str] = []

    class _Proc:
        returncode = 0

    def fake_run(cmd, **kwargs):
        seen.append(str(kwargs.get("cwd")))
        return _Proc()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    plan_dir = _plan_dir_for_run(tmp_path)
    monkeypatch.setattr(mod, "CURRENT_PLAN_DIR", plan_dir.resolve())

    mod.run_tdd_commands(plan_dir, {"dep_tdd_cmd": "echo probe"})

    assert seen == [str(mod.PROJECT_ROOT)]


def test_tdd_commands_prefer_worktree(tmp_path, monkeypatch):
    """完备模式记录了 worktree 时，TDD 命令在 worktree 内执行。"""
    mod = _load()
    seen: list[str] = []

    class _Proc:
        returncode = 0

    def fake_run(cmd, **kwargs):
        seen.append(str(kwargs.get("cwd")))
        return _Proc()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    plan_dir = _plan_dir_for_run(tmp_path)
    worktree = tmp_path / "worktrees" / "wt"
    worktree.mkdir(parents=True)

    tokens = tmp_path / "tokens"
    token_path = tokens / "20260812" / "run-dir.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps({
            "mode": "goal",
            "task_dir": str(plan_dir),
            "worktree": str(worktree),
            "worktree_branch": "task-isolated-x",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "TOKENS_DIR", tokens)
    monkeypatch.setattr(mod, "CURRENT_PLAN_DIR", plan_dir.resolve())

    mod.run_tdd_commands(plan_dir, {"dep_tdd_cmd": "echo probe"})

    assert seen == [str(worktree)]


def _goal_with_expiry(minutes: int) -> dict:
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return {"goal": {"expires_at": expires.isoformat()}}


def test_renew_extends_when_less_than_one_hour_left(monkeypatch):
    mod = _load()
    writes: list[dict] = []
    monkeypatch.setattr(mod, "_write_mode_file", lambda data, path: writes.append(dict(data)))

    data = _goal_with_expiry(30)
    mod._renew_goal_expiry(data, "token.json")

    assert len(writes) == 1
    renewed = datetime.fromisoformat(data["goal"]["expires_at"])
    assert renewed > datetime.now(timezone.utc) + timedelta(hours=5)


def test_renew_noop_when_plenty_of_time_left(monkeypatch):
    mod = _load()
    writes: list[dict] = []
    monkeypatch.setattr(mod, "_write_mode_file", lambda data, path: writes.append(dict(data)))

    data = _goal_with_expiry(5 * 60)
    before = data["goal"]["expires_at"]
    mod._renew_goal_expiry(data, "token.json")

    assert writes == []
    assert data["goal"]["expires_at"] == before


def test_renew_refuses_expired_goal(monkeypatch, capsys):
    """已过期不静默续命（fail-closed），必须人类重新激活。"""
    mod = _load()
    writes: list[dict] = []
    monkeypatch.setattr(mod, "_write_mode_file", lambda data, path: writes.append(dict(data)))

    data = _goal_with_expiry(-30)
    mod._renew_goal_expiry(data, "token.json")

    assert writes == []
    assert "已过期" in capsys.readouterr().err
