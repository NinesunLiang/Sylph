"""governance_bypass REDIRECT 测试（ADR 0015 二期）。

路径找补：Bash 写敏感治理文件（echo/cat >> CLAUDE.md 等绕过 Write 门禁）
→ pretool check 返回 REDIRECT（软门禁，不 BLOCK），引导走正确路径。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / ".claude/hooks"))
from pretool_gates import checks as CHECKS  # noqa: E402


def _payload(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_governance_bypass_check_exists_and_redirects_bash_echo():
    """Bash echo 写顶层 CLAUDE.md → REDIRECT（不 BLOCK）。"""
    result = CHECKS._check_governance_bypass(_payload("echo something >> CLAUDE.md"))
    assert result is not None, "governance_bypass 未检测 Bash 写敏感治理文件"
    assert result.startswith("REDIRECT"), f"应 REDIRECT 而非硬拦，got: {result!r}"


def test_governance_bypass_redirects_settings_append():
    result = CHECKS._check_governance_bypass(
        _payload("echo something >> .claude/settings.json")
    )
    assert result is not None and result.startswith("REDIRECT")


def test_governance_bypass_redirects_harness_append():
    result = CHECKS._check_governance_bypass(
        _payload("echo something >> scripts/carroros-gates/harness.yaml")
    )
    assert result is not None and result.startswith("REDIRECT")


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
