"""test_plan_dependency_tree_required.py — F2 红测试

L1/L2 任务的 plan.md 必须包含 '## 依赖树' 章节（中文 '依赖树' 或英文 'dependency tree'）。
缺失则 verify 不通过——依赖树是强制门禁，非软要求。
"""
from __future__ import annotations

from pathlib import Path
import sys

# 让 import carros_base 成功
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tempfile

from carros_base import _check_plan_has_dependency_tree


def test_plan_with_dependency_tree_passes():
    """含 '## 依赖树' 章节应通过。"""
    plan = """# Plan
## 依赖树
- a.py ← b.py
- b.py ← c.py

## Phase 1
- [ ] S1: ...
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(plan)
        plan_path = Path(f.name)
    try:
        ok, reason = _check_plan_has_dependency_tree(plan_path)
        assert ok, f"应通过。reason: {reason!r}"
    finally:
        plan_path.unlink()


def test_plan_without_dependency_tree_fails():
    """缺 '## 依赖树' 应失败。"""
    plan = """# Plan
## Phase 1
- [ ] S1: ...
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(plan)
        plan_path = Path(f.name)
    try:
        ok, reason = _check_plan_has_dependency_tree(plan_path)
        assert not ok, "缺依赖树应失败"
        assert "依赖树" in reason or "dependency" in reason.lower(), (
            f"失败原因应提及依赖树。reason: {reason!r}"
        )
    finally:
        plan_path.unlink()


def test_plan_with_english_dependency_tree_passes():
    """英文 'Dependency Tree' 也应识别。"""
    plan = """# Plan
## Dependency Tree
- a.py ← b.py

## Phase 1
- [ ] S1: ...
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(plan)
        plan_path = Path(f.name)
    try:
        ok, reason = _check_plan_has_dependency_tree(plan_path)
        assert ok, f"应通过。reason: {reason!r}"
    finally:
        plan_path.unlink()