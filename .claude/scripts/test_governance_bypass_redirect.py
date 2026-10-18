"""governance_bypass 测试（ADR 0015 二期 → P0 治理加固 2026-10-18）。

行为变更：
  旧：Bash 写治理文件 → REDIRECT（软门禁，不 BLOCK）。
  新：Bash 写治理文件 → BLOCK（冻结域），除非持人类签发的审批票。

原因：REDIRECT 可被模型「重试」穿过去；治理文件的可逆性不足，必须人类共签。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / ".claude/hooks"))
from pretool_gates import checks as CHECKS  # noqa: E402


@pytest.fixture(autouse=True)
def _no_live_ticket(monkeypatch, tmp_path):
    """隔离真实审批票：测试默认「无票」。"""
    monkeypatch.setenv("CARROROS_GOV_TICKET", str(tmp_path / "no-ticket.json"))


def _payload(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_governance_bypass_blocks_bash_echo_to_claude_md():
    result = CHECKS._check_governance_bypass(_payload("echo something >> CLAUDE.md"))
    assert result is not None, "governance_bypass 未检测 Bash 写敏感治理文件"
    assert result.startswith("BLOCK"), f"应硬拦而非 REDIRECT，got: {result!r}"


def test_governance_bypass_blocks_settings_append():
    result = CHECKS._check_governance_bypass(
        _payload("echo something >> .claude/settings.json")
    )
    assert result is not None and result.startswith("BLOCK")


def test_governance_bypass_blocks_harness_append():
    result = CHECKS._check_governance_bypass(
        _payload("echo something >> .claude/workflows/frontend-overnight/scripts/carroros-gates/harness.yaml")
    )
    assert result is not None and result.startswith("BLOCK")


def test_governance_bypass_ignores_benign_bash():
    """合法 Bash（读/非敏感写）不被误伤。"""
    assert CHECKS._check_governance_bypass(_payload("ls -la")) is None
    assert CHECKS._check_governance_bypass(_payload("echo hello")) is None
    assert CHECKS._check_governance_bypass(
        _payload("echo x >> .omc/tasks/test/plan.md")
    ) is None


def test_governance_bypass_ignores_non_bash_tools():
    """Write/Edit 工具仍由 _check_sensitive_edit 处理，不重复拦截。"""
    assert CHECKS._check_governance_bypass(
        {"tool_name": "Write", "tool_input": {"file_path": "CLAUDE.md"}}
    ) is None
