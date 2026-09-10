"""index46 S5 机制修复回归测试（先红后绿）。

覆盖共识差距：
- G2/F1  L2 门列表重复登记（3 道门每工具调用跑两遍）
- G1/F2  分级默认值反了：非交互兜底 l2（应先 l1）
- G3/F3  隐私门禁路径模式过宽（`secret-leak` 目录被误拦）
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pretool_gates import checks  # noqa: E402
from pretool_gates import helpers  # noqa: E402


def _load_gate_module() -> ModuleType:
    """加载 pretool-gate.py（含连字符文件名，不能用 import 语句）。"""
    spec = importlib.util.spec_from_file_location(
        "pretool_gate_mod", Path(__file__).resolve().parents[1] / "pretool-gate.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── G2 / F1：L2 门列表不得重复登记（单一真源） ──

def test_l1_gates_have_no_duplicate_names():
    names = [name for name, _ in _load_gate_module().L1_GATES]
    assert len(names) == len(set(names)), f"L1 门列表有重名: {names}"


def test_l2_gates_have_no_duplicate_names():
    names = [name for name, _ in _load_gate_module().GATES]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, f"L2 门列表重复登记（同一调用会跑两遍）: {dupes}"


def test_l2_gates_superset_of_l1_core():
    """去重后 L2 仍必须是 L1 的超集——安全门一道都不能少。"""
    mod = _load_gate_module()
    l1 = {name for name, _ in mod.L1_GATES}
    l2 = {name for name, _ in mod.GATES}
    assert l1 <= l2, f"L2 缺少 L1 的门: {sorted(l1 - l2)}"


def test_injection_guard_stays_on_at_l1():
    """G1：档位默认降为 l1 后，注入防护/超长写保护不得随之丢失（kernel.md 明文要求）。"""
    names = {name for name, _ in _load_gate_module().L1_GATES}
    assert "injection-guard" in names


def test_core_security_gates_present_at_l1():
    """L1 是安全底线：凭据/密钥/治理绕过/治理删除保护必须常开。"""
    names = {name for name, _ in _load_gate_module().L1_GATES}
    for gate in ("sensitive-edit", "sensitive-read", "sensitive-write-bash",
                 "secret-scan", "governance-bypass", "governance-delete-protection",
                 "omc-skeleton-readonly", "test-verification"):
        assert gate in names, f"L1 缺少安全门: {gate}"


# ── G1 / F2：分级默认值 = L1（对齐 AGENTS.md「默认 L1」） ──

def test_gate_mode_defaults_to_l1_without_token(monkeypatch):
    monkeypatch.delenv("CARROROS_GATE_MODE", raising=False)
    monkeypatch.setenv("CI", "")
    monkeypatch.setattr(helpers, "_active_token", lambda: None)
    assert helpers._get_gate_mode() == "l1"


def test_gate_mode_env_override_l2_still_wins(monkeypatch):
    monkeypatch.setenv("CARROROS_GATE_MODE", "l2")
    monkeypatch.setattr(helpers, "_active_token", lambda: None)
    assert helpers._get_gate_mode() == "l2"


def test_gate_mode_env_override_l1_still_wins(monkeypatch):
    monkeypatch.setenv("CARROROS_GATE_MODE", "l1")
    monkeypatch.setattr(helpers, "_active_token", lambda: None)
    assert helpers._get_gate_mode() == "l1"


def test_gate_mode_follows_l2_task_token(monkeypatch):
    """L2 任务 token 必须把门禁升到 l2（安全门不能因默认值变更而丢）。"""
    monkeypatch.delenv("CARROROS_GATE_MODE", raising=False)
    monkeypatch.setattr(helpers, "_active_token", lambda: {"session": {"level": "L2"}})
    assert helpers._get_gate_mode() == "l2"


def test_gate_mode_follows_l1_task_token(monkeypatch):
    monkeypatch.delenv("CARROROS_GATE_MODE", raising=False)
    monkeypatch.setattr(helpers, "_active_token", lambda: {"session": {"level": "L1"}})
    assert helpers._get_gate_mode() == "l1"


def test_harness_config_gate_mode_is_honored(tmp_path, monkeypatch):
    """G1：`.claude/harness.yaml` 的档位配置必须真的生效（原路径写错 → 永久失效）。"""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "harness.yaml").write_text("gate_mode: l2\n", encoding="utf-8")
    monkeypatch.setattr(helpers, "ROOT", tmp_path)
    assert helpers._harness_gate_mode() == "l2"


def test_harness_config_project_section_gate_mode_is_honored(tmp_path, monkeypatch):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "harness.yaml").write_text(
        "project:\n  gate_mode: l2\n", encoding="utf-8")
    monkeypatch.setattr(helpers, "ROOT", tmp_path)
    assert helpers._harness_gate_mode() == "l2"


def test_harness_config_absent_falls_back_to_l1(tmp_path, monkeypatch):
    monkeypatch.setattr(helpers, "ROOT", tmp_path)
    monkeypatch.delenv("CARROROS_GATE_MODE", raising=False)
    monkeypatch.setattr(helpers, "_active_token", lambda: None)
    assert helpers._get_gate_mode() == "l1"


# ── G3 / F3：隐私门禁路径模式——精确段匹配，不误伤带连字符的目录名 ──

def test_sensitive_path_does_not_block_hyphenated_eval_dir():
    """评测/审计用的 `secret-leak` 目录名不得被当成凭据文件拦掉。"""
    assert checks._is_read_sensitive(
        "/tmp/carros-eval-index46/sanitized/on/secret-leak/transcript.txt") is False
    assert checks._is_read_sensitive(
        "/tmp/carros-eval-index46/results/off/secret-leak/result.json") is False


def test_sensitive_path_still_blocks_real_credential_paths():
    """真实凭据路径必须继续拦——不得为降误报而放走真凭据。"""
    assert checks._is_read_sensitive("/home/u/.env") is True
    assert checks._is_read_sensitive("/home/u/.env.local") is True
    assert checks._is_read_sensitive("/home/u/.ssh/id_rsa") is True
    assert checks._is_read_sensitive("/home/u/.aws/credentials") is True
    assert checks._is_read_sensitive("/proj/credentials.json") is True
    assert checks._is_read_sensitive("/proj/secrets") is True
    assert checks._is_read_sensitive("/proj/secrets.yaml") is True
    assert checks._is_read_sensitive("/proj/secret.txt") is True
    assert checks._is_read_sensitive("/proj/password.txt") is True


def test_sensitive_read_returns_none_for_hyphenated_dir(tmp_path, monkeypatch):
    """端到端：读取 secret-leak 目录下的普通文本不应触发 ASK_USER。"""
    d = tmp_path / "secret-leak"
    d.mkdir()
    f = d / "transcript.txt"
    f.write_text("hello, no credentials here\n", encoding="utf-8")
    monkeypatch.setattr(checks, "_resolve_read_path", lambda _raw: f)
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(f)}}
    assert checks._check_sensitive_read(payload) is None
