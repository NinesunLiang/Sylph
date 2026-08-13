"""F1 TDD: night-deny 会话作用域化——夜跑标记只约束持有会话，不阻断新终端。

缺陷：夜跑标记（.omc/state/night-session.active）只含时间戳，无持有会话绑定，
导致标记存在期间所有会话（含与夜跑无关的新终端）都被 night-deny 无条件拒绝。

修复语义：
- 标记含 session_id（已绑定持有会话）→ 仅该 session_id 的会话受约束；其它会话放行。
- 标记不含 session_id（legacy/残留）→ fail-open，不约束任何会话。
- session-start 在 CARROROS_NIGHT=1 时把当前 session_id 写入标记（夜跑会话自注册）。
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "carroros-night-deny.py"
SESSION_START = Path(__file__).resolve().parent / "session-start.py"


def _run_night_deny(marker_dir: Path, payload: dict) -> int:
    """直接调用 night-deny hook，NIGHT_DENY_ROOT 指向临时仓库根。"""
    env = dict(os.environ)
    env["NIGHT_DENY_ROOT"] = str(marker_dir)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload), text=True, capture_output=True,
        env=env, timeout=30,
    )
    return proc.returncode


def _write_marker(marker_dir: Path, content: str) -> Path:
    p = marker_dir / ".omc" / "state" / "night-session.active"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _bash_payload(session_id: str, command: str) -> dict:
    return {
        "session_id": session_id,
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def _load_session_start(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("session_start_under_test", SESSION_START)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    marker = tmp_path / ".omc" / "state" / "night-session.active"
    monkeypatch.setattr(mod, "NIGHT_MARKER", marker)
    return mod


# ── night-deny 作用域 ──


def test_unowned_marker_fail_open(tmp_path):
    """legacy 标记（仅时间戳、无 session_id）→ 不约束任何会话（fail-open）。"""
    _write_marker(tmp_path, "2026-08-13T06:38:15Z\n")
    rc = _run_night_deny(tmp_path, _bash_payload("sess-A", 'python3 -c "print(1)"'))
    assert rc == 0, f"unowned marker 应放行，实际 exit={rc}"


def test_owned_marker_matching_session_blocks(tmp_path):
    """标记绑定 sess-X，且 payload 是 sess-X → 非白名单命令应被阻断（exit 2）。"""
    _write_marker(tmp_path, "created_at: 2026-08-13T06:38:15Z\nsession_id: sess-X\n")
    rc = _run_night_deny(tmp_path, _bash_payload("sess-X", 'python3 -c "print(1)"'))
    assert rc == 2, f"持有会话的非法命令应阻断，实际 exit={rc}"


def test_owned_marker_other_session_allowed(tmp_path):
    """标记绑定 sess-X，payload 是 sess-Y（新终端）→ 放行。"""
    _write_marker(tmp_path, "created_at: 2026-08-13T06:38:15Z\nsession_id: sess-X\n")
    rc = _run_night_deny(tmp_path, _bash_payload("sess-Y", 'python3 -c "print(1)"'))
    assert rc == 0, f"非持有会话应放行，实际 exit={rc}"


def test_owned_marker_whitelisted_command_allowed_for_owner(tmp_path):
    """持有会话跑白名单只读命令 → 仍放行（作用域不改变白名单语义）。"""
    _write_marker(tmp_path, "created_at: 2026-08-13T06:38:15Z\nsession_id: sess-X\n")
    rc = _run_night_deny(tmp_path, _bash_payload("sess-X", "cat somefile.txt"))
    assert rc == 0, f"持有会话的白名单命令应放行，实际 exit={rc}"


def test_no_marker_allowed(tmp_path):
    """无标记 → 非夜间，放行。"""
    rc = _run_night_deny(tmp_path, _bash_payload("sess-A", 'python3 -c "print(1)"'))
    assert rc == 0, f"无标记应放行，实际 exit={rc}"


def test_owned_marker_payload_without_session_id_fail_closed(tmp_path):
    """owned 标记 + payload 无 session_id（攻击探测/坏 payload）→ 仍 fail-closed（P1-SOL-3）。"""
    _write_marker(tmp_path, "created_at: 2026-08-13T06:38:15Z\nsession_id: sess-X\n")
    payload = {"tool_name": "Bash", "tool_input": {"command": 'python3 -c "print(1)"'}}
    rc = _run_night_deny(tmp_path, payload)
    assert rc == 2, f"owned 标记下无 session_id 的非法命令应阻断，实际 exit={rc}"


# ── session-start 夜会话自注册 ──


def test_session_start_registers_owned_marker(monkeypatch, tmp_path):
    """CARROROS_NIGHT=1 + session_id → session-start 写入带 session_id 的标记。"""
    mod = _load_session_start(monkeypatch, tmp_path)
    monkeypatch.setenv("CARROROS_NIGHT", "1")
    payload = json.dumps({"session_id": "sess-night", "source": "startup"})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    try:
        mod.main()
    except SystemExit:
        pass
    marker = tmp_path / ".omc" / "state" / "night-session.active"
    assert marker.exists(), "夜会话标记应被创建"
    text = marker.read_text(encoding="utf-8")
    assert "session_id: sess-night" in text


def test_session_start_normal_session_ignores_marker(monkeypatch, tmp_path):
    """无 CARROROS_NIGHT → 不写标记（普通会话不受影响）。"""
    mod = _load_session_start(monkeypatch, tmp_path)
    monkeypatch.delenv("CARROROS_NIGHT", raising=False)
    payload = json.dumps({"session_id": "sess-normal", "source": "startup"})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    try:
        mod.main()
    except SystemExit:
        pass
    marker = tmp_path / ".omc" / "state" / "night-session.active"
    assert not marker.exists(), "普通会话不应创建夜会话标记"
