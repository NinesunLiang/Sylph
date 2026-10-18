"""测试隔离：hook 不得把审计/重定向状态写进真实治理目录。

背景（2026-10-18）：测试 spawn 的 hook 曾写入 119 条真实审计事件，
把「人本」指标污染成 2.55。修复方式是环境变量隔离。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent


def test_conftest_sets_isolation_env():
    assert os.environ.get("CARROROS_AUDIT_DIR"), "conftest 必须设置审计隔离目录"
    assert os.environ.get("CARROROS_REDIRECT_STREAK"), "conftest 必须设置重定向状态隔离路径"


def test_constants_honor_audit_env(tmp_path):
    audit = tmp_path / "audit"
    streak = tmp_path / "streak.json"
    env = os.environ.copy()
    env["CARROROS_AUDIT_DIR"] = str(audit)
    env["CARROROS_REDIRECT_STREAK"] = str(streak)
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(HOOKS)!r});"
        "import pretool_gates.constants as c;"
        "print(c.AUDIT);"
        "print(c.REDIRECT_STREAK)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert lines[0] == str(audit), f"审计目录未跟随环境变量: {lines[0]}"
    assert lines[1] == str(streak), f"重定向状态未跟随环境变量: {lines[1]}"
