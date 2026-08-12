"""Focused regressions for sub-agent diagnostic/reliability fixes (index11 S5).

Covers three D2 candidate defects:
  - #19 spawn message misleadingly says "claude CLI" while launching a Python executor
  - #6 Popen stdout/stderr are DEVNULL'd so crash diagnostics are lost
  - #5 non-loopback Agent endpoint is not fail-closed (task data could leak to an
    arbitrary host with the fixture key)

Red-first: these tests fail on the pre-fix code and pass after the minimal repair.
"""
import json

import pytest

from sub_agent_executor import SubAgentExecutor
from sub_agent_manager import SubAgentManager


def make_manager(tmp_path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    manager = SubAgentManager(task_dir, project_root=tmp_path)
    plan = {
        "plan_id": "diag-matrix",
        "max_retries": 0,
        "steps": [{"id": "S1", "goal": "diagnostics test"}],
    }
    manager.distribute(plan)
    return manager, task_dir / "sub_task" / "sub-S1"


FAKE_CRASHER = (
    "import sys\n"
    "sys.stderr.write('FAKE_CRASH_STDERR_DIAGNOSTIC\\n')\n"
    "sys.stdout.write('FAKE_STDOUT_DIAGNOSTIC\\n')\n"
    "sys.exit(1)\n"
)


def test_spawn_captures_crash_stderr_and_honest_label(tmp_path, capsys, monkeypatch):
    """#6 stderr captured to a per-step log + #19 label reflects the real worker."""
    # This test exercises crash diagnostics, not endpoint policy. Pin a loopback
    # endpoint so the spawn-level fail-closed guard (which reads the inherited
    # ANTHROPIC_BASE_URL) does not preempt the fake worker.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:1")
    fake_script = tmp_path / ".omc" / "scripts" / "sub_agent_executor.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text(FAKE_CRASHER, encoding="utf-8")

    manager, sub_dir = make_manager(tmp_path)
    manager._spawn_subagent(sub_dir, "S1")
    proc = manager._spawned_procs.get("S1")
    assert proc is not None, "subagent must be spawned"
    proc.wait(timeout=10)

    out = capsys.readouterr().out
    # #19: message must not mislead as the claude CLI when we launch the python worker
    assert "claude CLI" not in out
    assert "sub_agent_executor" in out

    # #6: crash stderr must be retained on disk, not DEVNULL'd
    log = sub_dir / "executor.log"
    assert log.exists(), "per-step executor log must be created"
    assert "FAKE_CRASH_STDERR_DIAGNOSTIC" in log.read_text(encoding="utf-8")


def _no_network(*args, **kwargs):
    raise AssertionError("network must not be reached")


def test_non_loopback_endpoint_fails_closed(tmp_path, monkeypatch):
    """#5: non-loopback Agent endpoint must fail closed BEFORE any request."""
    _, sub_dir = make_manager(tmp_path)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://192.0.2.1")  # TEST-NET, non-loopback
    monkeypatch.setattr("subprocess.run", _no_network)
    executor = SubAgentExecutor(sub_dir)
    result = executor.run()
    assert result["status"] == "failed"
    failure = str(result["failure"])
    assert "non-loopback" in failure or "blocked" in failure


def test_loopback_endpoint_is_still_allowed(tmp_path, monkeypatch):
    """#5 guard must not block the legitimate loopback fixture path."""
    _, sub_dir = make_manager(tmp_path)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:1")  # loopback, closed port
    reached = {}
    def fake_run(*args, **kwargs):
        reached["called"] = True
        raise RuntimeError("curl exit 7: connection refused (loopback)")
    monkeypatch.setattr("subprocess.run", fake_run)
    executor = SubAgentExecutor(sub_dir)
    result = executor.run()
    assert reached.get("called"), "loopback must reach the connection layer"
    assert result["status"] == "failed"
    assert "non-loopback" not in str(result["failure"])
    assert "blocked" not in str(result["failure"])


def test_allowlist_env_can_bypass_non_loopback_guard(tmp_path, monkeypatch):
    """#5: CARROROS_ALLOW_NON_LOOPBACK=1 is the explicit escape hatch for authorized hosts."""
    _, sub_dir = make_manager(tmp_path)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://192.0.2.1")
    monkeypatch.setenv("CARROROS_ALLOW_REMOTE_AGENT", "1")
    reached = {}
    def fake_run(*args, **kwargs):
        reached["called"] = True
        raise RuntimeError("curl exit 28: connection timeout (allowlisted)")
    monkeypatch.setattr("subprocess.run", fake_run)
    executor = SubAgentExecutor(sub_dir)
    result = executor.run()
    assert reached.get("called"), "allowlisted non-loopback must reach the connection layer"
    assert result["status"] == "failed"
    assert "non-loopback" not in str(result["failure"])
    assert "blocked" not in str(result["failure"])


def test_loopback_default_without_env_is_allowed(tmp_path, monkeypatch):
    """#5: default loopback endpoint must pass the guard (only connection/API failures surface)."""
    _, sub_dir = make_manager(tmp_path)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    executor = SubAgentExecutor(sub_dir)
    try:
        executor._call_api("ping")
    except RuntimeError as exc:
        assert "non-loopback" not in str(exc)
        assert "blocked" not in str(exc)
