"""test_executor_step_contract.py — executor 步骤交接契约

executor.md 是 step 内证据账簿。EV 块应显式含 consumes + produces 字段。
- consumes: 步骤起点（来自 plan.S1.consumes 或上步 produces）
- produces: 步骤输出（plan.S1.produces 内容 + 实际产物描述）

契约先行：AI 写 EV 块时必须先填 consumes 确认输入到位，再填 produces 输出。
如果 consumes 字段空 → 步骤没做契约握手 → 验证应失败。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")

import inspect
import carros_base as module


def test_executor_template_has_consumes_field():
    """executor EV 块模板应含 consumes 字段。"""
    src = inspect.getsource(module._write_default_executor)
    assert "consumes:" in src, "executor EV 块模板应含 consumes 字段"


def test_executor_template_has_produces_field():
    """executor EV 块模板应含 produces 字段。"""
    src = inspect.getsource(module._write_default_executor)
    assert "produces:" in src, "executor EV 块模板应含 produces 字段"


def test_executor_template_documents_contract():
    """executor 模板应说明 consumes → produces 契约握手。"""
    src = inspect.getsource(module._write_default_executor)
    # 模板内有契约说明
    assert "契约" in src and "consumes" in src and "produces" in src


def test_executor_template_distinguishes_from_soft_completion():
    """executor 模板应明确 consumes/produces 是路径锁定（不是防错兜底）。"""
    src = inspect.getsource(module._write_default_executor)
    # 模板应强调"契约先行"
    assert "契约先行" in src or "路径锁定" in src or "防错兜底" in src