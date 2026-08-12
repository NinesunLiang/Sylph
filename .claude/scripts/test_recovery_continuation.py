"""Focused regressions for recovery continuation (index12 S4 / P2-7).

index11 finding: recovery produced a summary-only resume and never signalled that
continuation was attempted, so a compacted agent had no actionable next step. This
suite locks in (1) a "## Next Action" section derived from pending/non-terminal work,
and (2) a structured continuation artifact that marks continuation_attempted=True.
"""
import json

from sub_agent_recovery import RecoveryCheckpoint


def test_resume_has_next_action_for_pending_work(tmp_path):
    task = tmp_path / "task"
    task.mkdir()
    (task / "plan.md").write_text(
        "# Plan\n- [x] S1: baseline done\n- [ ] S2: pending\n- [ ] S3: pending\n",
        encoding="utf-8",
    )
    resume = RecoveryCheckpoint(task).generate_resume()
    assert "## Next Action" in resume
    # next pending step must be identifiable
    assert "S2" in resume


def test_resume_terminal_task_has_no_next_action(tmp_path):
    task = tmp_path / "task"
    task.mkdir()
    (task / "plan.md").write_text("# Plan\n- [x] S1: done\n- [x] S2: done\n", encoding="utf-8")
    resume = RecoveryCheckpoint(task).generate_resume()
    assert "## Next Action" not in resume


def test_continuation_artifact_marks_attempted(tmp_path):
    task = tmp_path / "task"
    task.mkdir()
    (task / "plan.md").write_text(
        "# Plan\n- [x] S1: done\n- [ ] S2: pending\n",
        encoding="utf-8",
    )
    rc = RecoveryCheckpoint(task)
    info = rc.save_continuation()
    assert info["continuation_attempted"] is True
    assert "S2" in info["pending_steps"]
    cont = task / "state" / "continuation.json"
    assert cont.exists()
    data = json.loads(cont.read_text(encoding="utf-8"))
    assert data["next_step"] == "S2"


def test_continuation_artifact_for_terminal_subtask(tmp_path):
    task = tmp_path / "task"
    sub = task / "sub_task" / "sub-S1"
    sub.mkdir(parents=True)
    (sub / "result.json").write_text(json.dumps({"status": "completed", "summary": "done"}))
    rc = RecoveryCheckpoint(task, step_id="S1")
    info = rc.save_continuation()
    assert info["continuation_attempted"] is False  # terminal → no continuation needed
    assert info["next_step"] is None
