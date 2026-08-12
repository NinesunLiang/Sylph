import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    for module_name in list(sys.modules):
        if module_name == "lib" or module_name.startswith("lib."):
            del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_task(tmp_path: Path) -> tuple[Path, Path]:
    task_dir = tmp_path / "task-a"
    task_dir.mkdir()
    (task_dir / "plan.md").write_text("- [ ] S1: continue\n", encoding="utf-8")
    (task_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    (task_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    token_path = tmp_path / "token.json"
    write_json(
        token_path,
        {
            "session": {"id": "task-a", "level": "L1"},
            "task": {"id": "task-a", "status": "active", "current_step": "S1", "scope": []},
            "status": "active",
            "stats": {"done": 0, "total": 1},
        },
    )
    return token_path, task_dir


def run_hook(module, payload: dict) -> None:
    original = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        with pytest.raises(SystemExit) as exc_info:
            module.main()
        assert exc_info.value.code == 0
    finally:
        sys.stdin = original


def test_precompact_passes_session_id_to_compact_write(monkeypatch, tmp_path):
    module = load_module("precompact_isolation", ROOT / ".claude/hooks/precompact-lifecycle.py")
    token_path, task_dir = make_task(tmp_path)
    calls = []

    class Result:
        returncode = 0
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(module, "_latest_token", lambda: token_path)
    monkeypatch.setattr(module, "_resolve_task_dir", lambda _: task_dir)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._refresh_compact_write("sid-a") == "ok"
    assert "--session-id" in calls[0]
    assert calls[0][calls[0].index("--session-id") + 1] == "sid-a"


def test_precompact_without_session_id_does_not_refresh(monkeypatch, tmp_path):
    module = load_module("precompact_missing_session", ROOT / ".claude/hooks/precompact-lifecycle.py")
    token_path, task_dir = make_task(tmp_path)
    monkeypatch.setattr(module, "_latest_token", lambda: token_path)
    monkeypatch.setattr(module, "_resolve_task_dir", lambda _: task_dir)
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: pytest.fail("unexpected refresh"))

    assert module._refresh_compact_write("") == "skipped:no_session_id"


def test_compact_write_capsule_is_session_bound(monkeypatch, tmp_path):
    module = load_module("context_engine_isolation", ROOT / ".claude/scripts/context_engine.py")
    token_path, task_dir = make_task(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)

    assert module.compact_write(token_path, task_dir, session_id="sid-a") == 0
    capsule_path = tmp_path / ".omc/state/resume-capsule.json"
    capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
    assert capsule["session_id"] == "sid-a"
    assert capsule["plan_dir"] == str(task_dir)


def test_compact_write_includes_document_pointers_and_checklist(monkeypatch, tmp_path):
    module = load_module("context_engine_documents", ROOT / ".claude/scripts/context_engine.py")
    token_path, task_dir = make_task(tmp_path)
    (task_dir / "executor.md").write_text(
        "# Executor\n- [x] S1 evidence\n- [ ] S2 pending\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)

    assert module.compact_write(token_path, task_dir, user_prompt="last query", session_id="sid-a") == 0

    handoff = (tmp_path / ".omc/session-handoff.md").read_text(encoding="utf-8")
    assert f"task_dir: {task_dir}" in handoff
    assert f"plan: {task_dir / 'plan.md'}" in handoff
    assert f"checklist: {task_dir / 'state' / 'checklist.md'}" in handoff
    assert "- [x] S1 evidence" in handoff
    assert "- [ ] S2 pending" in handoff
    prompts = (tmp_path / ".omc/state/last-user-prompt.md").read_text(encoding="utf-8")
    assert "last query" in prompts
    assert not (task_dir / "state/session-handoff.md").exists()


def write_capsule(tmp_path: Path, session_id: str) -> tuple[Path, Path]:
    token_path, task_dir = make_task(tmp_path)
    capsule_path = tmp_path / ".omc/state/resume-capsule.json"
    write_json(
        capsule_path,
        {
            "active_token": str(token_path),
            "plan_dir": str(task_dir),
            "current_step": "S1",
            "task_id": "task-a",
            "session_id": session_id,
        },
    )
    return capsule_path, task_dir


def test_postcompact_consumes_matching_capsule(monkeypatch, tmp_path):
    capsule_path, _ = write_capsule(tmp_path, "sid-a")
    module = load_module("postcompact_matching", ROOT / ".claude/hooks/postcompact.py")
    monkeypatch.setattr(module, "ROOT", tmp_path)

    run_hook(module, {"session_id": "sid-a"})

    note = tmp_path / ".omc/state/resume-note.md"
    assert note.exists()
    assert "session_id=sid-a" in note.read_text(encoding="utf-8")
    assert not capsule_path.exists()


def test_session_start_injects_bound_handoff_and_recent_prompts(monkeypatch, tmp_path, capsys):
    module = load_module("session_start_bound_resume", ROOT / ".claude/hooks/session-start.py")
    task_dir = tmp_path / "tasks" / "20260811" / "task-a"
    state_dir = task_dir / "state"
    state_dir.mkdir(parents=True)
    (tmp_path / ".omc/session-handoff.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".omc/session-handoff.md").write_text(
        f"task_dir: {task_dir}\nchecklist: {state_dir / 'checklist.md'}\n",
        encoding="utf-8",
    )
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "state/last-user-prompt.md").write_text("last query from user\n", encoding="utf-8")
    note = tmp_path / "state/resume-note.md"
    note.write_text(
        f"session_id=sid-a\ntask=task-a\ntask_dir={task_dir}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "OMC", tmp_path)
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "STEPWISE_STATE", tmp_path / "stepwise")

    original = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"source": "compact", "session_id": "sid-a"}))
    try:
        with pytest.raises(SystemExit) as exc_info:
            module.main()
        assert exc_info.value.code == 0
    finally:
        sys.stdin = original

    output = json.loads(capsys.readouterr().out)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "session-handoff.md" in context
    assert "last query from user" in context
    assert not note.exists()


