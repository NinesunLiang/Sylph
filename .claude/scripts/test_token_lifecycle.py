import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/scripts"))

from token_lifecycle import finalize_token, lock_path_for


def _write_token(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"session": {"id": "task"}, "status": "active", "revision": 2}),
        encoding="utf-8",
    )
    lock_path_for(path).touch()
    return path


def test_finalize_archived_retains_token_and_removes_sidecar(tmp_path):
    token_path = _write_token(tmp_path / "task.json")

    result = finalize_token(token_path, status="archived", reason="archive completed")

    assert result["status"] == "archived"
    assert json.loads(token_path.read_text(encoding="utf-8"))["status"] == "archived"
    assert token_path.exists()
    assert not lock_path_for(token_path).exists()


def test_finalize_failed_retains_token_and_removes_sidecar(tmp_path):
    token_path = _write_token(tmp_path / "task.json")

    result = finalize_token(token_path, status="failed", reason="terminal error")

    assert result["status"] == "failed"
    assert result["terminal_reason"] == "terminal error"
    assert token_path.exists()
    assert not lock_path_for(token_path).exists()


def test_finalize_is_idempotent_when_sidecar_is_already_missing(tmp_path):
    token_path = _write_token(tmp_path / "task.json")
    finalize_token(token_path, status="archived")

    finalize_token(token_path, status="archived")

    assert json.loads(token_path.read_text(encoding="utf-8"))["status"] == "archived"
    assert not lock_path_for(token_path).exists()


def test_finalize_rejects_non_terminal_status(tmp_path):
    token_path = _write_token(tmp_path / "task.json")

    with pytest.raises(ValueError, match="terminal status"):
        finalize_token(token_path, status="active")

    assert lock_path_for(token_path).exists()
