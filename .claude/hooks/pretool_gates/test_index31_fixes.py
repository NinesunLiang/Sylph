"""test_index31_fixes.py — index30 双法官优化项机制修复 TDD（先红后绿）。

F1 审计压缩：PASS 收敛为计数文件，不再逐条写 audit JSONL
F2 凭据 default-deny：sensitive-edit 对凭据类路径从 ASK_USER 升级为 BLOCK
F3 验证补位：改 .py 且项目有测试但无 pytest 记录 → REDIRECT 强制验证文化
F4 L1 联动：任务 level=L1 时 gate mode 回落 l1（headless 下小任务不再跑 20 道门）
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pretool_gates import checks  # noqa: E402
from pretool_gates import helpers  # noqa: E402


def _payload(tool: str, **kw) -> dict:
    return {"tool_name": tool, "tool_input": kw}


# ── F1 审计压缩 ─────────────────────────────────────────────────────────

def test_pass_decision_writes_counter_not_audit():
    """PASS 决策不再逐条写 audit；计数文件 +1。"""
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        old_audit = helpers.AUDIT
        old_cnt = helpers._GATE_PASS_COUNTER
        helpers.AUDIT = Path(td) / "audit"
        helpers._GATE_PASS_COUNTER = Path(td) / "gate-pass-count.jsonl"
        try:
            helpers._record_gate_decision("action", None, "l1")  # None → PASS
            helpers._record_gate_decision("action", None, "l1")
            assert not helpers.AUDIT.exists(), "PASS 不应写 audit JSONL"
            lines = helpers._GATE_PASS_COUNTER.read_text(encoding="utf-8").splitlines()
            assert len(lines) == 2, f"计数应 2 条, 实际 {len(lines)}"
            assert json.loads(lines[0])["gate"] == "action"
        finally:
            helpers.AUDIT = old_audit
            helpers._GATE_PASS_COUNTER = old_cnt


def test_non_pass_decision_still_writes_audit():
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        old_audit = helpers.AUDIT
        helpers.AUDIT = Path(td) / "audit"
        try:
            helpers._record_gate_decision("action", "BLOCK dangerous", "l1")
            assert helpers.AUDIT.exists()
            files = list(helpers.AUDIT.glob("*.jsonl"))
            assert files, "非 PASS 应写审计分片"
            content = files[0].read_text(encoding="utf-8")
            assert "BLOCK dangerous" in content
        finally:
            helpers.AUDIT = old_audit


# ── F2 凭据 default-deny ────────────────────────────────────────────────

def test_credential_edit_is_blocked_not_asked():
    """Edit credentials.json → BLOCK（原 ASK_USER；凭据类 default-deny）。"""
    r = checks._check_sensitive_edit(_payload("Edit", file_path="credentials.json",
                                               old_string="a", new_string="b"))
    assert r and r.startswith("BLOCK"), f"凭据编辑应 BLOCK, 实际: {r}"


def test_env_file_write_is_blocked():
    r = checks._check_sensitive_edit(_payload("Write", file_path="/x/.env", content="K=1"))
    assert r and r.startswith("BLOCK"), f".env 写入应 BLOCK, 实际: {r}"


def test_governance_file_edit_requires_human_ticket(monkeypatch, tmp_path):
    """P0（2026-10-18 人类裁决）：治理文件从 WARN 升级为 BLOCK，须持人类审批票。

    行为变更说明：旧契约是「治理文件 WARN 后放行」；新契约是「无票即拒绝」。
    """
    monkeypatch.setenv("CARROROS_GOV_TICKET", str(tmp_path / "no-ticket.json"))
    r = checks._check_sensitive_edit(_payload("Edit", file_path=".claude/hooks/pretool-gate.py",
                                               old_string="a", new_string="b"))
    assert r is not None and r.startswith("BLOCK"), f"治理文件无票应 BLOCK: {r}"


# ── F3 验证补位 ─────────────────────────────────────────────────────────

def _mk_project(with_test: bool, pytest_evidence: bool) -> Path:
    td = Path(tempfile.mkdtemp(prefix="carros-t31-"))
    (td / "app.py").write_text("x = 1\n", encoding="utf-8")
    if with_test:
        (td / "test_app.py").write_text("def test_x(): pass\n", encoding="utf-8")
    audit = td / ".omc" / "state" / "audit"
    if pytest_evidence:
        audit.mkdir(parents=True)
        # index36 修复：日期炸弹——门禁 _check_test_verification 查的是「今天」的 audit 分片
        # （datetime.now().strftime('%Y-%m-%d')），fixture 硬编码 2026-08-15 导致今天必红。
        # 改用今天日期，与门禁契约对齐。
        # index40 修复：证据格式对齐 F2——test_run 事件带近期 timestamp（_recent_test_run 按窗口校验）
        from datetime import datetime, timezone
        today = datetime.now().strftime("%Y-%m-%d")
        (audit / f"{today}.jsonl").write_text(
            json.dumps({"event_type": "test_run", "reason": "pytest",
                        "timestamp": datetime.now(timezone.utc).isoformat()}) + "\n",
            encoding="utf-8")
    return td


def test_edit_py_without_test_evidence_redirects():
    td = _mk_project(with_test=True, pytest_evidence=False)
    old = os.getcwd()
    old_state = checks.STATE_DIR
    try:
        os.chdir(td)
        # index37 修复：hermetic——避免读到真实仓库 audit（test_run 记录器/测试运行会污染）
        checks.STATE_DIR = td / ".omc" / "state"
        r = checks._check_test_verification(
            _payload("Edit", file_path="app.py", old_string="1", new_string="2"))
    finally:
        checks.STATE_DIR = old_state
        os.chdir(old)
    assert r and r.startswith("REDIRECT"), f"改 .py 无测试证据应 REDIRECT, 实际: {r}"


def test_edit_py_with_pytest_evidence_allowed():
    td = _mk_project(with_test=True, pytest_evidence=True)
    old = os.getcwd()
    old_state = checks.STATE_DIR
    try:
        os.chdir(td)
        checks.STATE_DIR = td / ".omc" / "state"
        r = checks._check_test_verification(
            _payload("Edit", file_path="app.py", old_string="1", new_string="2"))
    finally:
        checks.STATE_DIR = old_state
        os.chdir(old)
    assert r is None, f"已有 pytest 证据应放行, 实际: {r}"


def test_edit_py_without_tests_allowed():
    td = _mk_project(with_test=False, pytest_evidence=False)
    old = os.getcwd()
    old_state = checks.STATE_DIR
    try:
        os.chdir(td)
        checks.STATE_DIR = td / ".omc" / "state"
        r = checks._check_test_verification(
            _payload("Edit", file_path="app.py", old_string="1", new_string="2"))
    finally:
        checks.STATE_DIR = old_state
        os.chdir(old)
    assert r is None, f"无测试文件应放行, 实际: {r}"


def test_edit_non_py_allowed():
    r = checks._check_test_verification(_payload("Edit", file_path="README.md",
                                                  old_string="a", new_string="b"))
    assert r is None


# ── F4 L1 联动 ──────────────────────────────────────────────────────────

def test_gate_mode_from_l1_token():
    assert helpers._gate_mode_from_token({"session": {"level": "L1"}}) == "l1"


def test_gate_mode_from_l2_token():
    assert helpers._gate_mode_from_token({"session": {"level": "l2"}}) == "l2"


def test_gate_mode_from_no_token():
    assert helpers._gate_mode_from_token({}) == ""
    assert helpers._gate_mode_from_token(None) == ""
