"""index49 S4：完备模式**前置** TDD 门 —— 依赖树全绿 + 特性全红。

人类要求：开发前，依赖树 TDD 全绿（地基可用）、特性 TDD 全红（测试确实在测未实现行为）。
判据来自 plan.md 声明的 `dep_tdd_cmd` / `feature_tdd_cmd`。简易模式（L1）no-op。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("lx_goal_g49", SKILL_DIR / "lx-goal.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("lx_goal_g49", mod)
    spec.loader.exec_module(mod)
    return mod


PLAN_WITH_CMDS = """# Plan

## 依赖树

- D1 `foo.py` -> 被 S2 依赖

## Phase 1

- [ ] S1: 做点事
  - dep_tdd_cmd: exit 0
  - feature_tdd_cmd: exit 1
"""

PLAN_WITHOUT_CMDS = "# Plan\n\n## 依赖树\n\n- D1 x\n\n## Phase 1\n\n- [ ] S1: y\n"


def test_extract_tdd_commands():
    mod = _load()
    cmds = mod.extract_tdd_commands(PLAN_WITH_CMDS)
    assert cmds["dep_tdd_cmd"] == "exit 0"
    assert cmds["feature_tdd_cmd"] == "exit 1"


def test_extract_returns_empty_when_absent():
    mod = _load()
    assert mod.extract_tdd_commands(PLAN_WITHOUT_CMDS) == {}


# ── 前置门：依赖树须绿、特性须红 ──

def test_pretdd_pass_when_dep_green_feature_red():
    mod = _load()
    ok, detail = mod.evaluate_pretdd({"dep_exit": 0, "feature_exit": 1})
    assert ok, detail


def test_pretdd_fail_when_dep_red():
    mod = _load()
    ok, detail = mod.evaluate_pretdd({"dep_exit": 1, "feature_exit": 1})
    assert not ok and "依赖树" in detail, detail


def test_pretdd_fail_when_feature_green():
    """特性 TDD 若已绿，说明测试没在测新东西（无效测试）→ 必须拒绝。"""
    mod = _load()
    ok, detail = mod.evaluate_pretdd({"dep_exit": 0, "feature_exit": 0})
    assert not ok and "特性" in detail, detail


def test_pretdd_fail_when_feature_missing():
    mod = _load()
    ok, detail = mod.evaluate_pretdd({"dep_exit": 0, "feature_exit": None})
    assert not ok, detail


# ── 门在生命周期中的位置（2026-10-24 修复）──
# 判据写在 plan.md，而 plan.md 在 phase0-done 之后才填写。
# 因此前置门只能挂在 plan-done（进入 EXECUTING 前），不能挂在 phase0-done。

RESEARCH_OK = (
    "# Research\n\n## 背景\n真实背景。\n\n## 约束\n本地约束。\n\n"
    "## 已知信息\n已知事实。\n\n## 不确定性\n待验证边界。\n\n"
    "## 全貌\n完整调用链。\n\n## 依赖树\n- research → plan\n\n"
    "## 方案\n最小修复方案。\n\n## Dependency TDD\ncommand: pytest; exit_code: 0\n"
)

EXECUTOR_OK = (
    "# Executor\n\n## Conditions\n- tmp env\n\n## Key Changes\n- probe\n\n"
    "## Decisions\n- Rationale: probe\n\n## Acceptance Checklist\n- [ ] probe\n\n"
    "## TDD Evidence\n- Dependency TDD command: pytest -> exit 0\n"
)

PLAN_WITH_GATE_CMDS = (
    "# Plan\n\n## 依赖树\n- probe fixture\n\n"
    "## TDD 判据\n- dep_tdd_cmd: exit 0\n- feature_tdd_cmd: exit 1\n\n"
    "## Phase 1\n- [ ] S1: probe step\n"
    "  - depends_on: none\n  - scope: probe\n"
    "  - acceptance: probe passes\n  - verify: command:pytest\n"
)


def _lifecycle_ctx(tmp_path, monkeypatch, plan_text: str):
    import json

    date = "20260812"
    plan_dir = tmp_path / "tasks" / date / "probe-task"
    plan_dir.mkdir(parents=True)
    (plan_dir / "research.md").write_text(RESEARCH_OK, encoding="utf-8")
    (plan_dir / "plan.md").write_text(plan_text, encoding="utf-8")
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
            "goal": {"state": "CLARIFY", "description": "gate position"},
            "stats": {"done": 0, "total": 1},
            "task": {"current_step": None, "status": "planning"},
        }),
        encoding="utf-8",
    )

    mod = _load()
    monkeypatch.setattr(mod, "TOKENS_DIR", tokens)
    monkeypatch.setattr(mod, "TASKS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(mod, "PLANS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(mod, "CURRENT_PLAN_DIR", plan_dir.resolve())
    monkeypatch.setattr(mod, "enter_isolation_if_complete", lambda *a, **k: {})
    return mod, plan_dir, token_path


def _state(token_path: Path) -> str:
    import json

    return json.loads(token_path.read_text(encoding="utf-8"))["goal"]["state"]


def test_phase0_done_does_not_require_tdd_commands(tmp_path, monkeypatch, capsys):
    """研究阶段 plan.md 还是空骨架，前置门不得在此拦截。"""
    mod, _plan_dir, token_path = _lifecycle_ctx(tmp_path, monkeypatch, PLAN_WITHOUT_CMDS)
    mod.cmd_phase0_done()  # 不应抛 SystemExit
    assert _state(token_path) == "PLANNING"
    # 完成即告知下一步入参（事前强调，不靠事后报错）
    assert "下一步：plan-done" in capsys.readouterr().out


def test_plan_done_enforces_pretdd_gate(tmp_path, monkeypatch):
    """plan.md 缺判据 → 停在 PLANNING，不进入执行态。"""
    import pytest

    mod, _plan_dir, token_path = _lifecycle_ctx(tmp_path, monkeypatch, PLAN_WITHOUT_CMDS)
    mod.cmd_phase0_done()
    with pytest.raises(SystemExit) as exc:
        mod.cmd_plan_done()
    assert exc.value.code == 1
    assert _state(token_path) == "PLANNING"


def test_plan_done_passes_when_tdd_commands_declared(tmp_path, monkeypatch):
    """判据齐全（依赖绿 + 特性红）→ plan-done 正常进入 EXECUTING。"""
    mod, _plan_dir, token_path = _lifecycle_ctx(tmp_path, monkeypatch, PLAN_WITH_GATE_CMDS)
    mod.cmd_phase0_done()
    mod.cmd_plan_done()
    assert _state(token_path) == "EXECUTING"
