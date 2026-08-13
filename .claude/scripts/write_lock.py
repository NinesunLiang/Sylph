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
from typing import Any, Callable

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


def update_json_with_lock(
    target: Path,
    updater: Callable[[dict[str, Any]], dict[str, Any] | None],
    timeout: float = 5.0,
) -> tuple[dict[str, Any], bool]:
    """Read, transform, and atomically publish JSON under the shared lock."""
    lock_path = _get_lock_path(target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
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
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                current = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
            except (OSError, json.JSONDecodeError):
                current = {}
            if not isinstance(current, dict):
                current = {}
            updated = updater(dict(current))
            if updated is None:
                return current, False
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as output:
                output.write(json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
                output.flush()
                os.fsync(output.fileno())
            tmp.replace(target)
            return updated, True
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
    return {}, False


# ─── Advisory cross-session edit lock (P1-5, index12 S3) ──────────────────────
# 解决并发 agent 会话同时修改共享非冻结脚本的文件竞争（index11 E11-004/005）。
# 无 hook 强制，是任何遵守 CarrorOS 的 agent 在写共享文件前应检查的 advisory 协议：
#   ok, info = acquire_edit_lock(Path("x.py"), holder=session_id)
#   if ok: ... edit ... ; release_edit_lock(target, holder)
# CAS 语义：O_EXCL 原子创建；仅 holder 可释放；过期可 steal；corrupt 不静默偷锁。


def _edit_lock_path(target: Path) -> Path:
    return Path(str(target) + ".edit.lock")


def acquire_edit_lock(
    target: Path,
    holder: str,
    ttl_sec: float = 3600.0,
) -> tuple[bool, dict[str, Any]]:
    """Advisory CAS acquire of the edit lock for a shared file.

    Returns (acquired, lock_info). On conflict returns (False, current_info).
    Never steals a corrupt/unreadable lock (fail-closed).
    """
    lock_path = _edit_lock_path(target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        try:
            info: dict[str, Any] = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False, {"holder": "unknown", "corrupt": True}
        if time.time() > info.get("expires_at", 0):
            stolen = {"holder": holder, "acquired_at": now, "expires_at": now + ttl_sec}
            tmp = lock_path.with_suffix(".lock.tmp")
            tmp.write_text(json.dumps(stolen, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(lock_path)
            return True, stolen
        return False, info
    try:
        info = {"holder": holder, "acquired_at": now, "expires_at": now + ttl_sec}
        os.write(fd, json.dumps(info, ensure_ascii=False, indent=2).encode("utf-8"))
        os.fsync(fd)
        return True, info
    finally:
        os.close(fd)


def release_edit_lock(target: Path, holder: str) -> bool:
    """Release the edit lock only if held by the given holder (CAS)."""
    lock_path = _edit_lock_path(target)
    try:
        info = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True  # absent/unreadable → treated as released
    if info.get("holder") != holder:
        return False
    try:
        lock_path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def edit_lock_status(target: Path) -> dict[str, Any]:
    """Return current edit-lock status for a target file."""
    lock_path = _edit_lock_path(target)
    if not lock_path.exists():
        return {"locked": False, "holder": None, "expires_at": None, "expired": False}
    try:
        info = json.loads(lock_path.read_text(encoding="utf-8"))
        expired = time.time() > info.get("expires_at", 0)
        return {
            "locked": not expired,
            "holder": info.get("holder"),
            "expires_at": info.get("expires_at"),
            "expired": expired,
        }
    except (OSError, json.JSONDecodeError):
        return {"locked": True, "holder": "unknown", "expired": False, "corrupt": True}
