"""TDD for allocator repository-root path resolution."""

import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("alloc_root_under_test", SCRIPTS / "alloc_report_index.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_paths_are_repo_root_relative():
    module = _load()
    repo_root = SCRIPTS.parents[1]
    assert module.PROJECT_ROOT == repo_root
    assert module.BENCHMARKING == repo_root / "Benchmarking"
    assert module.LOCK_FILE == repo_root / ".omc" / "state" / "report-index.lock"
