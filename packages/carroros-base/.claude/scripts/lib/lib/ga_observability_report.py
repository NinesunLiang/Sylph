#!/usr/bin/env python3
"""Report builder for CarrorOS GA observability."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ga_observability_metrics import (  # type: ignore[reportMissingImports]
    percentile,
    stable_prefix_hash,
    status_counts,
    token_compact_count,
    token_controllable_tokens,
    token_critical_count,
    token_l5_count,
    token_status,
    token_turn_count,
)

CONTEXT_BUDGET = 12000
EST_INPUT_TOKEN_USD_PER_M = 3.0
EST_OUTPUT_TOKEN_USD_PER_M = 15.0


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_report(project: Path, tokens: list[tuple[Path, dict[str, Any]]], stable_prefix_files: list[Path]) -> dict[str, Any]:
    prefix = stable_prefix_hash(project, stable_prefix_files)
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
            "token_path": str(path.relative_to(project)),
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
