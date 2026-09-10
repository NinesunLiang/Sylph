"""index48 S4：completion-gate 验收测试（人类指令：「防止虚假完成，要经过特性 TDD 验收，
以及依赖树相关的 TDD 验收；以防止引入负面影响」）。

两段验收：
  一、**特性 TDD** —— 证明它确实能阻止「虚假完成」：
        - 非 completed → 放行
        - completed 且**无证据** → 不得静默放行
        - completed 且**证据合格**（≥20 字符且含 VERIFIED）→ 放行
  二、**依赖树 TDD** —— 证明外部依赖缺失/异常时不崩（fail-open），
        即改动不引入负面影响：
        - 证据目录不存在 → 不崩
        - stdin 非 JSON → 不崩
        - 已移除的 error-dna.jsonl 不存在 → 不崩（index48 解耦回归）

隔离方式：直接加载模块并 monkeypatch `PROJECT_ROOT` / `STATE_DIR` 到 tmp 目录，
不触碰真实 `.omc/state`。
"""
from __future__ import annotations

import importlib.util
import io
import json
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "completion-gate.py"

EVIDENCE_NAME = ".completion-evidence-" + datetime.now().strftime("%Y%m%d-%H%M")


def _load():
    spec = importlib.util.spec_from_file_location("completion_gate_48", HOOK)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(mod, monkeypatch, tmp: Path, payload_text: str):
    """在隔離的 tmp 项目下跑 main()，返回 (exit_code, stdout)。"""
    state = tmp / ".omc" / "state"
    state.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp)
    monkeypatch.setattr(mod, "STATE_DIR", state)
    monkeypatch.setattr("sys.stdin", io.StringIO(payload_text))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    code = 0
    try:
        mod.main()
    except SystemExit as exc:
        code = exc.code or 0
    return code, out.getvalue()


def _payload(status: str) -> str:
    return json.dumps({"tool_name": "TaskUpdate",
                       "tool_input": {"taskId": "1", "status": status}})


def _wrote_evidence(tmp: Path, text: str) -> None:
    state = tmp / ".omc" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / EVIDENCE_NAME).write_text(text, encoding="utf-8")


# ── 一、特性 TDD ──

def test_feature_non_completed_passes_through(tmp_path, monkeypatch):
    mod = _load()
    code, out = _run(mod, monkeypatch, tmp_path, _payload("in_progress"))
    assert code == 0
    assert json.loads(out.strip().splitlines()[-1]).get("continue") is True


def test_feature_completed_without_evidence_is_not_silently_passed(tmp_path, monkeypatch):
    """核心特性：无证据的「完成」必须被拦下（防虚假完成）。"""
    mod = _load()
    _code, out = _run(mod, monkeypatch, tmp_path, _payload("completed"))
    last = out.strip().splitlines()[-1]
    data = json.loads(last)
    # 要么显式阻断（continue=False / deny），要么附带拦截说明——但不得是干净放行
    assert data.get("continue") is not True or "hookSpecificOutput" in data, \
        f"无证据的 completed 被静默放行: {data}"


def test_feature_completed_without_evidence_logs_redirect(tmp_path, monkeypatch):
    mod = _load()
    _run(mod, monkeypatch, tmp_path, _payload("completed"))
    log = tmp_path / ".omc" / "state" / "completion-gate-autonomous.log"
    assert log.exists() and "REDIRECT" in log.read_text(encoding="utf-8"), \
        "无证据的 completed 未留下 REDIRECT 记录"


def test_feature_completed_with_valid_evidence_passes(tmp_path, monkeypatch):
    mod = _load()
    _wrote_evidence(tmp_path, "unit tests VERIFIED: 42 passed, 0 failed\n")
    code, out = _run(mod, monkeypatch, tmp_path, _payload("completed"))
    assert code == 0
    assert json.loads(out.strip().splitlines()[-1]).get("continue") is True


# ── 二、依赖树 TDD（外部依赖缺失/异常不得崩）──

def test_dep_missing_state_dir_does_not_crash(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mod, "STATE_DIR", tmp_path / "nonexistent" / "state")
    monkeypatch.setattr("sys.stdin", io.StringIO(_payload("completed")))
    monkeypatch.setattr("sys.stdout", io.StringIO())
    try:
        mod.main()
    except SystemExit:
        pass  # 正常退出即可
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"依赖缺失时崩溃: {type(exc).__name__}: {exc}")


def test_dep_malformed_stdin_does_not_crash(tmp_path, monkeypatch):
    mod = _load()
    _code, out = _run(mod, monkeypatch, tmp_path, "{not json at all")
    assert json.loads(out.strip().splitlines()[-1]).get("continue") is True


def test_dep_no_error_dna_file_does_not_crash(tmp_path, monkeypatch):
    """index48：error-dna 已移除，钩子不得依赖它（解耦回归）。"""
    mod = _load()
    assert not (tmp_path / ".omc" / "state" / "error-dna.jsonl").exists()
    _code, out = _run(mod, monkeypatch, tmp_path, _payload("completed"))
    assert out.strip(), "钩子无输出"
