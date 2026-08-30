"""test_anti_patterns_l_section.py — anti-patterns.md L 段存在性测试"""
from pathlib import Path


DOC = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/anti-patterns.md")


def test_l_section_exists():
    """anti-patterns.md 应含 L 段（AI 行为反模式）。"""
    text = DOC.read_text()
    assert "## L. AI 行为反模式" in text, "anti-patterns.md 缺 L 段"


def test_all_6_l_modes_documented():
    """L 段应含 6 个反模式（L1-L6）。"""
    text = DOC.read_text()
    for i in range(1, 7):
        assert f"### L{i} " in text, f"缺 L{i} 段"


def test_l_modes_have_against_solutions():
    """每个 L 模式应含 '→ against' 解决方案段。"""
    text = DOC.read_text()
    assert text.count("→ against") >= 6, f"L 段 → against 段数: {text.count('→ against')}"


def test_l_section_has_quick_lookup_table():
    """L 段应含速查表。"""
    text = DOC.read_text()
    assert "模式速查表" in text


def test_index37_source_cited():
    """L 段应引用 index37 来源。"""
    text = DOC.read_text()
    assert "index37" in text, "L 段应说明来源是 index37"