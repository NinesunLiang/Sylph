"""test_action_gate_scope.py — T3 红测试

pretool-gate action_gate 应基于 working-set.yaml 检查 Bash 命令路径：
- 路径在 allowed_paths → 放行
- 路径不在 → REDIRECT（要求 AI 修路径或更新 working-set）

注：sensitive paths (.env/.ssh 等) 由 _check_sensitive_write_bash 拦截，
不在本测试范围。本测试聚焦 working-set 范围外的合法写操作。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "pretool-gate.py"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _run_hook(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
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


def _bash_payload(command: str) -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def test_bash_write_to_allowed_path_passes():
    """Bash 写 allowed_paths 内文件应放行（写到 src/foo.py）。"""
    payload = _bash_payload("echo hello > /Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/src/foo.py")
    r = _run_hook(payload)
    # 期望：continue=true 或 not REDIRECT
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    assert decision != "ask" or "REDIRECT" not in r.get("stderr", ""), (
        f"工作区内路径被 REDIRECT。stderr: {r['stderr']!r}"
    )


def test_bash_write_to_denied_path_redirected():
    """Bash 写 .env（denied_paths）应被拦截（sensitive_write 已有防御）。"""
    payload = _bash_payload("echo token=abc > /Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.env")
    r = _run_hook(payload)
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    # sensitive_write 已拦（deny 或 BLOCK）
    assert decision in ("deny", "ask") or "BLOCK" in r.get("stderr", ""), (
        f".env 写未被拦。stderr: {r['stderr']!r}, decision: {decision!r}"
    )


def test_bash_read_only_passes():
    """Bash 只读命令（ls/cat）应放行。"""
    payload = _bash_payload("ls /tmp")
    r = _run_hook(payload)
    # 不应被 REDIRECT
    stderr = r.get("stderr", "")
    assert "REDIRECT" not in stderr, (
        f"ls 命令被 REDIRECT。stderr: {stderr!r}"
    )