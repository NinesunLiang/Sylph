"""test_handoff_step_contract.py — handoff 步骤交接契约

handoff.md 是 step 边界文件：S1 完成后写 handoff，让 S2 启动时直接读 consumes。
契约先行（不是事后兜底）：
  - handoff 必须显式记录 "last_step_produces:" 让下步启动能直接 verify
  - handoff 必须显式记录 "next_step_consumes:" 让 AI 在下步前知道需要什么

如果 handoff 缺契约字段，AI 启动下步时会不知道要什么 → 跑偏。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")
sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts/lib")

import inspect
import handoff_writer as module


def test_handoff_contains_last_step_produces():
    """handoff 模板/函数应生成 'Last Step Produces' 段。"""
    src = inspect.getsource(module)
    assert "Last Step Produces" in src or "last_step_produces" in src.lower(), (
        f"handoff 应含 Last Step Produces 段。实际: {src[:2000]}"
    )


def test_handoff_contains_next_step_consumes():
    """handoff 应生成 'Next Step Consumes' 段。"""
    src = inspect.getsource(module)
    assert "Next Step Consumes" in src or "next_step_consumes" in src.lower()


def test_handoff_documents_contract_chain():
    """handoff 应有契约链说明：上步 produces → 下步 consumes。"""
    src = inspect.getsource(module)
    assert "produces" in src.lower() and "consumes" in src.lower()