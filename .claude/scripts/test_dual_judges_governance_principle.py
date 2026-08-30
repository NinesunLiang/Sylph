"""test_dual_judges_governance_principle.py — DUAL_JUDGES_README.md 治理哲学段存在性"""
from pathlib import Path

DOC = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts/DUAL_JUDGES_README.md")


def test_governance_principle_section_exists():
    """DUAL_JUDGES_README.md 应含治理哲学段。"""
    text = DOC.read_text()
    assert "## 7. 治理哲学" in text


def test_principle_states_diversion_and_fallback():
    """治理哲学段应明确"疏导 + 兜底"原则。"""
    text = DOC.read_text()
    assert "疏导" in text and "兜底" in text


def test_22_gates_breakdown_referenced():
    """治理哲学段应含 22 门分类数字。"""
    text = DOC.read_text()
    # 22 应在"治理哲学"段之后
    import re
    m = re.search(r"## 7\. 治理哲学.*?(?=^##\s)", text, re.DOTALL | re.MULTILINE)
    assert m, "未找到 ## 7 段范围"
    section = m.group(0)
    assert "22" in section, "## 7 段应含 22 数字"


def test_principle_links_to_full_doc():
    """治理哲学段应链到完整文档。"""
    text = DOC.read_text()
    assert "governance-philosophy.md" in text


def test_step_contract_mentioned():
    """应提及步骤交接契约（用户视角能看到的好处）。"""
    text = DOC.read_text()
    assert "consumes" in text.lower() or "produces" in text.lower()


def test_hook_error_fix_commits_mentioned():
    """应提及关键 bug 修复（让用户知道问题已解）。"""
    text = DOC.read_text()
    # 至少提到 hook error 修复 + 归档不卡
    assert "hook error" in text.lower() or "归档" in text