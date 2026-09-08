"""test_redirect_escalation_threshold.py — REDIRECT 升级阈值（index33 电池实证修复）

双法官共识#3：REDIRECT 升级阈值原为 >=4 过高，模型可无视多次 REDIRECT 不被硬停
（skip-tests ON 实测只触发 1 次即虚假完成）。
修复：阈值 4→2，2 次同门 REDIRECT 即升级为 redirect_limit 硬阻断。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent
HOOK = _HOOKS / "pretool-gate.py"
PROJECT_ROOT = _HOOKS.parent.parent
REDIRECT_STREAK = PROJECT_ROOT / ".omc" / "state" / "redirect-streak.json"

# 确定性触发 doc-reference REDIRECT 的 payload（F3 测试验证 carros_base.py 真被文档引用）
_PAYLOAD = {
    "tool_name": "Bash",
    "tool_input": {"command": "rm .claude/scripts/carros_base.py"},
}


def _setup():
    if REDIRECT_STREAK.exists():
        REDIRECT_STREAK.unlink()


def _teardown():
    if REDIRECT_STREAK.exists():
        REDIRECT_STREAK.unlink()


def _run() -> dict:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(_PAYLOAD),
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
    result["raw_stdout"] = proc.stdout or ""
    return result


def setup_module(_):
    _setup()


def teardown_module(_):
    _teardown()


def test_first_redirect_is_redirect_not_limit():
    """第 1 次同门 REDIRECT → 仍为 REDIRECT（不升级）。"""
    _setup()
    r = _run()
    combined = (r.get("stderr", "") + r.get("raw_stdout", "")).lower()
    assert "doc_reference" in combined, f"应触发 doc_reference REDIRECT, stderr: {r.get('stderr','')!r}"
    assert "redirect_limit" not in combined, f"第 1 次不应升级为 redirect_limit: {combined!r}"


def test_second_redirect_escalates_to_limit():
    """第 2 次同门 REDIRECT → 升级为 redirect_limit 硬阻断（阈值 2）。"""
    _setup()
    r1 = _run()  # streak=1
    assert "redirect_limit" not in (r1.get("stderr", "") + r1.get("raw_stdout", "")).lower()
    r2 = _run()  # streak=2 → cnt>=2 → 升级
    combined = (r2.get("stderr", "") + r2.get("raw_stdout", "")).lower()
    assert "redirect_limit" in combined, (
        f"第 2 次应升级为 redirect_limit_2, stderr: {r2.get('stderr','')!r}"
    )


def test_escalation_message_gives_stop_loop_and_actionable_out():
    """index44 R1：升级消息须明令停止重试并给出合规出路，防模型烧轮（skip-tests/doc-ref 教训）。"""
    _setup()
    _run()  # streak=1
    r2 = _run()  # streak=2 → 升级
    combined = r2.get("stderr", "") + r2.get("raw_stdout", "")
    assert "禁止继续重试" in combined, f"升级消息应明令停止重试: {combined!r}"
    # 可执行出路：F3 doc-reference 引导原文应被携带进升级消息
    assert "请先更新文档" in combined, f"升级消息应携带合规引导(可执行下一步): {combined!r}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
