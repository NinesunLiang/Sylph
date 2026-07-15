#!/usr/bin/env python3
"""Pure metric helpers for CarrorOS GA observability."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = round((len(ordered) - 1) * pct)
    return ordered[index]


def stable_prefix_hash(project: Path, files: list[Path]) -> dict[str, Any]:
    h = hashlib.sha256()
    file_rows: list[dict[str, Any]] = []
    total_chars = 0
    for path in files:
        if not path.exists():
            continue
        rel = str(path.relative_to(project))
        data = path.read_bytes()
        h.update(rel.encode("utf-8") + b"\0" + data + b"\0")
        total_chars += len(data)
        file_rows.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {
        "algorithm": "sha256(path+nul+content+nul)",
        "hash": h.hexdigest(),
        "files": file_rows,
        "controllable_prefix_chars": total_chars,
        "controllable_prefix_tokens": total_chars // 4,
    }


def token_turn_count(token: dict[str, Any]) -> int:
    stats = token.get("stats", {}) if isinstance(token.get("stats"), dict) else {}
    candidates = [stats.get("tick"), stats.get("turns"), token.get("turns")]
    nums = [int(v) for v in candidates if isinstance(v, int)]
    return max(nums) if nums else 0


def token_controllable_tokens(token: dict[str, Any], fallback: int) -> int:
    context = token.get("context", {}) if isinstance(token.get("context"), dict) else {}
    session = token.get("session", {}) if isinstance(token.get("session"), dict) else {}
    for source in (context, session, token):
        value = source.get("controllable_tokens") or source.get("token_used") or source.get("context_tokens")
        if isinstance(value, int):
            return value
    return fallback


def token_l5_count(token: dict[str, Any]) -> int:
    session = token.get("session", {}) if isinstance(token.get("session"), dict) else {}
    compact = token.get("compact", {}) if isinstance(token.get("compact"), dict) else {}
    total = 0
    for source in (session, compact, token):
        for key in ("l5_count", "l5_triggers", "auto_compact_l5_count"):
            value = source.get(key)
            if isinstance(value, int):
                total += value
    if token.get("water_level_triggered") == "compact" and token.get("l5_as_memory"):
        total += 1
    return total


def token_compact_count(token: dict[str, Any]) -> int:
    session = token.get("session", {}) if isinstance(token.get("session"), dict) else {}
    compact = token.get("compact", {}) if isinstance(token.get("compact"), dict) else {}
    total = 0
    for source in (session, compact, token):
        for key in ("compact_count", "compact_requests", "compacts"):
            value = source.get(key)
            if isinstance(value, int):
                total += value
    if token.get("water_level_triggered") == "compact":
        total += 1
    return total


def token_critical_count(token: dict[str, Any]) -> int:
    session = token.get("session", {}) if isinstance(token.get("session"), dict) else {}
    total = 0
    for source in (session, token):
        for key in ("critical_trip_count", "water_critical_count"):
            value = source.get(key)
            if isinstance(value, int):
                total += value
    if token.get("water_level_triggered") == "compact":
        total += 1
    return total


def token_status(token: dict[str, Any]) -> str:
    task_value = token.get("task")
    task: dict[str, Any] = task_value if isinstance(task_value, dict) else {}
    return str(token.get("status") or task.get("status") or "unknown")


def status_counts(tokens: list[tuple[Path, dict[str, Any]]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in (item[1] for item in tokens):
        status = token_status(token)
        counts[status] = counts.get(status, 0) + 1
    return counts
