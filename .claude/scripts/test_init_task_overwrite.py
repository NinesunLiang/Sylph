"""P0-3: cmd_init must fail-closed when the task-id already exists.

Regression for Benchmarking index7 P0 "explicit task ID 仍可覆盖已有 task/token".
Overwriting an existing token / non-empty task dir is irreversible, so it must
be refused unless the caller explicitly passes force=True (human-authorized).
"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "carros_base.py"
spec = importlib.util.spec_from_file_location("carros_base_under_test", SCRIPT)
assert spec is not None
carros_base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(carros_base)


def token(task_id, task_dir, status="active"):
    return {
        "session": {"id": task_id},
        "task_dir": str(task_dir),
        "status": status,
        "task": {"status": status, "current_step": "S1"},
        "stats": {"done": 0, "total": 1},
    }


def configure_paths(tmp_path, monkeypatch):
    tokens = tmp_path / "tokens"
    tasks = tmp_path / "tasks"
    tokens.mkdir()
    tasks.mkdir()
    monkeypatch.setattr(carros_base, "OMC_TOKENS", tokens)
    monkeypatch.setattr(carros_base, "OMC_TASKS", tasks)
    monkeypatch.setattr(carros_base, "OMC_ROOT", tmp_path)
    monkeypatch.setattr(carros_base, "_write_handoff", lambda *a, **k: None)
    monkeypatch.setenv("CARROROS_TOKEN_PATH", "")
    return tokens, tasks


def write_token(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ── _task_token_exists ─────────────────────────────────────────────

def test_token_exists_no_token_returns_none(tmp_path, monkeypatch):
    tokens, _ = configure_paths(tmp_path, monkeypatch)
    assert carros_base._task_token_exists("ghost") is None


def test_token_exists_finds_same_session_id_across_dates(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    hit = tokens / "20260811" / "task-a.json"
    other = tokens / "20260812" / "task-b.json"
    write_token(hit, token("task-a", tasks / "task-a"))
    write_token(other, token("task-b", tasks / "task-b"))

    found = carros_base._task_token_exists("task-a")

    assert found == hit


def test_token_exists_ignores_lock_files(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    write_token(tokens / "20260811" / "task-a.json", token("task-a", tasks / "task-a"))
    (tokens / "20260811" / "task-a.json.lock").write_text("sidecar\n")

    assert carros_base._task_token_exists("task-a") is not None


# ── cmd_init fail-closed ───────────────────────────────────────────

def test_init_refuses_existing_token_without_force(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    task_dir = tasks / "task-a"
    write_token(tokens / "20260811" / "task-a.json", token("task-a", task_dir))

    rc = carros_base.cmd_init("task-a", steps=["S1"], task_dir=str(task_dir))

    assert rc == 2


def test_init_refuses_nonempty_task_dir_without_force(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    task_dir = tasks / "task-a"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "plan.md").write_text("# existing\n")

    rc = carros_base.cmd_init("task-a", steps=["S1"], task_dir=str(task_dir))

    assert rc == 2


def test_init_force_overwrites_existing_token(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    task_dir = tasks / "task-a"
    write_token(tokens / "20260811" / "task-a.json", token("task-a", task_dir))

    rc = carros_base.cmd_init("task-a", steps=["S1"], task_dir=str(task_dir), force=True)

    assert rc == 0


def test_init_fresh_task_still_succeeds(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    task_dir = tasks / "task-b"

    rc = carros_base.cmd_init("task-b", steps=["S1"], task_dir=str(task_dir))

    assert rc == 0
    created = next(tokens.glob("*/task-b.json"))
    assert json.loads(created.read_text(encoding="utf-8"))["session"]["id"] == "task-b"
