"""command: 证据必须真执行（TDD / RED 先行）。

背景：`carros_base.py` 的计划模板承诺「command 规则由 VerifyGate 真实执行」，
但旧实现只把 AI 自述的 `source` / `output_tail` 当证据。本测试锁死新契约：
  1. 白名单命令 → 真跑，exit=0 才算通过
  2. exit≠0 → 直接失败，不再看自述
  3. shell 元字符 / 非白名单 → 不执行，回退旧的证据匹配（保持兼容）
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import verify_gate as vg  # noqa: E402


def test_allowed_command_really_runs():
    code, out = vg._execute_verify_command("python3 -m pytest --version")
    assert code == 0, f"pytest --version 应 exit=0, got {code}: {out}"
    assert out.strip()


def test_non_whitelisted_command_is_not_executed():
    code, reason = vg._execute_verify_command("rm -rf /tmp/never-exist-carror")
    assert code is None
    assert "whitelist" in reason or "unsafe" in reason


def test_shell_metacharacters_are_rejected():
    code, reason = vg._execute_verify_command(
        "python3 -m pytest -q; rm -rf /tmp/never-exist-carror"
    )
    assert code is None
    assert reason


def test_command_rule_passes_by_real_execution():
    ok, reason, _ = vg.match_verify_rule("command: python3 -m pytest --version", [])
    assert ok is True
    assert "executed" in reason


def test_command_rule_fails_on_nonzero_exit():
    ok, reason, _ = vg.match_verify_rule(
        "command: python3 -m pytest --definitely-not-a-real-flag", []
    )
    assert ok is False
    assert "failed" in reason


def test_sandbox_env_strips_secrets():
    env = vg._sandbox_env({
        "PATH": "/bin", "FOO": "bar",
        "OPENROUTER_API_KEY": "x", "DEEPSEEK_API_KEY": "y",
        "ANTHROPIC_AUTH_TOKEN": "z",
    })
    assert env["PATH"] == "/bin"
    assert env["FOO"] == "bar"
    assert "OPENROUTER_API_KEY" not in env
    assert "DEEPSEEK_API_KEY" not in env
    assert "ANTHROPIC_AUTH_TOKEN" not in env


def test_safe_python_c_is_allowed():
    code, out = vg._execute_verify_command(
        'python3 -c "import json;print(json.dumps({\'a\':1}))"'
    )
    assert code == 0, out


def test_python_c_with_os_import_is_rejected():
    code, reason = vg._execute_verify_command(
        'python3 -c "import os;os.system(\'echo hi\')"'
    )
    assert code is None
    assert "unsafe_python_c" in reason


def test_python_c_with_write_mode_is_rejected():
    code, reason = vg._execute_verify_command(
        'python3 -c "open(\'/tmp/x\',\'w\').write(\'x\')"'
    )
    assert code is None
    assert "unsafe_python_c" in reason


def test_cd_inside_repo_is_allowed():
    code, out = vg._execute_verify_command(
        "cd .claude/scripts && python3 -m pytest --version"
    )
    assert code == 0, out


def test_cd_outside_repo_is_rejected():
    code, reason = vg._execute_verify_command(
        "cd ~/Desktop && python3 -m pytest --version"
    )
    assert code is None
    assert "outside_repo" in reason or "unsupported" in reason


def test_non_whitelisted_command_falls_back_to_evidence():
    evidence = [{
        "type": "test",
        "source": "make check",
        "exit_code": 0,
        "evidence_level": "E3",
    }]
    ok, reason, _ = vg.match_verify_rule("command: make check", evidence)
    assert ok is True
    assert "made check" not in reason.lower()  # 走的是证据匹配分支
