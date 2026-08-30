"""test_plan_done_strict.py — 优化1 红测试

plan-done 应严格化：
1. plan.md 必须含 '## 依赖树' 章节（F2 同步到 lx-goal）
2. plan.md 必须含依赖关系声明（depends_on 不全为 none）
3. cmd_done 时 verdict schema 必须含 status + confidence 字段
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tempfile
from goal_contracts import PlanGate, PlanGateError


def test_plan_without_dependency_tree_fails():
    """PlanGate 应检测 plan.md 缺 '## 依赖树' 章节。"""
    plan = """# Plan
## Phase 1
- [ ] S1:foo:
  - depends_on: none
  - scope: foo
  - acceptance: ok
  - verify: command: pytest foo.py
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(plan)
        p = Path(f.name)
    try:
        try:
            PlanGate.validate(p)
            ok = True
        except PlanGateError:
            ok = False
        assert not ok, "PlanGate 应检测缺依赖树章节"
    finally:
        p.unlink()


def test_plan_with_dependency_tree_passes():
    """含 '## 依赖树' 应通过。"""
    plan = """# Plan
## 依赖树
- a.py ← b.py

## Phase 1
- [ ] S1:foo:
  - depends_on: none
  - scope: foo
  - acceptance: ok
  - verify: command: pytest foo.py
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(plan)
        p = Path(f.name)
    try:
        result = PlanGate.validate(p)
        assert result.get("valid", True)
    finally:
        p.unlink()


def test_plan_with_english_dependency_tree_passes():
    """英文 '## Dependency Tree' 也应通过。"""
    plan = """# Plan
## Dependency Tree
- a.py <- b.py

## Phase 1
- [ ] S1:foo:
  - depends_on: none
  - scope: foo
  - acceptance: ok
  - verify: command: pytest foo.py
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(plan)
        p = Path(f.name)
    try:
        result = PlanGate.validate(p)
        assert result.get("valid", True)
    finally:
        p.unlink()