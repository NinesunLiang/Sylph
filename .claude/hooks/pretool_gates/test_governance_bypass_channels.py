"""冻结域的运行时不可绕过性（Bash 通道）。

治理文件 = 规则来源。AI 能写它，就等于能给自己松绑。
下面每条都是当前实现放行的写法；先红后绿。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))

from pretool_gates.checks import _check_governance_bypass  # noqa: E402


def gate(cmd: str):
    return _check_governance_bypass({"tool_name": "Bash", "tool_input": {"command": cmd}})


WRITES = [
    "echo x >> .claude/hooks/hook-launcher.py",
    "echo x >> ./.claude/./hooks/hook-launcher.py",
    "echo x >> .claude//hooks/hook-launcher.py",
    "echo x >> claude.md",
    "cp /tmp/x .claude/hooks/hook-launcher.py",
    "mv /tmp/x CLAUDE.md",
    "ln -sf /tmp/x .claude/kernel.md",
    "sed -i '' s/a/b/ .claude/hooks/pretool-gate.py",
    "cat /tmp/x | tee -a .claude/kernel.md",
    "git checkout -- CLAUDE.md",
    "perl -pi -e 's/a/b/' AGENTS.md",
    "dd if=/tmp/x of=.claude/hooks/pretool-gate.py",
]


@pytest.mark.parametrize("cmd", WRITES)
def test_write_channels_blocked(cmd):
    assert gate(cmd), f"放行了：{cmd}"


@pytest.mark.parametrize("cmd", [
    "cat CLAUDE.md",
    "grep -n gate .claude/kernel.md",
    "head -20 AGENTS.md",
    "git log --oneline -3",
])
def test_reads_still_allowed(cmd):
    assert gate(cmd) is None, f"误拦了：{cmd}"
