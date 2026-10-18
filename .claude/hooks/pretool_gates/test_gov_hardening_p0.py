"""test_gov_hardening_p0.py — P0 治理加固 RED 测试。

覆盖两件事：
  A. 冻结域硬拒绝 + 人类审批票
     - 治理文件无票 → BLOCK（不再 WARN / goal 模式不再降级放行）
     - 治理清单补漏：index.md / harness.yaml / CLAUDE.md
     - 有效票（路径 + 内容哈希 + TTL）→ 放行
     - 过期票 / 哈希不符 / 文件未列入 → BLOCK
     - Bash 重定向写治理文件 → BLOCK（不再 REDIRECT）
  B. 门禁 fail-closed
     - 安全门自身抛异常 → 返回 BLOCK，不再静默放行
     - 非安全门抛异常 → 仍可继续（避免把所有门都变成硬阻断）
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOKS = ROOT / ".claude" / "hooks"


# ── 载入被测模块 ───────────────────────────────────────────────────────

def _load_checks():
    import sys
    sys.path.insert(0, str(HOOKS))
    from pretool_gates import checks as CHECKS  # noqa: E402
    return CHECKS


def _load_helpers():
    import sys
    sys.path.insert(0, str(HOOKS))
    from pretool_gates import helpers as HELPERS  # noqa: E402
    return HELPERS


def _load_pretool_gate():
    spec = importlib.util.spec_from_file_location(
        "pretool_gate_under_test", HOOKS / "pretool-gate.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECKS = _load_checks()
HELPERS = _load_helpers()


def _payload(tool: str, **tool_input) -> dict:
    return {"tool_name": tool, "tool_input": tool_input}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_ticket(ticket_path: Path, files: dict[str, str], *,
                  ttl_minutes: int = 30, expires_delta_minutes: int | None = None,
                  created_offset_minutes: int = 0) -> None:
    now = datetime.now(timezone.utc)
    created = now - timedelta(minutes=created_offset_minutes)
    expires = (now + timedelta(minutes=ttl_minutes)
               if expires_delta_minutes is None
               else now + timedelta(minutes=expires_delta_minutes))
    ticket_path.parent.mkdir(parents=True, exist_ok=True)
    ticket_path.write_text(json.dumps({
        "version": 1,
        "approved_by": "human-tester",
        "reason": "pytest",
        "created_at": created.isoformat(),
        "expires_at": expires.isoformat(),
        "files": {k: {"sha256": v, "used": False} for k, v in files.items()},
    }, ensure_ascii=False), encoding="utf-8")


@pytest.fixture()
def ticket_path(tmp_path, monkeypatch):
    p = tmp_path / "governance-approval.json"
    monkeypatch.setenv("CARROROS_GOV_TICKET", str(p))
    return p


# ── A1. 治理清单补漏 ───────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    ".claude/index.md",
    ".claude/harness.yaml",
    "CLAUDE.md",
    ".claude/kernel.md",
    "AGENTS.md",
    ".claude/settings.json",
    ".claude/hooks/pretool-gate.py",
    ".claude/rules/external-knowledge.md",
    ".claude/scripts/gov_approve.py",
])
def test_governance_scope_covers_all_frozen_files(path):
    assert HELPERS._is_governance(path) is True, f"{path} 应在治理保护域内"


@pytest.mark.parametrize("path", [
    ".claude/scripts/carros_base.py",
    ".claude/scripts/verify_gate.py",
    ".claude/scripts/jev_audit.py",
])
def test_scripts_are_tools_not_governance(path):
    """2026-10-18 人类裁决：.claude/scripts 是普通工具，不需要签票。"""
    assert HELPERS._is_governance(path) is False, f"{path} 不应再要求审批票"


# ── A2. 无票 → BLOCK ───────────────────────────────────────────────────

def test_governance_edit_blocked_without_ticket(ticket_path):
    r = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/kernel.md",
                 old_string="a", new_string="b")
    )
    assert r is not None and r.startswith("BLOCK"), f"治理文件无票应 BLOCK, got: {r!r}"


def test_governance_write_blocked_without_ticket(ticket_path):
    r = CHECKS._check_sensitive_edit(
        _payload("Write", file_path=".claude/index.md", content="x")
    )
    assert r is not None and r.startswith("BLOCK")


def test_goal_mode_does_not_downgrade_governance(ticket_path, monkeypatch):
    """goal 模式也必须 BLOCK，不得降级放行。"""
    monkeypatch.setattr(CHECKS, "_goal_mode", lambda: True)
    r = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/kernel.md",
                 old_string="a", new_string="b")
    )
    assert r is not None and r.startswith("BLOCK"), f"goal 模式不得放行, got: {r!r}"


# ── A3. 有效票 → 放行 ──────────────────────────────────────────────────

def test_valid_ticket_allows_governance_edit(ticket_path):
    target = ROOT / ".claude" / "kernel.md"
    _write_ticket(ticket_path, {".claude/kernel.md": _sha256(target)})
    r = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/kernel.md",
                 old_string="a", new_string="b")
    )
    assert r is None, f"有效票应放行, got: {r!r}"


def test_ticket_for_other_file_does_not_allow(ticket_path):
    target = ROOT / ".claude" / "kernel.md"
    _write_ticket(ticket_path, {".claude/kernel.md": _sha256(target)})
    r = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/index.md",
                 old_string="a", new_string="b")
    )
    assert r is not None and r.startswith("BLOCK")


# ── A4. 失效票 → BLOCK ─────────────────────────────────────────────────

def test_expired_ticket_blocks(ticket_path):
    target = ROOT / ".claude" / "kernel.md"
    _write_ticket(ticket_path, {".claude/kernel.md": _sha256(target)},
                  expires_delta_minutes=-1)
    r = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/kernel.md",
                 old_string="a", new_string="b")
    )
    assert r is not None and r.startswith("BLOCK")


def test_hash_mismatch_blocks(ticket_path):
    _write_ticket(ticket_path, {".claude/kernel.md": "0" * 64})
    r = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/kernel.md",
                 old_string="a", new_string="b")
    )
    assert r is not None and r.startswith("BLOCK")


def test_ticket_ttl_capped_at_24h(ticket_path):
    target = ROOT / ".claude" / "kernel.md"
    _write_ticket(ticket_path, {".claude/kernel.md": _sha256(target)},
                  expires_delta_minutes=60 * 48)
    r = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/kernel.md",
                 old_string="a", new_string="b")
    )
    assert r is not None and r.startswith("BLOCK"), "超过 24h 的票应失效"


# ── A5. Bash 通道 → BLOCK ──────────────────────────────────────────────

def test_bash_redirect_to_governance_denied(ticket_path):
    """Bash 写治理文件必须是硬拒绝（BLOCK 或 ASK_USER 在 CC 都是 deny）。"""
    r = CHECKS._check_sensitive_write_bash(
        _payload("Bash", command="echo x >> .claude/kernel.md")
    )
    assert r is not None, "Bash 写治理文件必须被拒绝"
    assert r.startswith(("BLOCK", "ASK_USER")), f"应为硬拒绝, got: {r!r}"
    assert "governance_frozen" in r


def test_bash_redirect_with_valid_ticket_allowed(ticket_path):
    target = ROOT / ".claude" / "kernel.md"
    _write_ticket(ticket_path, {".claude/kernel.md": _sha256(target)})
    r = CHECKS._check_sensitive_write_bash(
        _payload("Bash", command="echo x >> .claude/kernel.md")
    )
    assert r is None, f"有效票应放行 Bash 写入, got: {r!r}"


def test_bash_redirect_to_after_ticket_consumed(ticket_path):
    """票的哈希只校验一次；首次使用后标记 used，后续写入仅受 TTL 约束。"""
    target = ROOT / ".claude" / "kernel.md"
    _write_ticket(ticket_path, {".claude/kernel.md": _sha256(target)})
    first = CHECKS._check_sensitive_edit(
        _payload("Edit", file_path=".claude/kernel.md",
                 old_string="a", new_string="b")
    )
    assert first is None
    data = json.loads(ticket_path.read_text(encoding="utf-8"))
    assert data["files"][".claude/kernel.md"]["used"] is True


# ── B. fail-closed ─────────────────────────────────────────────────────

def test_security_gate_exception_fails_closed():
    gate = _load_pretool_gate()

    def _boom(payload):
        raise RuntimeError("boom")

    result, crashed = gate._call_gate("governance-bypass", _boom, {})
    assert crashed is True
    assert result is not None and result.startswith("BLOCK"), \
        f"安全门异常应 fail-closed, got: {result!r}"


def test_non_security_gate_exception_does_not_block():
    gate = _load_pretool_gate()

    def _boom(payload):
        raise RuntimeError("boom")

    result, crashed = gate._call_gate("test-verification", _boom, {})
    assert crashed is True
    assert result is None, f"非安全门异常不应硬阻断, got: {result!r}"


# ── C. agentic-ui：ASK_USER 必须是宿主可选择的 ask ─────────────────────

def _last_json(out: str) -> dict:
    lines = [ln for ln in out.splitlines() if ln.strip().startswith("{")]
    return json.loads(lines[-1])


def test_ask_user_emits_host_choice(capsys):
    """2026-10-18 用户裁决：ASK_USER 不得退化成文字 deny，必须让宿主弹出选择。"""
    HELPERS._block("ASK_USER governance_frozen", "确认后继续")
    data = _last_json(capsys.readouterr().out)
    assert data["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_destructive_block_still_denies(capsys):
    HELPERS._block("BLOCK plain_block", "危险操作")
    data = _last_json(capsys.readouterr().out)
    assert data["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_goal_mode_ask_user_stays_deny(capsys, monkeypatch):
    """无人值守时没人能回答 ask → 必须回退 deny + 引导，否则任务卡死。"""
    monkeypatch.setattr(HELPERS, "_goal_mode", lambda: True)
    HELPERS._block("ASK_USER governance_frozen", "确认后继续")
    data = _last_json(capsys.readouterr().out)
    assert data["hookSpecificOutput"]["permissionDecision"] == "deny"
