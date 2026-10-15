"""TDD for pre-push fail-closed behavior."""

import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("pre_push_under_test", SCRIPTS / "pre_push_check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_git_failure_is_not_reported_as_empty(monkeypatch):
    module = _load()

    class Failed:
        returncode = 2
        stdout = ""
        stderr = "git unavailable"

    def fail_run(*args, **kwargs):
        if len(args) + len(kwargs) < 0:
            raise AssertionError("unreachable")
        return Failed()

    monkeypatch.setattr(module.subprocess, "run", fail_run)
    try:
        module._git("status")
    except RuntimeError:
        return
    raise AssertionError("git failure must be visible, not converted to empty output")


def test_changed_and_deleted_use_same_baseline(monkeypatch):
    module = _load()
    calls = []

    def fake_git(*args):
        calls.append(args)
        return "file.py\n"

    monkeypatch.setattr(module, "_git", fake_git)
    module.changed_files()
    module.deleted_files()
    baselines = [args[1] for args in calls if args[:1] == ("diff",)]
    assert baselines and len(set(baselines)) == 1
