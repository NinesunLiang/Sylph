"""test_gate_bypassed_detection.py — 拦截≠阻止观测增强（index34 S2）

无人模式不硬阻断（人类裁决），拦截≠阻止通过"后写检测"留痕：
pretool-gate 刚 BLOCK 某敏感/凭据文件（audit 有 credential_write_block 等），
但该文件仍被写入 → 记录 gate_bypassed 事件（.omc/state/gate-bypassed.jsonl）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent


def _load_hook():
    sys.path.insert(0, str(_HOOKS))
    spec = importlib.util.spec_from_file_location("posttool_claim_audit_gb", _HOOKS / "posttool-claim-audit.py")
    assert spec is not None and spec.loader is not None, "hook 加载失败"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["posttool_claim_audit_gb"] = mod
    spec.loader.exec_module(mod)
    return mod


hook = _load_hook()


def _write_block_event(path: str, ts: str | None = None) -> dict:
    return {
        "actor": "hook:pretool-gate",
        "event_type": "credential_write_block",
        "path": path,
        "timestamp": ts or datetime.now(timezone.utc).isoformat(),
        "tool": "edit",
    }


def _make_audit(tmp_path, events: list[dict]) -> Path:
    audit = tmp_path / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "test.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")
    return audit


def test_detect_recent_credential_block_true(tmp_path):
    """同路径、近期有 credential_write_block → 检测为 True。"""
    audit = _make_audit(tmp_path, [_write_block_event("/tmp/x/credentials.json")])
    assert hook._detect_gate_bypassed("/tmp/x/credentials.json", tmp_path) is True


def test_detect_different_file_false(tmp_path):
    """同路径 BLOCK，但写的是另一个文件 → False（不误报）。"""
    _make_audit(tmp_path, [_write_block_event("/tmp/x/credentials.json")])
    assert hook._detect_gate_bypassed("/tmp/x/report.md", tmp_path) is False


def test_detect_no_block_event_false(tmp_path):
    """audit 无 BLOCK 事件 → False。"""
    _make_audit(tmp_path, [{"event_type": "other", "actor": "x"}])
    assert hook._detect_gate_bypassed("/tmp/x/credentials.json", tmp_path) is False


def test_detect_stale_block_false(tmp_path):
    """BLOCK 事件超过 120s 窗口 → False。"""
    old_ts = datetime.fromtimestamp(datetime.now().timestamp() - 300, tz=timezone.utc).isoformat()
    _make_audit(tmp_path, [_write_block_event("/tmp/x/credentials.json", old_ts)])
    assert hook._detect_gate_bypassed("/tmp/x/credentials.json", tmp_path) is False


def test_log_gate_bypassed_writes_event(tmp_path):
    """_log_gate_bypassed → gate-bypassed.jsonl 含 gate_bypassed 事件。"""
    hook._log_gate_bypassed(tmp_path, "/tmp/x/credentials.json", "Write")
    log = tmp_path / "gate-bypassed.jsonl"
    assert log.exists(), "gate-bypassed.jsonl 未创建"
    last = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert last["event_type"] == "gate_bypassed"
    assert "credentials.json" in last["file_path"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
