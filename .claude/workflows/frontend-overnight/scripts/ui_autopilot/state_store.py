"""state_store.py — Atomic checkpoint/restore for UI Autopilot RunState.

Provides disk-persisted state with:
  - Atomic writes (write-then-rename pattern)
  - Append-only event log (execution-events.jsonl)
  - Append-only score history (score-history.jsonl)
  - Checkpoint snapshots for rollback
  - Heartbeat for liveness monitoring

All operations are crash-safe: interrupted writes leave the previous
state intact.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .domain import RunState, RunEvent, Score


def _atomic_write(path: Path, data: str) -> None:
    """Write data to path atomically using write-then-rename.

    Protects against crashes during write: if the process dies mid-write,
    the original file remains untouched.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}."
    )
    try:
        os.write(fd, data.encode("utf-8"))
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, str(path))
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    """Append a JSON object as one line to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, sort_keys=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


# ── Run State Persistence ──────────────────────────────────────────────────────


def save_run_state(state: RunState, run_dir: Path) -> None:
    """Save RunState to run-state.json atomically.

    Args:
        state: Current RunState to persist
        run_dir: Run directory (e.g., .omc/ui-autopilot/{task_id}/)
    """
    state.touch()
    save_path = run_dir / "run-state.json"
    data = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
    _atomic_write(save_path, data)


def load_run_state(run_dir: Path) -> RunState | None:
    """Load RunState from run-state.json.

    Args:
        run_dir: Run directory

    Returns:
        RunState if file exists and is valid, None otherwise
    """
    load_path = run_dir / "run-state.json"
    if not load_path.exists():
        return None

    try:
        data = json.loads(load_path.read_text(encoding="utf-8"))
        return RunState.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


# ── Event Logging ──────────────────────────────────────────────────────────────


def log_event(run_dir: Path, event: RunEvent) -> None:
    """Append a run event to the execution-events.jsonl.

    Args:
        run_dir: Run directory
        event: Event to log
    """
    log_path = run_dir / "event-log.jsonl"
    _append_jsonl(log_path, json.loads(event.to_jsonl()))


def log_score(run_dir: Path, score: Score) -> None:
    """Append a score snapshot to score-history.jsonl.

    Args:
        run_dir: Run directory
        score: Current Score
    """
    log_path = run_dir / "score-history.jsonl"
    _append_jsonl(log_path, {
        "ts": datetime.now(timezone.utc).isoformat(),
        "geometry": score.geometry,
        "color": score.color,
        "typography": score.typography,
        "decoration": score.decoration,
        "layout": score.layout,
        "token_align": score.token_align,
        "interaction": score.interaction,
        "uif_composite": score.uif_composite(),
        "interaction_coverage": score.interaction_coverage,
        "h1_pass": score.h1_engineering_pass,
        "h2_pass": score.h2_evidence_pass,
    })


# ── Checkpoint Snapshots ───────────────────────────────────────────────────────


def save_checkpoint(state: RunState, run_dir: Path, label: str = "") -> str:
    """Save a named checkpoint snapshot for rollback.

    Checkpoints are saved as run-state-{label}.json in the checkpoints/
    subdirectory. The current state is also saved to run-state.json.

    Args:
        state: Current state to checkpoint
        run_dir: Run directory
        label: Optional label (timestamp used if empty)

    Returns:
        Checkpoint filename
    """
    if not label:
        label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    checkpoints_dir = run_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    filename = f"run-state-{label}.json"
    checkpoint_path = checkpoints_dir / filename

    data = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
    _atomic_write(checkpoint_path, data)

    # Also update main state
    state.last_checkpoint = label
    save_run_state(state, run_dir)

    return filename


def restore_checkpoint(run_dir: Path, label: str) -> RunState | None:
    """Restore RunState from a named checkpoint.

    Args:
        run_dir: Run directory
        label: Checkpoint label

    Returns:
        Restored RunState, or None if checkpoint not found
    """
    checkpoint_path = run_dir / "checkpoints" / f"run-state-{label}.json"
    if not checkpoint_path.exists():
        return None

    try:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        state = RunState.from_dict(data)

        # Restore the main state file from checkpoint
        save_run_state(state, run_dir)

        return state
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def list_checkpoints(run_dir: Path) -> list[str]:
    """List all available checkpoint labels.

    Args:
        run_dir: Run directory

    Returns:
        Sorted list of checkpoint labels
    """
    checkpoints_dir = run_dir / "checkpoints"
    if not checkpoints_dir.exists():
        return []

    checkpoints = []
    for f in sorted(checkpoints_dir.iterdir()):
        if f.name.startswith("run-state-") and f.name.endswith(".json"):
            label = f.name[len("run-state-"):-len(".json")]
            checkpoints.append(label)

    return checkpoints


# ── Heartbeat ──────────────────────────────────────────────────────────────────


def write_heartbeat(run_dir: Path, state: RunState) -> None:
    """Write a liveness heartbeat.

    CarrorOS can check this file to determine if the autopilot is still
    alive. Stale heartbeat (> 5 min) indicates a crash.

    Args:
        run_dir: Run directory
        state: Current RunState
    """
    heartbeat_path = run_dir / "heartbeat.json"
    data = json.dumps({
        "run_id": state.run_id,
        "status": str(state.status),
        "phase": str(state.phase),
        "iteration": state.iteration,
        "current_task_id": state.current_task_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "latest_score": state.latest_score.uif_composite(),
        "best_score": state.best_score.uif_composite(),
        "kimi_calls_used": state.kimi_calls_used,
        "total_model_calls": state.total_model_calls,
        "elapsed_seconds": (
            time.time() - state.wall_clock_start
            if state.wall_clock_start > 0 else 0
        ),
    }, ensure_ascii=False)
    _atomic_write(heartbeat_path, data)


def read_heartbeat(run_dir: Path) -> dict[str, Any] | None:
    """Read the current heartbeat.

    Args:
        run_dir: Run directory

    Returns:
        Heartbeat dict, or None if file doesn't exist
    """
    heartbeat_path = run_dir / "heartbeat.json"
    if not heartbeat_path.exists():
        return None

    try:
        return json.loads(heartbeat_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ── Blocker Tracking ───────────────────────────────────────────────────────────


def save_blocker(run_dir: Path, blocker: dict[str, Any]) -> None:
    """Save a blocker entry to blockers.yaml.

    Args:
        run_dir: Run directory
        blocker: Blocker details dict
    """
    blocker_path = run_dir / "blockers.yaml"

    blocker["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Simple YAML-compatible format
    lines = [
        f"- type: {blocker.get('type', 'unknown')}",
        f"  reason: {blocker.get('reason', 'unknown')}",
        f"  target: {blocker.get('target', '')}",
        f"  phase: {blocker.get('phase', '')}",
        f"  timestamp: {blocker['timestamp']}",
    ]

    if "recommendation" in blocker:
        lines.append(f"  recommendation: {blocker['recommendation']}")

    blocker_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
