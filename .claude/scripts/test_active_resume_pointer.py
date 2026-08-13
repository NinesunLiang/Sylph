"""Regression: active-resume pointer must not cross-task overlap (index19 M?).

Two concurrent tasks A and B: resume(A) writes pointer → resume(B) overwrites
it → A's later tick/verify reads pointer, lands on B, and mis-reads B's FAIL
records. Fix: resume refuses to overwrite a pointer that points to a different
still-active task (unless the pointed task is no longer active).
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import carros_base as cb


def _write_token(tok_dir, tid, status="active"):
    tok_dir.mkdir(parents=True, exist_ok=True)
    p = tok_dir / f"{tid}.json"
    p.write_text(json.dumps({
        "schema_version": "v1.0",
        "session": {"id": tid, "level": "L1"},
        "task_dir": str(tok_dir.parent),
        "status": status,
        "task": {"current_step": None, "status": "planning"},
        "stats": {"done": 0, "total": 1},
    }, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture
def fake_env(monkeypatch, tmp_path):
    """Point OMC dirs to tmp; inject fake lib.task_paths resolver for two tasks."""
    omc = tmp_path / "omc"
    (omc / "state").mkdir(parents=True)
    tokens = omc / "tokens"
    tokA = _write_token(tokens, "task-A")
    tokB = _write_token(tokens, "task-B")
    tA = omc / "tasks" / "20260813" / "task-A"
    tB = omc / "tasks" / "20260813" / "task-B"
    tA.mkdir(parents=True)
    tB.mkdir(parents=True)

    monkeypatch.setattr(cb, "OMC_ROOT", omc)
    monkeypatch.setattr(cb, "OMC_TOKENS", tokens)
    monkeypatch.setattr(cb, "OMC_TASKS", omc / "tasks")
    monkeypatch.setattr(cb, "cmd_report", lambda *a, **k: None)

    docs = {
        "task-A": {"date": "20260813", "slug": "task-A", "task_dir": tA, "token_path": tokA},
        "task-B": {"date": "20260813", "slug": "task-B", "task_dir": tB, "token_path": tokB},
    }
    lib_ns = type(sys)("lib")
    lib_ns.__path__ = [str(SCRIPTS_DIR / "lib")]
    lib_ns.resolve_task_document = lambda d: docs["task-A" if "task-A" in str(d) else "task-B"]
    monkeypatch.setitem(sys.modules, "lib", lib_ns)
    fake_tp = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location("lib.task_paths", str(SCRIPTS_DIR / "lib" / "task_paths.py"))
    )
    fake_tp.resolve_task_document = lib_ns.resolve_task_document
    monkeypatch.setitem(sys.modules, "lib.task_paths", fake_tp)
    return omc, docs


def test_resume_second_task_does_not_overwrite_pointer(fake_env):
    """resume(B) after resume(A): pointer must stay on A (B refused)."""
    omc, _ = fake_env
    cb.cmd_resume(str(omc / "tasks" / "20260813" / "task-A"))
    ptr = omc / "state" / "active-resume.json"
    assert ptr.exists(), "pointer should exist after resume A"
    data = json.loads(ptr.read_text(encoding="utf-8"))
    assert "task-A" in data.get("slug", ""), "pointer should point to A"

    cb.cmd_resume(str(omc / "tasks" / "20260813" / "task-B"))
    data2 = json.loads(ptr.read_text(encoding="utf-8"))
    assert "task-A" in data2.get("slug", ""), (
        f"pointer must stay on A after resume B, got {data2.get('slug')}"
    )


def test_resume_after_archived_task_allows_overwrite(fake_env):
    """Pointer to an archived (non-active) task may be overwritten."""
    omc, docs = fake_env
    cb.cmd_resume(str(omc / "tasks" / "20260813" / "task-A"))
    # Archive A's token, then resume B → allowed
    tokA = docs["task-A"]["token_path"]
    data = json.loads(tokA.read_text(encoding="utf-8"))
    data["status"] = "archived"
    tokA.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    cb.cmd_resume(str(omc / "tasks" / "20260813" / "task-B"))
    ptr = omc / "state" / "active-resume.json"
    data2 = json.loads(ptr.read_text(encoding="utf-8"))
    assert "task-B" in data2.get("slug", ""), "pointer should move to B after A archived"
