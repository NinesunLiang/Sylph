"""test_sandbox_long_task_doc.py — 沙箱长任务模式文档存在性"""
from pathlib import Path

DOC = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/sandbox-long-task-pattern.md")


def test_doc_exists():
    assert DOC.exists(), f"沙箱长任务文档不存在: {DOC}"


def test_doc_contains_5_modes():
    """文档应含 5 个模式（分批 / 后台 / 轮询 / 分阶段 / 异步）。"""
    text = DOC.read_text()
    for mode in ["分批 sleep", "后台运行", "轮询代替", "分阶段任务", "异步 + 短轮询"]:
        assert mode in text, f"缺模式: {mode}"


def test_doc_has_timeout_limits_table():
    """文档应含沙箱超时限制表。"""
    text = DOC.read_text()
    assert "Claude Code" in text and "DSH" in text
    assert "60 秒" in text or "120 秒" in text


def test_doc_has_judgment_table():
    """文档应含"操作类型 → 时长 → 做法"判断表。"""
    text = DOC.read_text()
    assert "单次 Bash 持续时长预估" in text or "通常时长" in text


def test_doc_has_anti_patterns():
    """文档应含"反模式"段。"""
    text = DOC.read_text()
    assert "反模式" in text


def test_doc_linked_in_references_index():
    """文档应在 references/index.md 中可发现。"""
    index = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/references/index.md")
    text = index.read_text()
    assert "sandbox-long-task-pattern.md" in text, "未在 references/index.md 中索引"