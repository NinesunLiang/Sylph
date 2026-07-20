#!/usr/bin/env python3
"""
ga_observability.py — collect CarrorOS GA observability candidate metrics.

This instruments GA observability. It does not by itself certify GA unless enough
real longitudinal samples exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
LIB = Path(__file__).resolve().parent / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from ga_observability_io import append_jsonl, load_tokens, write_json  # type: ignore[reportMissingImports]  # noqa: E402
from ga_observability_report import build_report, now_iso  # type: ignore[reportMissingImports]  # noqa: E402

OMC = PROJECT / ".omc"
TOKENS = OMC / "tokens"
METRICS = OMC / "metrics"
GA_DIR = METRICS / "ga"
OBSERVABILITY = GA_DIR / "observability.json"
EVIDENCE = METRICS / "runtime-verify" / "evidence.jsonl"

STABLE_PREFIX_FILES = [
    PROJECT / "AGENTS.md",
    PROJECT / ".claude" / "kernel.md",
    PROJECT / ".claude" / "index.md",
    PROJECT / ".claude" / "settings.json",
]


def main() -> int:
    tokens = load_tokens(TOKENS)
    report = build_report(PROJECT, tokens, STABLE_PREFIX_FILES)
    write_json(OBSERVABILITY, report)
    append_jsonl(EVIDENCE, {
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
