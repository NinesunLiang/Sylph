"""test_delete_doc_reference.py — F3 红测试

Delete 或 Bash rm 前应 grep .claude/references/ 与 README.md 等文档，
若有引用则 ASK_USER（文档可能被误删）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "pretool-gate.py"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REDIRECT_STREAK = PROJECT_ROOT / ".omc" / "state" / "redirect-streak.json"


def _setup_module():
    """测试开始前清空 redirect-streak，避免累积到上限触发 redirect_limit。"""
    if REDIRECT_STREAK.exists():
        REDIRECT_STREAK.unlink()


def _teardown_module():
    """测试结束后清理。"""
    if REDIRECT_STREAK.exists():
        REDIRECT_STREAK.unlink()


def _run_hook(payload: dict) -> dict:
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


def setup_module(_):
    _setup_module()


def teardown_module(_):
    _teardown_module()


def test_delete_script_with_doc_reference_redirects():
    """删除被文档引用的脚本应被 REDIRECT。"""
    # carros_base.py 被多个文档引用（实测：design-docs/14, INDEX.md, adr/0016）
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm .claude/scripts/carros_base.py"},
    }
    r = _run_hook(payload)
    stderr = r.get("stderr", "")
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    # F3 修复前：不被拦（F3 修复前 hook 不查文档引用）
    # F3 修复后：应 ASK
    assert decision == "ask" or "REDIRECT" in stderr or "doc_reference" in stderr, (
        f"删被文档引用的脚本未被拦。decision: {decision!r}, stderr: {stderr!r}"
    )


def test_delete_unreferenced_script_passes():
    """删除未被文档引用的脚本应放行（不误拦）。"""
    # content_writer.py 实测无引用（除 .claude/scripts/ 自身）
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm .claude/scripts/content_writer.py"},
    }
    r = _run_hook(payload)
    stderr = r.get("stderr", "")
    assert "doc_reference" not in stderr.lower(), (
        f"误报：未引用的脚本被拦。stderr: {stderr!r}"
    )