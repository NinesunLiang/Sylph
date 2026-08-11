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
    executor._call_api = lambda instruction: instruction[:0]
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

    write_result(sub_dir, json.dumps({"status": "running"}))
    assert manager.cancel("S1", "cancelled by matrix") is True
    assert json.loads((sub_dir / "result.json").read_text())["status"] == "cancelled"


def test_resume_is_takeover_evidence(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    write_result(sub_dir, json.dumps({"status": "failed", "failure": "crash", "retry_count": 1}))
    resume = RecoveryCheckpoint(manager.task_dir, step_id="S1").generate_resume()
    assert "Status: failed" in resume
    assert "crash" in resume
    assert "Retry count: 1" in resume


def test_auto_run_does_not_hide_failed_or_timeout(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    manager._wait_all = lambda: "has_failures"
    manager.retry_failed = lambda: []

    for status in ("failed", "timeout"):
        write_result(
            sub_dir,
            json.dumps({
                "status": status,
                "failure": f"{status} fixture",
                "retry_count": 1,
                "max_retries": 1,
            }),
        )
        result = manager.auto_run(wait=True)
        assert result["status"] == "has_failures"
        assert result["failed"] == 1
        assert result["collect_result"]["failed"] == [("S1", f"{status} fixture")]


def test_cancelled_result_rejects_late_executor_completion(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    executor = SubAgentExecutor(sub_dir)

    assert manager.cancel("S1", "cancelled before late write") is True
    executor._update_result("completed", summary="late completion", full_output="late")

    result = json.loads((sub_dir / "result.json").read_text())
    assert result["status"] == "cancelled"
    assert result["failure"] == "cancelled before late write"


def test_cancelled_result_is_not_collected_as_success(tmp_path):
    manager, _ = make_manager(tmp_path)
    assert manager.cancel("S1", "cancelled for test") is True

    collected = manager.collect("S1")

    assert collected["success"] is False
    assert "cancelled" in collected["error"]


def test_cancelled_is_terminal_in_poll_and_auto_run(tmp_path):
    manager, _ = make_manager(tmp_path)
    assert manager.cancel("S1", "cancelled for aggregation") is True

    snapshot = manager.poll()
    result = manager.auto_run(wait=True)

    assert snapshot["cancelled"] == 1
    assert snapshot["pending"] == 0
    assert result["status"] == "cancelled"
    assert result["cancelled"] == 1
    assert result["failed"] == 0


def test_timeout_is_persisted_and_rejects_late_completion(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    executor = SubAgentExecutor(sub_dir)
    write_result(
        sub_dir,
        json.dumps({
            "status": "running",
            "generation": 0,
            "started_at": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
        }),
    )
    manager.set_config(timeout=1)

    assert manager.poll()["steps"][0]["status"] == "timeout"
    assert json.loads((sub_dir / "result.json").read_text())["status"] == "timeout"
    assert executor._update_result(
        "completed",
        summary="late timeout completion",
        expected_generation=0,
        allowed_statuses={"running"},
    ) is False
    assert json.loads((sub_dir / "result.json").read_text())["status"] == "timeout"


def test_retry_generation_rejects_old_executor(tmp_path):
    manager, sub_dir = make_manager(tmp_path)
    old_executor = SubAgentExecutor(sub_dir)
    write_result(
        sub_dir,
        json.dumps({
            "status": "failed",
            "failure": "first attempt",
            "retry_count": 0,
            "max_retries": 1,
            "generation": 0,
        }),
    )

    assert manager.retry("S1") is True
    current = json.loads((sub_dir / "result.json").read_text())
    assert current["status"] == "pending"
    assert current["generation"] == 1
    assert old_executor._update_result(
        "completed",
        summary="old attempt",
        expected_generation=0,
        allowed_statuses={"running"},
    ) is False
    assert json.loads((sub_dir / "result.json").read_text())["status"] == "pending"
