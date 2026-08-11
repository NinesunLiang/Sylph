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
    monkeypatch.setenv("CARROROS_TOKEN_PATH", "")
    return tokens, tasks


def write_token(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_init_does_not_archive_unrelated_active_token(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    other_dir = tasks / "task-b"
    other_path = tokens / "20260811" / "task-b.json"
    original = token("task-b", other_dir)
    write_token(other_path, original)

    task_dir = tasks / "task-a"
    assert carros_base.cmd_init("task-a", steps=["S1"], task_dir=str(task_dir)) == 0

    assert json.loads(other_path.read_text(encoding="utf-8")) == original
    created = tokens / "20260811" / "task-a.json"
    assert json.loads(created.read_text(encoding="utf-8"))["session"]["id"] == "task-a"


def test_unbound_lookup_does_not_select_other_active_token(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    first_path = tokens / "20260811" / "task-a.json"
    other_path = tokens / "20260811" / "task-b.json"
    write_token(first_path, token("task-a", tasks / "task-a"))
    write_token(other_path, token("task-b", tasks / "task-b"))

    found, found_path = carros_base._find_latest_token()

    assert found is None
    assert found_path is None


def test_single_active_token_remains_compatible(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    only_path = tokens / "20260811" / "task-a.json"
    write_token(only_path, token("task-a", tasks / "task-a"))

    found, found_path = carros_base._find_latest_token()

    assert found["session"]["id"] == "task-a"
    assert found_path == only_path


def test_task_id_selector_isolated(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    first_path = tokens / "20260811" / "task-a.json"
    other_path = tokens / "20260811" / "task-b.json"
    write_token(first_path, token("task-a", tasks / "task-a"))
    write_token(other_path, token("task-b", tasks / "task-b"))
    monkeypatch.setenv("CARROROS_TASK_ID", "task-b")

    found, found_path = carros_base._find_latest_token()

    assert found["session"]["id"] == "task-b"
    assert found_path == other_path


def test_selector_mismatch_fails_closed(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    first_path = tokens / "20260811" / "task-a.json"
    other_path = tokens / "20260811" / "task-b.json"
    write_token(first_path, token("task-a", tasks / "task-a"))
    write_token(other_path, token("task-b", tasks / "task-b"))
    monkeypatch.setenv("CARROROS_TASK_ID", "missing")

    found, found_path = carros_base._find_latest_token()

    assert found is None
    assert found_path is None


def test_explicit_token_path_is_the_only_lookup_context(tmp_path, monkeypatch):
    tokens, tasks = configure_paths(tmp_path, monkeypatch)
    other_path = tokens / "20260811" / "task-b.json"
    write_token(other_path, token("task-b", tasks / "task-b"))
    monkeypatch.setenv("CARROROS_TOKEN_PATH", str(other_path))

    found, found_path = carros_base._find_latest_token()

    assert found["session"]["id"] == "task-b"
    assert found_path == other_path
