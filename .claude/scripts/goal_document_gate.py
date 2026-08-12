"""Canonical Goal document write gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GoalDocumentGateError(ValueError):
    """Raised when a Goal document write is outside its lifecycle phase."""


def _read_token(token_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoalDocumentGateError(f"Goal token unreadable: {token_path}") from exc
    if not isinstance(data, dict):
        raise GoalDocumentGateError(f"Goal token is not an object: {token_path}")
    return data


def canonical_parent_token(task_dir: str | Path, project_root: str | Path) -> tuple[Path, dict[str, Any]] | None:
    """Resolve a canonical parent token without scanning unrelated active tasks."""
    task_path = Path(task_dir).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    canonical_task = task_path.parent.parent.name == "tasks"
    token_path = root / ".omc" / "tokens" / task_path.parent.name / f"{task_path.name}.json"
    if not token_path.exists():
        if canonical_task:
            raise GoalDocumentGateError(f"Goal parent token missing: {token_path}")
        return None

    token = _read_token(token_path)
    if token.get("mode") != "goal":
        return token_path, token

    expected_dir = token.get("task_dir")
    if expected_dir and Path(expected_dir).expanduser().resolve() != task_path:
        raise GoalDocumentGateError(
            f"Goal task_dir mismatch: token={expected_dir} expected={task_path}"
        )
    task_id = token.get("session", {}).get("id")
    if task_id and task_id != task_path.name:
        raise GoalDocumentGateError(
            f"Goal task_id mismatch: token={task_id} expected={task_path.name}"
        )
    return token_path, token


def require_document_write(
    token_path: str | Path,
    document: str,
    action: str = "document write",
    allowed_states: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    """Validate token/task identity before a document write; plans remain editable."""
    path = Path(token_path).expanduser()
    token = _read_token(path)
    if token.get("mode") != "goal":
        return token
    expected_dir = token.get("task_dir")
    if expected_dir and not Path(expected_dir).expanduser().exists():
        raise GoalDocumentGateError(f"Goal task_dir missing: {expected_dir}")
    if allowed_states:
        state = token.get("goal", {}).get("state")
        if state not in allowed_states:
            raise GoalDocumentGateError(
                f"Goal state={state or 'UNKNOWN'} is not allowed for {action}; "
                f"expected one of {sorted(allowed_states)}"
            )
    return token


def require_parent_write(
    task_dir: str | Path,
    project_root: str | Path,
    document: str,
    action: str,
    allowed_states: set[str] | frozenset[str] | None = None,
) -> tuple[Path | None, dict[str, Any]]:
    """Validate a parent task writer using its exact task_dir-derived token."""
    resolved = canonical_parent_token(task_dir, project_root)
    if resolved is None:
        return None, {}
    token_path, token = resolved
    if token.get("mode") == "goal":
        require_document_write(token_path, document, action, allowed_states)
    return token_path, token
