"""Focused regressions for sub-agent process-group isolation (index12 S5 / P2-8).

Before the fix the manager spawned the worker without a new session, and cancel/timeout
terminated only the direct child, orphaning grandchildren (e.g. a curl the worker spawned).
This suite locks in: (1) worker spawns in its own process group (start_new_session),
(2) cancel kills the whole group, (3) timeout kills the whole group.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from sub_agent_manager import SubAgentManager


@pytest.fixture(autouse=True)
def _loopback_env(monkeypatch):
    # This suite exercises process-group isolation, not endpoint policy; pin a
    # loopback endpoint so the spawn-level fail-closed guard does not preempt it.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:1")


def make_manager(tmp_path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    manager = SubAgentManager(task_dir, project_root=tmp_path)
    plan = {
        "plan_id": "pg-matrix",
        "max_retries": 0,
        "steps": [{"id": "S1", "goal": "process group test"}],
    }
    manager.distribute(plan)
    return manager, task_dir / "sub_task" / "sub-S1"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _wait_for_pidfile(path: Path, timeout: float = 3.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            try:
                return int(path.read_text().strip())
            except (OSError, ValueError):
                pass
        time.sleep(0.05)
    raise AssertionError(f"grandchild pid file not written: {path}")


def _install_fake_executor(tmp_path, body: str):
    fake = tmp_path / ".omc" / "scripts" / "sub_agent_executor.py"
    fake.parent.mkdir(parents=True)
    fake.write_text(body, encoding="utf-8")


GRANDCHILD_SLEEP = (
    "import subprocess, time\n"
    "gc = subprocess.Popen(['sleep', '30'])\n"
    "open('gc.pid', 'w').write(str(gc.pid))\n"
    "time.sleep(30)\n"
)

# Timeout path: poll only marks a timeout for status==running with a started_at.
TIMEOUT_GRANDCHILD = (
    "import json, subprocess, sys, time\n"
    "from datetime import datetime, timezone, timedelta\n"
    "sub = sys.argv[1]\n"
    "open(sub + '/result.json', 'w').write(json.dumps({"
    "'status': 'running', "
    "'started_at': (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()}))\n"
    "gc = subprocess.Popen(['sleep', '30'])\n"
    "open('gc.pid', 'w').write(str(gc.pid))\n"
    "time.sleep(30)\n"
)


def test_cancel_kills_whole_process_group(tmp_path):
    _install_fake_executor(tmp_path, GRANDCHILD_SLEEP)
    manager, sub_dir = make_manager(tmp_path)
    manager._spawn_subagent(sub_dir, "S1")
    proc = manager._spawned_procs.get("S1")
    assert proc is not None
    gc_pid = _wait_for_pidfile(tmp_path / "gc.pid")
    assert _alive(gc_pid), "grandchild must be alive before cancel"
    assert manager.cancel("S1", "process-group kill test") is True
    time.sleep(0.3)
    assert not _alive(gc_pid), "grandchild must be killed with the group"


def test_timeout_kills_whole_process_group(tmp_path):
    _install_fake_executor(tmp_path, TIMEOUT_GRANDCHILD)
    manager, sub_dir = make_manager(tmp_path)
    manager.set_config(timeout=1)
    manager._spawn_subagent(sub_dir, "S1")
    proc = manager._spawned_procs.get("S1")
    assert proc is not None
    gc_pid = _wait_for_pidfile(tmp_path / "gc.pid")
    assert _alive(gc_pid)
    # poll will detect timeout for the running step and must kill the group
    snapshot = manager.poll()
    assert snapshot["steps"][0]["status"] == "timeout"
    time.sleep(0.3)
    assert not _alive(gc_pid), "grandchild must be killed on timeout"


def test_worker_runs_in_own_session(tmp_path):
    _install_fake_executor(
        tmp_path,
        "import os, time\n"
        "open('pgid.pid', 'w').write(str(os.getpgrp()))\n"
        "time.sleep(30)\n",
    )
    manager, sub_dir = make_manager(tmp_path)
    manager._spawn_subagent(sub_dir, "S1")
    proc = manager._spawned_procs.get("S1")
    assert proc is not None
    worker_pgid = _wait_for_pidfile(tmp_path / "pgid.pid")
    assert worker_pgid == proc.pid, (
        f"worker must be its own process group leader (pgid={worker_pgid}, pid={proc.pid})"
    )
    manager.cancel("S1", "cleanup")
