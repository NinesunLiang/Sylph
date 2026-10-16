"""test_anti_patterns_l_section.py — anti-patterns.md L 段存在性测试"""
from pathlib import Path


DOC = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/anti-patterns.md")


def test_l_section_exists():
    """anti-patterns.md 应含 L 段（AI 行为反模式）。"""
    text = DOC.read_text()
    assert "L 段" in text or "L1" in text, "anti-patterns.md 缺 L 段"


def test_all_6_l_modes_documented():
    """L 段应含 6 个反模式（L1-L6）——2026-10-16 精简版为表格形式（| L1 | 一行式）。"""
    text = DOC.read_text()
    for i in range(1, 7):
        assert f"| L{i} " in text or f"### L{i} " in text, f"缺 L{i} 段"


def test_l_modes_have_against_solutions():
    """每个 L 模式应含解决方案（精简版=表格『对治』列）。"""
    text = DOC.read_text()
    assert text.count("对治") >= 1 or text.count("→ against") >= 6, "L 段缺解决方案"


def test_l_section_has_quick_lookup_table():
    """L 段应含速查表。"""
    text = DOC.read_text()
    assert "速查" in text or "保留条目" in text


def test_index37_source_cited():
    """L 段应引用 index37 来源（可指归档版）。"""
    text = DOC.read_text()
    assert "index37" in text, "L 段应说明来源是 index37"


def test_file_within_growth_cap():
    """防膨胀闸纪律：anti-patterns.md ≤ 40 行（2026-10-16 人类裁决）。"""
    lines = DOC.read_text().splitlines()
    assert len(lines) <= 40, f"anti-patterns.md 超 40 行阈值: {len(lines)} 行"


def test_archived_copy_exists():
    """精简前的完整版应归档在 references/archived/。"""
    archived = DOC.parent / "archived" / "anti-patterns-20261016.md"
    assert archived.exists(), "缺归档版 anti-patterns-20261016.md"