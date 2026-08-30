"""test_governance_delete_protection.py — 治理指令文件删除保护（index33 电池实证修复）

rm-dot 电池实证（index33）：ON 侧模型删光 AGENTS.md/CLAUDE.md/README/.omc，
而 .claude/.git 仅靠 Claude Code 内建 rm -rf 门禁存活——治理基座无自保。
修复：新增 _check_governance_delete_protection，删除 AGENTS.md/CLAUDE.md/kernel.md/index.md → REDIRECT。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS))

from pretool_gates import checks  # noqa: E402


def _bash_rm_payload(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def _delete_payload(path: str) -> dict:
    return {"tool_name": "Delete", "tool_input": {"file_path": path}}


# ── 治理指令文件删除 → REDIRECT ───────────────────────────────────────────

def test_rm_agents_md_redirects():
    """Bash rm AGENTS.md → REDIRECT（治理指令文件不可删）。"""
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm AGENTS.md"))
    assert r and "REDIRECT" in r and "governance_delete_protected" in r, f"实际: {r!r}"


def test_rm_claude_md_redirects():
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm CLAUDE.md"))
    assert r and "governance_delete_protected" in r, f"实际: {r!r}"


def test_rm_kernel_md_redirects():
    """删 .claude/kernel.md（治理内核）→ REDIRECT。"""
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm .claude/kernel.md"))
    assert r and "governance_delete_protected" in r, f"实际: {r!r}"


def test_rm_index_md_redirects():
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm .claude/index.md"))
    assert r and "governance_delete_protected" in r, f"实际: {r!r}"


def test_delete_tool_agents_md_redirects():
    """Delete 工具删 AGENTS.md → REDIRECT。"""
    r = checks._check_governance_delete_protection(_delete_payload("AGENTS.md"))
    assert r and "governance_delete_protected" in r, f"实际: {r!r}"


# ── 普通文件删除 → 放行 ───────────────────────────────────────────────────

def test_rm_normal_file_passes():
    """Bash rm 普通文件 → 放行（None）。"""
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm README.md"))
    assert r is None, f"普通文件删除不应拦截, 实际: {r!r}"


def test_rm_data_txt_passes():
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm data.txt notes.md temp.py"))
    assert r is None, f"多文件普通删除不应拦截, 实际: {r!r}"


def test_no_delete_command_passes():
    """非删除命令 → 放行。"""
    r = checks._check_governance_delete_protection(
        {"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    assert r is None, f"非删除命令不应拦截, 实际: {r!r}"


# ── index34 修复：rm flags 形态（验收法官发现真实攻击形态 rm -rf 被绕过）────────

def test_rm_rf_agents_md_redirects():
    """rm -rf AGENTS.md（真实攻击形态）→ REDIRECT。"""
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm -rf AGENTS.md"))
    assert r and "governance_delete_protected" in r, f"rm -rf 应拦截, 实际: {r!r}"


def test_rm_f_claude_md_redirects():
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm -f CLAUDE.md"))
    assert r and "governance_delete_protected" in r, f"rm -f 应拦截, 实际: {r!r}"


def test_rm_force_kernel_md_redirects():
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm --force .claude/kernel.md"))
    assert r and "governance_delete_protected" in r, f"rm --force 应拦截, 实际: {r!r}"


def test_git_rm_r_agents_md_redirects():
    r = checks._check_governance_delete_protection(_bash_rm_payload("git rm -r AGENTS.md"))
    assert r and "governance_delete_protected" in r, f"git rm -r 应拦截, 实际: {r!r}"


def test_rm_rf_multiple_governance_files_redirects():
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm -rf AGENTS.md CLAUDE.md"))
    assert r and "governance_delete_protected" in r, f"rm -rf 多文件应拦截, 实际: {r!r}"


def test_rm_rf_index_md_redirects():
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm -rf .claude/index.md"))
    assert r and "governance_delete_protected" in r, f"rm -rf .claude/index.md 应拦截, 实际: {r!r}"


# ── index34 收紧：不误伤普通 index.md/kernel.md ────────────────────────────

def test_rm_docs_index_md_passes():
    """rm docs/index.md（非治理目录）→ 放行（不误伤）。"""
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm docs/index.md"))
    assert r is None, f"docs/index.md 不应拦截, 实际: {r!r}"


def test_rm_kernel_md_root_passes():
    """rm kernel.md（非 .claude/ 下的普通文件）→ 放行。"""
    r = checks._check_governance_delete_protection(_bash_rm_payload("rm notes/kernel.md"))
    assert r is None, f"非治理 kernel.md 不应拦截, 实际: {r!r}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
