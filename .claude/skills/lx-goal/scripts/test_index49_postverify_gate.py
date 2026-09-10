"""index49 S5：完备模式**后置**门（依赖树与特性均须全绿）+ 双法官验收。

人类要求：开发后验证阶段，依赖树与特性 TDD 都要全绿；并通过双法官验收。
验收通过后自动合回发起分支（见 cmd_accept）。
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


# ── 后置门：两者均须绿 ──

def test_posttdd_pass_when_both_green():
    mod = _load()
    ok, detail = mod.evaluate_posttdd({"dep_exit": 0, "feature_exit": 0})
    assert ok, detail


def test_posttdd_fail_when_feature_red():
    mod = _load()
    ok, detail = mod.evaluate_posttdd({"dep_exit": 0, "feature_exit": 1})
    assert not ok and "特性" in detail, detail


def test_posttdd_fail_when_dep_red():
    mod = _load()
    ok, detail = mod.evaluate_posttdd({"dep_exit": 1, "feature_exit": 0})
    assert not ok and "依赖树" in detail, detail
