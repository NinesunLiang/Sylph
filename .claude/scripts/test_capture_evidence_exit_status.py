"""TDD for capture_evidence exit status and import safety."""

import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("capture_evidence_under_test", SCRIPTS / "capture_evidence.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_reports_failed_expectation(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "PROJECT", tmp_path)
    ok = module.run("broken", ["/usr/bin/false"], lambda *_: True)
    assert ok is False


def test_main_returns_nonzero_when_check_fails(monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "run", lambda *unused_args: False)
    assert module.main() != 0
