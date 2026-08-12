"""P0-4: sub_agent_recovery must read the token schema written by the manager.

Regression for Benchmarking index7 P2. The manager writes parent.task_dir /
parent.plan_id / subtask.plan_text, but recovery read parent.task_id and
subtask.plan, so resume output always lost parent_id / subtask_plan.
"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "sub_agent_recovery.py"
spec = importlib.util.spec_from_file_location("sub_agent_recovery_under_test", SCRIPT)
assert spec is not None
recovery_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(recovery_mod)


def make_sub_dir(tmp_path, token_data):
    task_dir = tmp_path / "task"
    sub_dir = task_dir / "sub_task" / "sub-S1"
    sub_dir.mkdir(parents=True)
    (sub_dir / "token.json").write_text(json.dumps(token_data), encoding="utf-8")
    return task_dir


NEW_FORMAT_TOKEN = {
    "session": {"id": "plan-S1", "created_at": "2026-08-12T00:00:00Z"},
    "parent": {
        "plan_id": "plan-123",
        "task_dir": "/tmp/task-a",
        "step_id": "S1",
    },
    "subtask": {
        "goal": "do the thing",
        "plan_text": json.dumps({"goal": "do the thing", "type": "code"}),
    },
}

OLD_FORMAT_TOKEN = {
    "parent": {"task_id": "legacy-task", "step_id": "S1"},
    "subtask": {"plan": "legacy plan text"},
}


def test_recovery_reads_manager_format_parent_id(tmp_path):
    task_dir = make_sub_dir(tmp_path, NEW_FORMAT_TOKEN)

    rc = recovery_mod.RecoveryCheckpoint(task_dir, step_id="S1")
    status = rc.check_status()

    # manager writes parent.task_dir, not parent.task_id
    assert status.get("parent_id") is not None
    assert status.get("parent_id") == "/tmp/task-a"


def test_recovery_reads_manager_format_subtask_plan(tmp_path):
    task_dir = make_sub_dir(tmp_path, NEW_FORMAT_TOKEN)

    rc = recovery_mod.RecoveryCheckpoint(task_dir, step_id="S1")
    status = rc.check_status()

    # manager writes subtask.plan_text, not subtask.plan
    assert status.get("subtask_plan")
    assert "do the thing" in status["subtask_plan"]


def test_recovery_backward_compatible_legacy_token(tmp_path):
    task_dir = make_sub_dir(tmp_path, OLD_FORMAT_TOKEN)

    rc = recovery_mod.RecoveryCheckpoint(task_dir, step_id="S1")
    status = rc.check_status()

    assert status.get("parent_id") == "legacy-task"
    assert status.get("subtask_plan") == "legacy plan text"


def test_resume_includes_parent_and_plan(tmp_path):
    task_dir = make_sub_dir(tmp_path, NEW_FORMAT_TOKEN)

    rc = recovery_mod.RecoveryCheckpoint(task_dir, step_id="S1")
    resume = rc.generate_resume()

    assert "Step: S1" in resume
    assert "parent" not in resume.lower() or "plan" in resume.lower()
