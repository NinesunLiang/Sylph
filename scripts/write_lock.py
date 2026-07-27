#!/usr/bin/env python3
"""write_lock.py — 共享文件写锁

防止多 gate 并发写 token.json/skipped-risks.jsonl 等共享状态文件。
Grok P0 发现: 多 gate 可能在同一进程窗口写 token.json 导致 torn write。

用法:
  from write_lock import write_with_lock
  write_with_lock(Path(".omc/state/token.json"), data)
"""

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Any

LOCK_DIR: Path | None = None


def set_lock_dir(path: Path) -> None:
    global LOCK_DIR
    LOCK_DIR = path


def _get_lock_path(target: Path) -> Path:
    ld = LOCK_DIR or target.parent
    lock_name = target.name + ".lock"
    return ld / lock_name


def write_with_lock(
    target: Path,
    data: dict[str, Any] | list,
    timeout: float = 5.0,
    indent: int = 2,
) -> bool:
    """Write JSON data to target file with advisory file lock.

    Uses fcntl.flock on a sidecar .lock file for cross-process safety.
    Retries with 0.3s backoff within timeout.
    Returns True on success, False if lock not acquired.
    """
    lock_path = _get_lock_path(target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            # Check stale lock (>10s)
            try:
                age = time.monotonic() - lock_path.stat().st_mtime
                if age > 10.0:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            time.sleep(0.3)
            continue

        try:
            # Acquire fcntl lock on the lock file
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            tmp.replace(target)
            return True
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
    return False
