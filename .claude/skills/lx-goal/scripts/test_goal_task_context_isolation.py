import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py"
spec = importlib.util.spec_from_file_location("lx_goal_task_context_under_test", GOAL)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _task_fixture(root: Path, name: str) -> tuple[Path, Path]:
    plan_dir = root / ".omc" / "tasks" / "20260811" / name
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    (plan_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (plan_dir / "executor.md").write_text("# Executor\n\n## Acceptance Checklist\n- [x] S1 complete\n", encoding="utf-8")
    token_path = root / ".omc" / "tokens" / "20260811" / f"{name}.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": name},
                "task_dir": str(plan_dir),
                "status": "active",
                "goal": {"state": "VERIFYING", "description": name},
            }
        ),
        encoding="utf-8",
    )
    token_path.with_suffix(token_path.suffix + ".lock").touch()
    return plan_dir, token_path


def test_goal_off_requires_explicit_task_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / ".omc" / "tokens")

    with pytest.raises(SystemExit):
        module.cmd_off()


def test_goal_off_only_finalizes_selected_task(monkeypatch, tmp_path):
    project = tmp_path / "project"
    task_a, token_a = _task_fixture(project, "goal-a")
    _, token_b = _task_fixture(project, "goal-b")
    monkeypatch.setattr(module, "PROJECT_ROOT", project)
    monkeypatch.setattr(module, "TOKENS_DIR", project / ".omc" / "tokens")
    monkeypatch.setattr(module, "STATE_DIR", project / ".omc" / "state")
    monkeypatch.setattr(module, "cmd_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "plan_step_count", lambda path: 1)
    monkeypatch.setattr(module, "incomplete_plan_steps", lambda path: [])
    monkeypatch.setattr(module, "missing_verified_evidence", lambda path: [])

    module.cmd_off(task_a)

    assert json.loads(token_a.read_text(encoding="utf-8"))["status"] == "completed"
    assert not token_a.with_suffix(token_a.suffix + ".lock").exists()
    assert json.loads(token_b.read_text(encoding="utf-8"))["status"] == "active"
    assert token_b.with_suffix(token_b.suffix + ".lock").exists()
    assert not (project / ".omc" / "state" / "tokens" / "lx-goal.json").exists()


def test_goal_context_rejects_cross_task_token(monkeypatch, tmp_path):
    project = tmp_path / "project"
    task_a, token_a = _task_fixture(project, "goal-a")
    task_b, _ = _task_fixture(project, "goal-b")
    token_a.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "goal-b"},
                "task_dir": str(task_b),
                "status": "active",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "TOKENS_DIR", project / ".omc" / "tokens")

    with pytest.raises(RuntimeError, match="task_id mismatch|task_dir mismatch"):
        module._goal_context(task_a)
