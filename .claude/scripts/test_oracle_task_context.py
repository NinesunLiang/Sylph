"""Task-bound autonomous detection for oracle_agent (concurrent-session isolation).

Regression for index11 E11-004: oracle_agent._is_autonomous_mode() read the
shared global markers `.omc/state/tokens/autonomous.active` + `lx-goal.json`,
so one terminal's goal task changed another terminal's oracle review. Task
state must live only in the task's own token; no global inference.
"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "oracle_agent.py"
spec = importlib.util.spec_from_file_location("oracle_agent_under_test", SCRIPT)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_goal_token(path, mode="goal", status="active"):
    path.write_text(
        json.dumps({
            "mode": mode,
            "status": status,
            "session": {"id": "task-x"},
            "goal": {"state": "EXECUTING", "description": "x"},
        }),
        encoding="utf-8",
    )


def test_goal_token_is_autonomous(tmp_path):
    tok = tmp_path / "goal.json"
    write_goal_token(tok)

    assert module._is_autonomous_mode(str(tok)) is True


def test_non_goal_token_not_autonomous(tmp_path):
    tok = tmp_path / "task.json"
    write_goal_token(tok, mode="task")

    assert module._is_autonomous_mode(str(tok)) is False


def test_no_token_ignores_global_markers():
    """Without a bound task token the oracle must NOT infer autonomous mode
    from the shared global markers, even when they exist."""
    assert module._is_autonomous_mode() is False
    assert module._is_autonomous_mode(None) is False


def test_missing_token_path_fail_closed(tmp_path):
    assert module._is_autonomous_mode(str(tmp_path / "missing.json")) is False


def test_review_static_threads_token_context(tmp_path, monkeypatch):
    tok = tmp_path / "goal.json"
    write_goal_token(tok)
    seen = []
    monkeypatch.setattr(module, "_is_autonomous_mode",
                        lambda token_path=None: (seen.append(token_path) or False))
    monkeypatch.setattr(module, "_try_llm_model", lambda *a, **k: (False, ""))

    module.review_static("t1", token_path=str(tok))

    assert seen == [str(tok)], f"token context not threaded, got {seen}"
