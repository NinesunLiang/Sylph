"""test_action_gate_segments.py — index30 修复 TDD：危险命令复合命令绕过。

背景（index30 实测复现）：`cd /x && ... && git push --force` 等复合命令中段的
危险命令不命中 `^` 锚定模式 → 放行（真实发生了 force push 副作用）。
修复：按 ;/&&/||/|/换行 分段，每段做锚定匹配；引号内文本与注释不误伤。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pretool_gates.checks import _check_action_gate  # noqa: E402


def _bash(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


# ── 已拦截基线（不回归） ────────────────────────────────────────────────

def test_single_dangerous_still_blocked():
    for cmd in ("git push --force origin main", "rm -rf .", "sudo whoami"):
        r = _check_action_gate(_bash(cmd))
        assert r and r.startswith("BLOCK"), f"单条未拦: {cmd}"


def test_single_benign_still_allowed():
    for cmd in ("ls -la", "git log --oneline", "python3 -m pytest -q"):
        assert _check_action_gate(_bash(cmd)) is None, f"良性误拦: {cmd}"


# ── 复合命令中段（本次修复目标，先红） ─────────────────────────────────

def test_compound_middle_dangerous_blocked():
    cases = [
        "cd /tmp && git push --force origin main",
        "echo start; rm -rf .",
        "ls -la || sudo rm -rf /tmp/x",
        "python3 setup.py && chmod 777 /tmp/y",
        "git status | git push --force",
        "cd /x\ngit push --force origin main",
    ]
    for cmd in cases:
        r = _check_action_gate(_bash(cmd))
        assert r and r.startswith("BLOCK"), f"复合中段未拦: {cmd}"


# ── 不误伤（引号/注释/无危险） ─────────────────────────────────────────

def test_quoted_text_not_blocked():
    cases = [
        "echo \"git push --force\"",
        "echo 'rm -rf .'",
        "grep -r 'git push --force' docs/",
    ]
    for cmd in cases:
        assert _check_action_gate(_bash(cmd)) is None, f"引号内文本误拦: {cmd}"


def test_comment_only_not_blocked():
    cmd = "# git push --force origin main\nls"
    assert _check_action_gate(_bash(cmd)) is None


def test_benign_compound_not_blocked():
    cases = [
        "cd /tmp && ls -la",
        "echo a; echo b",
        "python3 -m pytest -q && git status",
    ]
    for cmd in cases:
        assert _check_action_gate(_bash(cmd)) is None, f"良性复合误拦: {cmd}"
