"""test_k1_extended_patterns.py — T2 红测试

K1 反模式（数值断言无来源）词表扩：context 压力下 AI 用模糊完成语
绕过检测。新词必须被检测到。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "posttool-claim-audit.py"


def _run_hook(content: str, file_path: str = "/tmp/foo-doc.md") -> dict:
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    result = {}
    lines = [l for l in (proc.stdout or "").splitlines() if l.strip().startswith("{")]
    if lines:
        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError:
            pass
    result["stderr"] = proc.stderr or ""
    return result


def test_completion_triggered_warn():
    """含 'all done' 应被软完成语扩展词表命中。"""
    content = "## Status\n\nAll done, ready for review.\n"
    r = _run_hook(content)
    assert "soft_completion" in r["stderr"].lower(), (
        f"all done 未被检测。stderr: {r['stderr']!r}"
    )


def test_fixed_triggered_warn():
    """含 'fixed it' 应被检测（context 压力下 AI 习惯用）。"""
    content = "## Bug fix\n\nFixed it.\n"
    r = _run_hook(content)
    assert "soft_completion" in r["stderr"].lower(), (
        f"fixed it 未被检测。stderr: {r['stderr']!r}"
    )


def test_verified_real_passes():
    """真有 VERIFIED 标记的不应被误报。"""
    content = (
        "## Fix\n\n"
        "VERIFIED: pytest tests/test_auth.py → 3 passed\n"
        "[已验证:src/auth.py:42] token 刷新逻辑已加\n"
    )
    r = _run_hook(content)
    # 不应被软完成语检测命中（VERIFIED 是真证据）
    assert "soft_completion" not in r["stderr"].lower(), (
        f"误报：真 VERIFIED 内容被当成软完成。stderr: {r['stderr']!r}"
    )