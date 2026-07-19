#!/usr/bin/env python3
"""CarrorOS PKG-C lifecycle SSOT.

Philosophy chain: 验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少
Disk is the only truth. Counters are derived from items length.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
STATE_DIR = ROOT / ".claude" / "state"
LIFECYCLE_PATH = STATE_DIR / "lifecycle.json"
HANDOFF_PATH = STATE_DIR / "handoff.json"
SNAPSHOT_DIR = STATE_DIR / "snapshots"

LIFECYCLE_VERSION = 1
HANDOFF_VERSION = 1
VALID_MODES = frozenset({"idle", "goal", "ghost"})
# optional human-md sequence parser (READ ONLY; does not write archives)
PROGRESS_RE = re.compile(r"\*\*Progress:\*\*\s*(\d+)\s*/\s*(\d+)\s*steps", re.I)


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: Dict[str, Any]) -> str:
    ensure_dirs()
    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    raw = path.read_text(encoding="utf-8")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != digest:
        raise IOError(f"write-verify-mismatch:{path}")
    json.loads(raw)
    return digest


def default_lifecycle() -> Dict[str, Any]:
    return {
        "version": LIFECYCLE_VERSION,
        "mode": "idle",
        "goal_id": None,
        "ghost_id": None,
        "session_id": None,
        "updated_at": _utc(),
        "compact": {
            "last_precompact_at": None,
            "last_snapshot_path": None,
            "last_sha256": None,
            "last_event_id": None,
        },
        "end": {
            "last_session_end_at": None,
            "last_subagent_stop_at": None,
            "sealed": False,
        },
        "seen_event_ids": [],
    }


def default_handoff() -> Dict[str, Any]:
    return {
        "version": HANDOFF_VERSION,
        "updated_at": _utc(),
        "written": 0,
        "claimed": 0,
        "reconciled": False,
        "items": [],
        "md_progress_note": None,
    }


def load_json(path: Path, default_factory) -> Dict[str, Any]:
    ensure_dirs()
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        data = default_factory()
        _atomic_write(path, data)
        return data
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"not-object:{path}")
    return data


def load_lifecycle() -> Dict[str, Any]:
    data = load_json(LIFECYCLE_PATH, default_lifecycle)
    data["version"] = LIFECYCLE_VERSION
    if data.get("mode") not in VALID_MODES:
        data["mode"] = "idle"
        data["goal_id"] = None
        data["ghost_id"] = None
    # hard mutex repair if both ids set
    if data.get("goal_id") and data.get("ghost_id"):
        data["mode"] = "idle"
        data["goal_id"] = None
        data["ghost_id"] = None
        data["mutex_repaired_at"] = _utc()
    data.setdefault("seen_event_ids", [])
    data.setdefault("compact", default_lifecycle()["compact"])
    data.setdefault("end", default_lifecycle()["end"])
    return data


def reconcile_handoff(data: Dict[str, Any], persist: bool = False) -> Dict[str, Any]:
    items = data.get("items")
    if not isinstance(items, list):
        items = []
        data["items"] = items
    written = len(items)
    claimed = data.get("claimed")
    if not isinstance(claimed, int):
        claimed = written
    data["reconciled"] = bool(claimed != written)
    data["written"] = written
    data["claimed"] = written  # disk wins
    data["updated_at"] = _utc()
    data["version"] = HANDOFF_VERSION
    if persist:
        _atomic_write(HANDOFF_PATH, data)
    return data


def load_handoff() -> Dict[str, Any]:
    data = load_json(HANDOFF_PATH, default_handoff)
    return reconcile_handoff(data, persist=False)


def save_lifecycle(data: Dict[str, Any]) -> str:
    data["updated_at"] = _utc()
    data["version"] = LIFECYCLE_VERSION
    seen = data.get("seen_event_ids") or []
    if len(seen) > 200:
        data["seen_event_ids"] = seen[-200:]
    return _atomic_write(LIFECYCLE_PATH, data)


def save_handoff(data: Dict[str, Any]) -> str:
    data = reconcile_handoff(data, persist=False)
    return _atomic_write(HANDOFF_PATH, data)


def event_seen(lifecycle: Dict[str, Any], event_id: Optional[str]) -> bool:
    if not event_id:
        return False
    return event_id in (lifecycle.get("seen_event_ids") or [])


def mark_event(lifecycle: Dict[str, Any], event_id: Optional[str]) -> None:
    if not event_id:
        return
    seen = lifecycle.setdefault("seen_event_ids", [])
    if event_id not in seen:
        seen.append(event_id)


def set_mode(
    mode: str,
    goal_id: Optional[str] = None,
    ghost_id: Optional[str] = None,
) -> Dict[str, Any]:
    if mode not in VALID_MODES:
        raise ValueError(f"LIFECYCLE_MUTEX:invalid-mode:{mode}")
    if mode == "goal":
        if not goal_id:
            raise ValueError("LIFECYCLE_MUTEX:goal-id-required")
        if ghost_id:
            raise ValueError("LIFECYCLE_MUTEX:ghost-id-not-allowed-in-goal")
    elif mode == "ghost":
        if not ghost_id:
            raise ValueError("LIFECYCLE_MUTEX:ghost-id-required")
        if goal_id:
            raise ValueError("LIFECYCLE_MUTEX:goal-id-not-allowed-in-ghost")
    elif mode == "idle":
        if goal_id or ghost_id:
            raise ValueError("LIFECYCLE_MUTEX:idle-forbids-ids")

    lc = load_lifecycle()
    cur = lc.get("mode", "idle")
    if mode == "goal" and cur == "ghost":
        raise ValueError("LIFECYCLE_MUTEX:cannot-enter-goal-while-ghost")
    if mode == "ghost" and cur == "goal":
        raise ValueError("LIFECYCLE_MUTEX:cannot-enter-ghost-while-goal")

    lc["mode"] = mode
    lc["goal_id"] = goal_id if mode == "goal" else None
    lc["ghost_id"] = ghost_id if mode == "ghost" else None
    save_lifecycle(lc)
    return lc


def append_handoff_item(
    kind: str,
    body: Dict[str, Any],
    event_id: Optional[str] = None,
    source: str = "unknown",
) -> Tuple[Dict[str, Any], bool]:
    lc = load_lifecycle()
    if event_id and event_seen(lc, event_id):
        return load_handoff(), False

    hb = load_handoff()
    item_id = event_id or hashlib.sha256(
        f"{kind}:{_utc()}:{len(hb['items'])}".encode()
    ).hexdigest()[:16]
    hb["items"].append(
        {
            "id": item_id,
            "kind": kind,
            "source": source,
            "at": _utc(),
            "body": body,
        }
    )
    save_handoff(hb)
    if event_id:
        mark_event(lc, event_id)
        save_lifecycle(lc)
    return load_handoff(), True


def peek_md_progress(md_path: Path) -> Optional[Dict[str, int]]:
    """Read-only parse of classic session-handoff.md Progress line."""
    if not md_path.is_file():
        return None
    text = md_path.read_text(encoding="utf-8", errors="replace")
    m = PROGRESS_RE.search(text)
    if not m:
        return None
    return {"done": int(m.group(1)), "total": int(m.group(2))}


def read_stdin_json() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}
    return data if isinstance(data, dict) else {"_raw": data}


def write_precompact_snapshot(
    hook_input: Dict[str, Any],
    event_id: Optional[str],
) -> Tuple[Path, str, Dict[str, Any]]:
    lc = load_lifecycle()
    hb = load_handoff()
    hb = reconcile_handoff(hb, persist=True)

    # optional note from Live session-handoff if present (never archive write)
    live_md = ROOT / ".omc" / "session-handoff.md"
    md_note = peek_md_progress(live_md)
    if md_note is not None:
        hb["md_progress_note"] = md_note
        # distortion signal: digest vs JSON written
        if md_note.get("done") is not None and md_note["done"] != hb["written"]:
            hb["md_vs_json_mismatch"] = True
        save_handoff(hb)
        hb = load_handoff()

    snapshot = {
        "version": 1,
        "type": "precompact",
        "at": _utc(),
        "event_id": event_id,
        "hook_input": {
            "session_id": hook_input.get("session_id") or hook_input.get("sessionId"),
            "cwd": hook_input.get("cwd"),
            "hook_event_name": hook_input.get("hook_event_name")
            or hook_input.get("hookEventName")
            or "PreCompact",
            "transcript_path": hook_input.get("transcript_path")
            or hook_input.get("transcriptPath"),
        },
        "lifecycle": {
            "mode": lc.get("mode"),
            "goal_id": lc.get("goal_id"),
            "ghost_id": lc.get("ghost_id"),
            "session_id": lc.get("session_id"),
        },
        "handoff": {
            "written": hb.get("written"),
            "claimed": hb.get("claimed"),
            "reconciled": hb.get("reconciled"),
            "items": hb.get("items"),
            "md_progress_note": hb.get("md_progress_note"),
            "md_vs_json_mismatch": hb.get("md_vs_json_mismatch", False),
        },
    }
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = SNAPSHOT_DIR / f"precompact-{ts}-{digest[:8]}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    raw = path.read_text(encoding="utf-8")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != digest:
        raise IOError("PRECOMPACT_FAIL:snapshot-hash-mismatch")

    try:
        rel = str(path.relative_to(ROOT))
    except ValueError:
        rel = str(path)

    append_handoff_item(
        kind="precompact_flush",
        body={
            "snapshot": rel,
            "sha256": digest,
            "handoff_written": hb.get("written"),
        },
        event_id=event_id,
        source="precompact-lifecycle",
    )

    lc = load_lifecycle()
    if event_id:
        mark_event(lc, event_id)
    lc["compact"]["last_precompact_at"] = _utc()
    lc["compact"]["last_snapshot_path"] = rel
    lc["compact"]["last_sha256"] = digest
    lc["compact"]["last_event_id"] = event_id
    sid = snapshot["hook_input"].get("session_id")
    if sid:
        lc["session_id"] = sid
    save_lifecycle(lc)
    return path, digest, load_handoff()


def seal_session_end(
    event_id: Optional[str],
    reason: str,
    hook_input: Dict[str, Any],
) -> Dict[str, Any]:
    lc = load_lifecycle()
    if event_id and event_seen(lc, event_id) and lc.get("end", {}).get("sealed"):
        return lc

    hb = reconcile_handoff(load_handoff(), persist=True)
    append_handoff_item(
        kind="session_end",
        body={
            "reason": reason,
            "mode": lc.get("mode"),
            "handoff_written": hb.get("written"),
            "session_id": hook_input.get("session_id")
            or hook_input.get("sessionId")
            or lc.get("session_id"),
        },
        event_id=event_id,
        source="session-end-lifecycle",
    )
    lc = load_lifecycle()
    if event_id:
        mark_event(lc, event_id)
    lc["end"]["last_session_end_at"] = _utc()
    lc["end"]["sealed"] = True
    lc["mode"] = "idle"
    lc["goal_id"] = None
    lc["ghost_id"] = None
    save_lifecycle(lc)
    return lc


def on_subagent_stop(event_id: Optional[str], hook_input: Dict[str, Any]) -> Dict[str, Any]:
    lc = load_lifecycle()
    if event_id and event_seen(lc, event_id):
        return load_handoff()

    agent_id = (
        hook_input.get("agent_id")
        or hook_input.get("agentId")
        or hook_input.get("subagent_id")
        or "unknown"
    )
    agent_type = hook_input.get("agent_type") or hook_input.get("agentType") or "unknown"
    hb, _ = append_handoff_item(
        kind="subagent_stop",
        body={
            "agent_id": agent_id,
            "agent_type": agent_type,
            "session_id": hook_input.get("session_id") or hook_input.get("sessionId"),
        },
        event_id=event_id,
        source="subagent-stop-lifecycle",
    )
    lc = load_lifecycle()
    if event_id:
        mark_event(lc, event_id)
    lc["end"]["last_subagent_stop_at"] = _utc()
    save_lifecycle(lc)
    return hb


def stderr(msg: str) -> None:
    sys.stderr.write(msg if msg.endswith("\n") else msg + "\n")


def stdout_json(data: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False) + "\n")
