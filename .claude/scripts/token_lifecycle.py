#!/usr/bin/env python3
"""Shared token terminal finalization."""

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path


TERMINAL_STATUSES = frozenset({"archived", "completed", "failed", "expired", "cancelled"})


def lock_path_for(token_path: str | Path) -> Path:
    path = Path(token_path)
    return path.with_suffix(path.suffix + ".lock")


def finalize_token(
    token_path: str | Path,
    *,
    status: str,
    reason: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Persist a terminal token and remove its sidecar lock idempotently."""
    if status not in TERMINAL_STATUSES:
        raise ValueError(f"status must be a terminal status, got {status!r}")

    path = Path(token_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = lock_path_for(path)
    tmp_path = path.with_suffix(path.suffix + f".{os.getpid()}.finalize.tmp")

    try:
        with sidecar.open("a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                token = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(token, dict):
                    raise ValueError(f"token must be an object: {path}")
                now = datetime.now(timezone.utc).isoformat()
                token["status"] = status
                token["terminal_at"] = now
                if reason:
                    token["terminal_reason"] = reason
                if metadata:
                    token.setdefault("terminal", {}).update(metadata)
                token["revision"] = token.get("revision", 0) + 1
                tmp_path.write_text(
                    json.dumps(token, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                os.replace(tmp_path, path)
                return token
            finally:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                sidecar.unlink(missing_ok=True)
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        sidecar.unlink(missing_ok=True)
