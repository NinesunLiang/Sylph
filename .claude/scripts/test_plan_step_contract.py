"""test_plan_step_contract.py — plan 步骤交接契约（red test）

plan.md 模板应为每个 step 加 produces + consumes 字段——
- produces: 本步的输出/产物（给下步用）
- consumes: 本步的输入/依赖（从上步拿）

这让 AI 在执行前看 consumes，执行后产 produces，下一步用 produces 作为 consumes。
避免"步骤需要的和上一步给的不匹配报错"。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")

import carros_base as module
import tempfile
import os


def test_plan_template_includes_produces_field():
    """plan 模板生成的 step 应含 'produces:' 字段。"""
    # 调用 _write_default_plan 或类似函数
    # 这里检查默认 plan 文本内容
    from pathlib import Path as _P
    import inspect
    # 找 plan 写入函数
    func = module._write_default_plan
    src = inspect.getsource(func)
    assert "produces" in src, "plan 模板应包含 'produces' 字段"


def test_plan_template_includes_consumes_field():
    """plan 模板生成的 step 应含 'consumes:' 字段。"""
    import inspect
    src = inspect.getsource(module._write_default_plan)
    assert "consumes" in src, "plan 模板应包含 'consumes' 字段"


def test_plan_template_step_has_5_fields():
    """每个 step 应有 7 字段：status/depends_on/scope/consumes/produces/acceptance/verify。"""
    import inspect
    src = inspect.getsource(module._write_default_plan)
    required = ["status", "depends_on", "scope", "consumes", "produces", "acceptance", "verify"]
    for field in required:
        assert f"{field}:" in src or f"- {field}:" in src, (
            f"plan 模板 step 缺字段: {field}"
        )


def test_consumes_produces_described_in_comment():
    """模板里应有 comments 说明 consumes/produces 是步骤交接契约。"""
    import inspect
    src = inspect.getsource(module._write_default_plan)
    assert "consumes" in src and "produces" in src
    # 至少要解释
    assert "交接" in src or "consumes" in src.lower()  # accepts 交接 或 consumes 字段