def test_postcompact_keeps_foreign_capsule(monkeypatch, tmp_path):
    capsule_path, _ = write_capsule(tmp_path, "sid-a")
    module = load_module("postcompact_foreign", ROOT / ".claude/hooks/postcompact.py")
    monkeypatch.setattr(module, "ROOT", tmp_path)

    run_hook(module, {"session_id": "sid-b"})

    assert capsule_path.exists()
    assert not (tmp_path / ".omc/state/resume-note.md").exists()


def test_session_start_startup_does_not_inject_global_task(monkeypatch, tmp_path, capsys):
    module = load_module("session_start_startup", ROOT / ".claude/hooks/session-start.py")
    handoff = tmp_path / "session-handoff.md"
    handoff.write_text("foreign task\n", encoding="utf-8")
    monkeypatch.setattr(module, "HANDOFF", handoff)
    monkeypatch.setattr(module, "LAST_PROMPTS", tmp_path / "last-user-prompt.md")
    monkeypatch.setattr(module, "OMC", tmp_path)
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "STEPWISE_STATE", tmp_path / "stepwise")

    original = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"source": "startup", "session_id": "sid-b"}))
    try:
        with pytest.raises(SystemExit) as exc_info:
            module.main()
        assert exc_info.value.code == 0
    finally:
        sys.stdin = original

    output = json.loads(capsys.readouterr().out)
    assert output == {"continue": True}


def test_session_start_consumes_matching_resume_note(monkeypatch, tmp_path, capsys):
    module = load_module("session_start_matching", ROOT / ".claude/hooks/session-start.py")
    note = tmp_path / "state/resume-note.md"
    note.parent.mkdir(parents=True)
    note.write_text("session_id=sid-a\n[AUTO-RESUME] task-a\n", encoding="utf-8")
    monkeypatch.setattr(module, "OMC", tmp_path)
    monkeypatch.setattr(module, "HANDOFF", tmp_path / "missing-handoff.md")
    monkeypatch.setattr(module, "LAST_PROMPTS", tmp_path / "missing-prompts.md")
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "STEPWISE_STATE", tmp_path / "stepwise")

    original = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"source": "compact", "session_id": "sid-a"}))
    try:
        with pytest.raises(SystemExit) as exc_info:
            module.main()
        assert exc_info.value.code == 0
    finally:
        sys.stdin = original

    output = json.loads(capsys.readouterr().out)
    assert "AUTO-RESUME" in output["hookSpecificOutput"]["additionalContext"]
    assert not note.exists()


def test_session_start_injects_live_stepwise_on_compact(monkeypatch, tmp_path, capsys):
    module = load_module("session_start_stepwise", ROOT / ".claude/hooks/session-start.py")
    stepwise = tmp_path / "stepwise"
    stepwise.mkdir(parents=True)
    (stepwise / "task.json").write_text(
        json.dumps({
            "task_id": "task",
            "current_card": "C08",
            "passed": ["C00", "C01"],
            "status": "active",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "OMC", tmp_path)
    monkeypatch.setattr(module, "HANDOFF", tmp_path / "missing-handoff.md")
    monkeypatch.setattr(module, "LAST_PROMPTS", tmp_path / "missing-prompts.md")
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(module, "STEPWISE_STATE", stepwise)

    original = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"source": "compact", "session_id": "sid-a"}))
    try:
        with pytest.raises(SystemExit) as exc_info:
            module.main()
        assert exc_info.value.code == 0
    finally:
        sys.stdin = original

    output = json.loads(capsys.readouterr().out)
    assert output == {"continue": True}
