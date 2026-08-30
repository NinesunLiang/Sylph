"""test_governance_philosophy_doc.py — 治理哲学文档存在性测试"""
from pathlib import Path


def test_governance_philosophy_doc_exists():
    """治理哲学文档应存在 .claude/references/。"""
    p = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/governance-philosophy.md")
    assert p.exists(), f"治理哲学文档不存在: {p}"


def test_doc_has_principle_statement():
    """文档应含'疏导 + 兜底'原则声明。"""
    p = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/governance-philosophy.md")
    text = p.read_text()
    assert "疏导" in text and "兜底" in text


def test_doc_has_quantified_breakdown():
    """文档应含疏导/兜底比例（22 个门的分类）。"""
    p = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/governance-philosophy.md")
    text = p.read_text()
    # 至少要有 22 这个数字
    assert "22" in text


def test_doc_has_dont_rules():
    """文档应说明不应做什么（防错禁用场景）。"""
    p = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/governance-philosophy.md")
    text = p.read_text()
    # 不应纯防错
    assert "防错" in text
    assert "不应" in text or "禁用" in text
