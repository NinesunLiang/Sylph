"""Result-state adapter shared by the sub-agent manager and executor."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WRITE_LOCK_DIR = str(_PROJECT_ROOT / "scripts")
if _WRITE_LOCK_DIR not in sys.path:
    sys.path.insert(0, _WRITE_LOCK_DIR)

from write_lock import update_json_with_lock


TERMINAL_STATUSES = frozenset({"completed", "failed", "timeout", "cancelled"})
ResultUpdater = Callable[[dict[str, Any]], dict[str, Any] | None]


def read_result(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def update_result_locked(path: Path, updater: ResultUpdater) -> tuple[dict[str, Any], bool]:
    return update_json_with_lock(Path(path), updater)
