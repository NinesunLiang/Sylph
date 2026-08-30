"""test_soft_completion_in_posttool.py — T1 红测试

posttool-claim-audit 应检测 Edit/Write 内容中的软完成语（context 压力下 AI 自夸）。
测试用真 hook（stdin JSON）跑，验证软完成语触发 warn。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "posttool-claim-audit.py"


def _run_hook(payload: dict) -> dict:
    """Run posttool-claim-audit with given payload, return parsed JSON + stderr."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    out = (proc.stdout or "").strip()
    lines = [l for l in out.splitlines() if l.strip().startswith("{")]
    result = {}
    if lines:
        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError:
            pass
    # 关键：把 stderr 也带回（软完成语检测走 stderr）
    result["stderr"] = proc.stderr or ""
    result["raw_stdout"] = out
    return result


def _payload(content: str, file_path: str = "/tmp/test-doc.md") -> dict:
    return {
        "tool_name": "Write",
        "tool_input": {
            "file_path": file_path,
            "content": content,
        },
    }


def test_soft_completion_looks_good_triggers_warn():
    """Edit/Write 内容含"看起来没问题了"应触发软完成语 warn。"""
    payload = _payload(
        "## 修复报告\n\n看起来没问题了，可以发布。\n",
        file_path="/tmp/foo-doc.md",
    )
    result = _run_hook(payload)
    stderr = result.get("stderr", "")
    assert "soft_completion" in stderr.lower() or "软完成" in stderr, (
        f"软完成语未触发 warn。stderr: {stderr!r}"
    )


def test_soft_completion_basically_done_triggers_warn():
    """Edit/Write 内容含 'basically done' 应触发。"""
    payload = _payload(
        "## Status\n\nBasically done, just minor cleanup.\n",
        file_path="/tmp/foo-doc.md",
    )
    result = _run_hook(payload)
    stderr = result.get("stderr", "")
    assert "soft_completion" in stderr.lower() or "软完成" in stderr, (
        f"basically done 未触发。stderr: {stderr!r}"
    )


def test_no_soft_completion_passes_silently():
    """不含软完成语的内容不应误报。"""
    payload = _payload(
        "## 修复报告\n\n已修复问题：用户认证 token 过期 → 加 refresh 逻辑。\n"
        "VERIFIED: pytest tests/test_auth.py → 3 passed\n",
        file_path="/tmp/foo-doc.md",
    )
    result = _run_hook(payload)
    stderr = result.get("stderr", "")
    assert "soft_completion" not in stderr.lower(), (
        f"误报：正常 VERIFIED 内容被当成软完成。stderr: {stderr!r}"
    )