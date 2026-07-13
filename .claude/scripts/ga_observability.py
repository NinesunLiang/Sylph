#!/usr/bin/env python3
"""
ga_observability.py — collect CarrorOS GA observability candidate metrics.

This instruments GA observability. It does not by itself certify GA unless enough
real longitudinal samples exist.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
OMC = PROJECT / ".omc"
TOKENS = OMC / "tokens"
TASKS = OMC / "tasks"
METRICS = OMC / "metrics"
GA_DIR = METRICS / "ga"
OBSERVABILITY = GA_DIR / "observability.json"
EVIDENCE = METRICS / "runtime-verify" / "evidence.jsonl"

CONTEXT_BUDGET = 12000
EST_INPUT_TOKEN_USD_PER_M = 3.0
EST_OUTPUT_TOKEN_USD_PER_M = 15.0

STABLE_PREFIX_FILES = [
    PROJECT / "AGENTS.md",
    PROJECT / ".claude" / "kernel.md",
    PROJECT / ".claude" / "index.md",
    PROJECT / ".claude" / "settings.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = round((len(ordered) - 1) * pct)
    return ordered[index]


def stable_prefix_hash() -> dict[str, Any]:
    h = hashlib.sha256()
    files: list[dict[str, Any]] = []
    total_chars = 0
    for path in STABLE_PREFIX_FILES:
        if not path.exists():
            continue
        rel = str(path.relative_to(PROJECT))
        data = path.read_bytes()
        h.update(rel.encode("utf-8") + b"\0" + data + b"\0")
        total_chars += len(data)
        files.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {
        "algorithm": "sha256(path+nul+content+nul)",
        "hash": h.hexdigest(),
        "files": files,
        "controllable_prefix_chars": total_chars,
        "controllable_prefix_tokens": total_chars // 4,
    }


def load_tokens() -> list[tuple[Path, dict[str, Any]]]:
    tokens: list[tuple[Path, dict[str, Any]]] = []
    if not TOKENS.exists():
        return tokens
    for path in sorted(TOKENS.glob("**/*.json")):
        data = read_json(path)
        if data is not None:
            tokens.append((path, data))
    return tokens


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


def append_evidence(record: dict[str, Any]) -> None:
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_report() -> dict[str, Any]:
    prefix = stable_prefix_hash()
    tokens = load_tokens()
    fallback_tokens = int(prefix["controllable_prefix_tokens"])
    session_rows = []
    turn_counts: list[int] = []
    controllable_values: list[int] = []
    total_l5 = 0
    total_compacts = 0
    total_critical = 0
    for path, token in tokens:
        turns = token_turn_count(token)
        controllable = token_controllable_tokens(token, fallback_tokens)
        l5 = token_l5_count(token)
        compact = token_compact_count(token)
        critical = token_critical_count(token)
        turn_counts.append(turns)
        controllable_values.append(controllable)
        total_l5 += l5
        total_compacts += compact
        total_critical += critical
        session_rows.append({
            "token_path": str(path.relative_to(PROJECT)),
            "session_id": token.get("session", {}).get("id") if isinstance(token.get("session"), dict) else path.stem,
            "status": token_status(token),
            "turns": turns,
            "controllable_tokens": controllable,
            "l5_count": l5,
            "compact_count": compact,
            "critical_trip_count": critical,
        })

    sample_count = len(tokens)
    long_sessions = sum(1 for v in turn_counts if v >= 30)
    l5_ratio = (total_l5 / total_compacts) if total_compacts else 0.0
    estimated_input_tokens = sum(controllable_values)
    estimated_output_tokens = max(sum(turn_counts) * 500, 0)
    estimated_cost = (estimated_input_tokens / 1_000_000 * EST_INPUT_TOKEN_USD_PER_M) + (estimated_output_tokens / 1_000_000 * EST_OUTPUT_TOKEN_USD_PER_M)
    successful = sum(1 for token in (item[1] for item in tokens) if token_status(token).lower() in {"completed", "archived"})

    gate_status = {
        "GA-OBS-01": "PASS" if long_sessions >= 30 else "INSTRUMENTED_PENDING_SAMPLE",
        "GA-OBS-02": "PASS" if sample_count >= 30 else "INSTRUMENTED_PENDING_SAMPLE",
        "GA-OBS-03": "PASS" if sample_count >= 30 else "INSTRUMENTED_PENDING_SAMPLE",
        "GA-OBS-04": "PASS" if sample_count >= 30 else "INSTRUMENTED_PENDING_SAMPLE",
    }

    return {
        "schema": "carroros.ga.observability.v1",
        "generated_at": now_iso(),
        "ga_ready": False,
        "sample": {
            "session_count": sample_count,
            "long_session_count_30_plus_turns": long_sessions,
            "status_counts": status_counts(tokens),
        },
        "controllable_tokens": {
            "p50": percentile(controllable_values, 0.50),
            "p95": percentile(controllable_values, 0.95),
            "budget": CONTEXT_BUDGET,
            "source": "token context fields when present, otherwise stable-prefix estimate",
        },
        "turn_distribution": {
            "p50": percentile(turn_counts, 0.50),
            "p95": percentile(turn_counts, 0.95),
            "max": max(turn_counts) if turn_counts else None,
        },
        "l5": {
            "total_l5_count": total_l5,
            "total_compact_count": total_compacts,
            "l5_ratio": round(l5_ratio, 4),
        },
        "critical_water": {
            "total_critical_trips": total_critical,
            "critical_trip_rate_per_session": round(total_critical / sample_count, 4) if sample_count else 0,
        },
        "cost_estimate": {
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_usd_total": round(estimated_cost, 6),
            "estimated_usd_per_session": round(estimated_cost / sample_count, 6) if sample_count else None,
            "estimated_usd_per_successful_task": round(estimated_cost / successful, 6) if successful else None,
            "note": "estimate only; provider billing/cache data not observed",
        },
        "cache_stability_proxy": prefix,
        "gate_status": gate_status,
        "sessions": session_rows,
    }


def main() -> int:
    GA_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OBSERVABILITY.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    append_evidence({
        "test": "G6-GA-OBSERVABILITY-INSTRUMENTED",
        "status": "PASS",
        "detail": f"sessions={report['sample']['session_count']} long30={report['sample']['long_session_count_30_plus_turns']}",
        "output": str(OBSERVABILITY.relative_to(PROJECT)),
        "timestamp": now_iso(),
    })
    print(json.dumps({
        "observability": str(OBSERVABILITY.relative_to(PROJECT)),
        "gate_status": report["gate_status"],
        "ga_ready": False,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
