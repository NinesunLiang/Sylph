#!/usr/bin/env python3

"""
oma_lock_manager.py — Carror OS One-Man Army (OMA) Lock Manager v2

基于文件系统的分布式锁管理器，支持：
- 原子加锁（基于 O_EXCL）+ 原子夺锁（基于 os.rename 解决 TOCTOU）
- Heartbeat 过期锁检测
- 锁可观测性（.omc/state/locks.json）
- CLI 接口：acquire / release / heartbeat / status
"""

import sys, os, time, json, random, tempfile

from pathlib import Path


if sys.version_info < (3, 8):
    print("🚫 [Carror OS Error] oma_lock_manager 强依赖 Python 3.8+。", file=sys.stderr)
    sys.exit(2)


def get_project_root() -> Path:
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd()


PROJECT_ROOT = get_project_root()
LOCK_DIR = PROJECT_ROOT / ".omc" / "locks"
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
OBSERVABILITY_FILE = STATE_DIR / "locks.json"
TIMEOUT_SEC = float(os.environ.get("OMA_LOCK_TIMEOUT", 60.0))


def _read_harness_config():
    """Read harness config from cache file, with env var override."""
    root = get_project_root()
    cache_file = root / ".omc" / "state" / ".harness-cache"
    config = {}
    if cache_file.exists():
        try:
            for line in cache_file.read_text().splitlines():
                if '=' in line:
                    k, v = line.split('=', 1)
                    config[k] = v
        except Exception:
            pass
    return config


_harness_config = _read_harness_config()

MAX_OBSERVABILITY_EVENTS = int(os.environ.get(
    "OMA_MAX_OBSERVABILITY_EVENTS",
    _harness_config.get("oma_lock_manager.max_observability_events", "500")
))

INITIAL_BACKOFF = float(os.environ.get(
    "OMA_INITIAL_BACKOFF",
    _harness_config.get("oma_lock_manager.initial_backoff", "0.1")
))

MAX_BACKOFF = float(os.environ.get(
    "OMA_MAX_BACKOFF",
    _harness_config.get("oma_lock_manager.max_backoff", "1.0")
))

# Ensure directories exist at import time
LOCK_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_lock_file(target_path: str) -> Path:
    safe_name = str(target_path).replace("/", "_").replace("\\", "_").strip("_")
    return LOCK_DIR / f"{safe_name}.lock"


# ── Lock Observability ──────────────────────────────────────────────────

def _load_observability() -> dict:
    """Load the lock observability file, returning a dict with 'events' and 'current_locks'."""
    if OBSERVABILITY_FILE.exists():
        try:
            data = json.loads(OBSERVABILITY_FILE.read_text())
            if isinstance(data, dict) and "events" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"events": [], "current_locks": {}}


def _save_observability(data: dict):
    """Atomically write observability data to disk."""
    tmp = OBSERVABILITY_FILE.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2))
        os.rename(tmp, OBSERVABILITY_FILE)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def _record_observability(action: str, target_path: str, owner: str, success: bool, **extra):
    """Record a lock event in the observability file."""
    try:
        data = _load_observability()

        event = {
            "ts": time.time(),
            "action": action,
            "target": target_path,
            "owner": owner,
            "success": success,
        }
        event.update(extra)
        data["events"].append(event)

        # Trim events to prevent unbounded growth
        if len(data["events"]) > MAX_OBSERVABILITY_EVENTS:
            data["events"] = data["events"][-MAX_OBSERVABILITY_EVENTS:]

        # Update current_locks snapshot
        if action == "acquire" and success:
            data["current_locks"][target_path] = {
                "locked_by": owner,
                "locked_at": time.time(),
            }
        elif action == "steal" and success:
            data["current_locks"][target_path] = {
                "locked_by": owner,
                "locked_at": time.time(),
            }
        elif action == "heartbeat" and success and target_path in data["current_locks"]:
            data["current_locks"][target_path]["heartbeat_at"] = time.time()
        elif action == "release" and success:
            data["current_locks"].pop(target_path, None)

        _save_observability(data)
    except Exception:
        # Observability failures must never break lock operations
        pass


# ── Lock Operations ─────────────────────────────────────────────────────

