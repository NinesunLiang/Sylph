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
