import json
from datetime import datetime, timedelta, timezone

from sub_agent_executor import SubAgentExecutor
from sub_agent_manager import SubAgentManager
from sub_agent_recovery import RecoveryCheckpoint


def make_manager(tmp_path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    manager = SubAgentManager(task_dir, project_root=tmp_path)
    plan = {
        "plan_id": "offline-matrix",
        "max_retries": 1,
        "steps": [{"id": "S1", "goal": "offline test"}],
    }
    manager.distribute(plan)
    return manager, task_dir / "sub_task" / "sub-S1"


def write_result(sub_dir, value):
    (sub_dir / "result.json").write_text(value, encoding="utf-8")


def test_empty_result_is_bounded_failed(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    write_result(sub_dir, "{}")
    result = manager.poll()
    assert result["status"] == "has_failed"
    assert result["steps"][0]["status"] == "failed"


def test_malformed_result_is_bounded_failed(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    write_result(sub_dir, "not-json")
    result = manager.poll()
    assert result["steps"][0]["status"] == "failed"
    assert "malformed" in result["steps"][0]["failure"]


def test_empty_executor_output_is_failed(tmp_path):
    _, sub_dir = make_manager(tmp_path)
    executor = SubAgentExecutor(sub_dir)
    executor._call_api = lambda _instruction: ""
    result = executor.run()
    assert result["status"] == "failed"
    assert "empty" in result["failure"]


def test_crash_cancel_timeout_and_retry_cap_are_terminal(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    write_result(sub_dir, json.dumps({"status": "failed", "failure": "process crashed", "retry_count": 1, "max_retries": 1}))
    assert manager.poll()["steps"][0]["status"] == "failed"
    assert manager.retry("S1") is False
    assert json.loads((sub_dir / "result.json").read_text())["status"] == "failed"

    write_result(sub_dir, json.dumps({"status": "running", "started_at": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()}))
    manager.set_config(timeout=1)
    assert manager.poll()["steps"][0]["status"] == "timeout"

    assert manager.cancel("S1", "cancelled by matrix") is True
    assert json.loads((sub_dir / "result.json").read_text())["status"] == "cancelled"


def test_resume_is_takeover_evidence(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    write_result(sub_dir, json.dumps({"status": "failed", "failure": "crash", "retry_count": 1}))
    resume = RecoveryCheckpoint(manager.task_dir, step_id="S1").generate_resume()
    assert "Status: failed" in resume
    assert "crash" in resume
    assert "Retry count: 1" in resume
