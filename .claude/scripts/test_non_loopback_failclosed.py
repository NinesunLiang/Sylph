"""P0-5: sub-agent dispatch/execution must fail-closed on non-loopback endpoints.

Regression for Benchmarking index5 P1. The executor and manager read
ANTHROPIC_BASE_URL from the environment and would call any remote host. The
default must be loopback-only; a remote endpoint requires an explicit
CARROROS_ALLOW_REMOTE_AGENT=1 override (human-authorized, high-risk).
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".claude" / "scripts"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


result_mod = load(SCRIPTS / "sub_agent_result.py", "sub_agent_result_under_test")
executor_mod = load(SCRIPTS / "sub_agent_executor.py", "sub_agent_executor_under_test")
manager_mod = load(SCRIPTS / "sub_agent_manager.py", "sub_agent_manager_under_test")

LOOPBACK_URLS = ["http://127.0.0.1:9998", "http://localhost:9998", "http://[::1]:9998"]
REMOTE_URLS = ["https://api.anthropic.com", "http://192.168.1.50:8080", "https://proxy.example.com"]


# ── is_loopback_url ──────────────────────────────────────────────────

def test_loopback_urls_are_allowed():
    for url in LOOPBACK_URLS:
        assert result_mod.is_loopback_url(url), url


def test_remote_urls_are_rejected():
    for url in REMOTE_URLS:
        assert not result_mod.is_loopback_url(url), url


def test_invalid_url_is_rejected():
    assert not result_mod.is_loopback_url("not-a-url")
    assert not result_mod.is_loopback_url("")


# ── executor API-call boundary fail-closed ───────────────────────────

def test_executor_construction_with_remote_url_is_allowed(tmp_path, monkeypatch):
    """Construction must not over-block: a remote-configured endpoint is a
    legitimate config; the guard lives at the call boundary."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.example.com")
    monkeypatch.delenv("CARROROS_ALLOW_REMOTE_AGENT", raising=False)
    executor_mod.SubAgentExecutor(tmp_path)


def test_executor_call_api_blocks_remote_without_override(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.example.com")
    monkeypatch.delenv("CARROROS_ALLOW_REMOTE_AGENT", raising=False)
    ex = executor_mod.SubAgentExecutor(tmp_path)

    with pytest.raises(RuntimeError) as exc:
        ex._call_api("do something")
    assert "non-loopback" in str(exc.value)


def test_executor_call_api_allows_remote_with_override(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("CARROROS_ALLOW_REMOTE_AGENT", "1")
    ex = executor_mod.SubAgentExecutor(tmp_path)
    assert ex.agent_url == "https://api.example.com"


# ── manager spawn fail-closed ────────────────────────────────────────

def test_manager_refuses_remote_spawn_without_override(tmp_path, monkeypatch):
    task_dir = tmp_path / "task"
    sub_dir = task_dir / "sub_task" / "sub-S1"
    sub_dir.mkdir(parents=True)
    (sub_dir / "result.json").write_text(json.dumps({"status": "pending"}), encoding="utf-8")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.example.com")
    monkeypatch.delenv("CARROROS_ALLOW_REMOTE_AGENT", raising=False)

    calls = []
    monkeypatch.setattr(manager_mod.sb, "Popen", lambda *a, **k: calls.append(a) or object())

    mgr = manager_mod.SubAgentManager(task_dir)
    mgr._spawn_subagent(sub_dir, "S1")

    assert calls == []
    result = json.loads((sub_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
