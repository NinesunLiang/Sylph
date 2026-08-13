"""Goal activation must not inspect unrelated unfinished tasks."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py"
spec = importlib.util.spec_from_file_location("lx_goal_activation_isolation", GOAL)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_unrelated_active_token(root: Path) -> Path:
    token_dir = root / ".omc" / "tokens" / "20260813"
    token_dir.mkdir(parents=True)
    token = token_dir / "other-unfinished.json"
    token.write_text(
        json.dumps(
            {
                "mode": "goal",
                "session": {"id": "other-unfinished"},
                "status": "active",
                "goal": {"state": "EXECUTING"},
            }
        ),
        encoding="utf-8",
    )
    token.with_suffix(".json.lock").touch()
    return token


def test_goal_activation_no_longer_uses_global_duplicate_guard(monkeypatch, tmp_path):
    """The default activation path creates a unique slug without scanning tokens."""
    _write_unrelated_active_token(tmp_path)
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / ".omc" / "tokens")
    monkeypatch.setattr(module, "_goal_slug", lambda _goal: "fresh-goal")
    monkeypatch.setattr(module, "_find_active_goal", lambda *_args, **_kwargs: pytest.fail("global scan must not run"))

    plan_dir = tmp_path / ".omc" / "tasks" / "20260813" / "fresh-goal"
    plan_dir.mkdir(parents=True)
    for name in ("plan.md", "research.md", "executor.md"):
        (plan_dir / name).write_text("# fixture\n", encoding="utf-8")
    token_dir = tmp_path / ".omc" / "tokens" / "20260813"
    token_dir.mkdir(parents=True, exist_ok=True)
    token_path = token_dir / "fresh-goal.json"
    token_path.write_text(json.dumps({"session": {"id": "fresh-goal"}}), encoding="utf-8")

    class Result:
        returncode = 0
        stdout = f"CARROROS_TASK_DIR={plan_dir}\n"
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: Result())
    module.cmd_on("fresh goal")
    assert token_path.exists()
