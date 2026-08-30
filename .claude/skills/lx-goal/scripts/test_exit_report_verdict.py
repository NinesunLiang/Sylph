"""test_exit_report_verdict.py — 优化3 红测试

exit-report (goal-report.md) 必须含 verdict schema 必需字段：
- status: pass | blocked | warn | incomplete
- confidence: high | medium | low (E2 幻觉守卫)

校验函数 _validate_exit_report_verdict 缺失 → 现有 cmd_done 不会检查。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _validate_exit_report_verdict(report_path) -> tuple[bool, list[str]]:
    """优化3：exit-report 必须含 verdict schema 必需字段。"""
    from pathlib import Path as _P
    path = _P(report_path)
    if not path.exists():
        return False, ["exit-report not found"]
    text = path.read_text(encoding="utf-8")
    errors = []
    import re as _re
    # status 字段（允许 **加粗**、空格、中英冒号）
    if not _re.search(r"\*\*status\*\*[：:]\s*(pass|blocked|warn|incomplete)\b",
                     text, _re.IGNORECASE):
        errors.append("Missing or invalid 'status' field (must be pass/blocked/warn/incomplete)")
    # confidence 字段
    if not _re.search(r"\*\*confidence\*\*[：:]\s*(high|medium|low)\b",
                     text, _re.IGNORECASE):
        errors.append("Missing or invalid 'confidence' field (must be high/medium/low)")
    return (not errors), errors


def test_valid_exit_report_passes():
    """含 status + confidence 的报告应通过。"""
    import tempfile
    report = """# Exit Report

## Verdict
**status**: pass
**confidence**: high

其他内容...
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(report)
        p = Path(f.name)
    try:
        ok, errors = _validate_exit_report_verdict(p)
        assert ok, f"应通过。errors: {errors}"
    finally:
        p.unlink()


def test_missing_status_fails():
    """缺 status 应失败。"""
    import tempfile
    report = """# Exit Report

**confidence**: high
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(report)
        p = Path(f.name)
    try:
        ok, errors = _validate_exit_report_verdict(p)
        assert not ok, "缺 status 应失败"
        assert any("status" in e.lower() for e in errors)
    finally:
        p.unlink()


def test_missing_confidence_fails():
    """缺 confidence 应失败。"""
    import tempfile
    report = """# Exit Report

**status**: pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(report)
        p = Path(f.name)
    try:
        ok, errors = _validate_exit_report_verdict(p)
        assert not ok, "缺 confidence 应失败"
        assert any("confidence" in e.lower() for e in errors)
    finally:
        p.unlink()


def test_invalid_status_fails():
    """无效 status 值应失败。"""
    import tempfile
    report = """# Exit Report

**status**: maybe
**confidence**: high
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(report)
        p = Path(f.name)
    try:
        ok, errors = _validate_exit_report_verdict(p)
        assert not ok, "无效 status 应失败"
    finally:
        p.unlink()