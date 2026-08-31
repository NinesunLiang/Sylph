"""test_commit_soft_completion.py — 优化2 红测试

git commit -m "..." 应被软完成语检测（context 压力下 AI 写"all done"等绕过）。
不在 Bash 拦所有软完成语（误报高），仅对 git commit 拦截。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "pretool-gate.py"


def _run_hook(command: str) -> dict:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
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


def test_git_commit_with_soft_completion_redirected():
    """git commit -m 'all done' 应被 REDIRECT。"""
    r = _run_hook('git commit -m "all done, ready for review"')
    stderr = r.get("stderr", "")
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    assert decision == "ask" or "REDIRECT" in stderr or "soft_completion" in stderr, (
        f"git commit 软完成语未被拦。decision: {decision!r}, stderr: {stderr!r}"
    )


def test_git_commit_verified_real_passes():
    """git commit -m 'VERIFIED: ...' 不应误拦。"""
    r = _run_hook('git commit -m "VERIFIED: pytest tests/ → 3 passed"')
    stderr = r.get("stderr", "")
    assert "soft_completion" not in stderr.lower(), (
        f"误报：真 VERIFIED commit 被拦。stderr: {stderr!r}"
    )


def test_non_git_command_with_soft_completion_passes():
    """非 git commit 的命令（含软完成语）应放行（避免误报）。"""
    r = _run_hook('echo "all done"')
    stderr = r.get("stderr", "")
    assert "soft_completion" not in stderr.lower(), (
        f"误报：非 git 命令被拦。stderr: {stderr!r}"
    )


# index36 修复：状态污染——redirect-streak.json 是仓库级共享状态，先前测试/会话残留的
# commit-soft-completion streak（c≥4）会使 pretool-gate 升级为 redirect_limit_4（ASK_USER），
# 导致本测试断言"首触发应为 REDIRECT"失败。镜像 test_redirect_escalation_threshold.py
# 的清理模式：模块 setup/teardown 删除 streak 文件，保证每次独立红绿。
def _streak_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".omc" / "state" / "redirect-streak.json"


def setup_module(_module):
    try:
        if _streak_path().exists():
            _streak_path().unlink()
    except OSError:
        pass


def teardown_module(_module):
    try:
        if _streak_path().exists():
            _streak_path().unlink()
    except OSError:
        pass