def acquire_lock(target_path: str, owner: str) -> bool:
    os.makedirs(LOCK_DIR, exist_ok=True)
    lock_file = get_lock_file(target_path)
    base_sleep = INITIAL_BACKOFF

    lock_data = {
        "locked_by": owner,
        "locked_at": time.time(),
        "heartbeat_at": time.time(),
    }

    while True:
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w') as f:
                json.dump(lock_data, f)
            _record_observability("acquire", target_path, owner, True)
            print("👉 Re-insp-OMA-Design:4.1-AtomicLock")
            return True
        except FileExistsError:
            try:
                with open(lock_file, 'r') as f:
                    data = json.load(f)

                # Determine lock freshness using the later of locked_at or heartbeat_at
                lock_time = max(data.get("locked_at", 0), data.get("heartbeat_at", 0))
                if time.time() - lock_time > TIMEOUT_SEC:
                    # Lock is stale — attempt atomic replacement via os.rename
                    # This eliminates the TOCTOU race between checking expiry and acquiring
                    old_owner = data.get("locked_by", "unknown")
                    tmp = lock_file.with_suffix(f".lock.{os.getpid()}.{random.randint(100000, 999999)}")
                    try:
                        tmp.write_text(json.dumps(lock_data))
                        # os.rename is atomic on POSIX: dst is atomically replaced
                        os.rename(tmp, lock_file)
                    except Exception:
                        try:
                            tmp.unlink(missing_ok=True)
                        except Exception:
                            pass
                        time.sleep(0.1)
                        continue

                    # Verify we won the race (read our own write)
                    try:
                        with open(lock_file, 'r') as f:
                            verify = json.load(f)
                        if verify.get("locked_by") == owner:
                            _record_observability("steal", target_path, owner, True, old_owner=old_owner)
                            print("👉 Re-insp-OMA-Design:4.1-AtomicLock")
                            return True
                    except Exception:
                        pass

                    # Someone else stole it first — keep waiting
                    continue

                locked_by = data.get("locked_by", "unknown")
                print("👉 Re-insp-OMA-Design:4.2-SpinQueue_Wait")
                print(f"WAITING:{locked_by}")
                sys.stdout.flush()
                # Exponential backoff with jitter to prevent thundering herd
                time.sleep(base_sleep + random.uniform(0, 0.1))
                base_sleep = min(MAX_BACKOFF, base_sleep * 1.5)

            except (json.JSONDecodeError, OSError):
                time.sleep(0.1)


def release_lock(target_path: str, owner: str) -> bool:
    lock_file = get_lock_file(target_path)
    try:
        if not lock_file.exists():
            return False
        # Validate ownership before release
        with open(lock_file, 'r') as f:
            data = json.load(f)
        if data.get("locked_by") == owner or owner == "force":
            lock_file.unlink(missing_ok=True)
            _record_observability("release", target_path, owner, True)
            return True
        return False
    except Exception:
        return False


def update_heartbeat(target_path: str, owner: str) -> bool:
    """Update the heartbeat timestamp for an active lock, extending its lease."""
    lock_file = get_lock_file(target_path)
    try:
        if not lock_file.exists():
            return False
        with open(lock_file, 'r') as f:
            data = json.load(f)
        if data.get("locked_by") != owner:
            return False
        # Update heartbeat in a new dict and write atomically
        data["heartbeat_at"] = time.time()
        tmp = lock_file.with_suffix(f".hb.{os.getpid()}.{random.randint(100000, 999999)}")
        try:
            tmp.write_text(json.dumps(data))
            os.rename(tmp, lock_file)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                return False
        _record_observability("heartbeat", target_path, owner, True)
        return True
    except Exception:
        return False


def list_locks() -> dict:
    """Return a dict of all current lock files with their contents."""
    result = {}
    if not LOCK_DIR.is_dir():
        return result
    for lock_file in sorted(LOCK_DIR.iterdir()):
        if lock_file.suffix == ".lock" and lock_file.is_file():
            try:
                data = json.loads(lock_file.read_text())
                result[lock_file.stem] = data
            except (json.JSONDecodeError, OSError):
                result[lock_file.stem] = {"error": "unreadable"}
    return result


# ── CLI ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: oma_lock_manager.py <acquire|release|heartbeat|status> <target> [owner]", file=sys.stderr)
        sys.exit(1)

    action, target = sys.argv[1], sys.argv[2]
    owner = sys.argv[3] if len(sys.argv) > 3 else "unknown"

    if action == "acquire":
        acquire_lock(target, owner)
        print("ACQUIRED")
    elif action == "release":
        release_lock(target, owner)
        print("RELEASED")
    elif action == "heartbeat":
        ok = update_heartbeat(target, owner)
        print("HEARTBEAT_OK" if ok else "HEARTBEAT_FAIL")
        sys.exit(0 if ok else 1)
    elif action == "status":
        locks = list_locks()
        print(json.dumps(locks, indent=2))
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)
