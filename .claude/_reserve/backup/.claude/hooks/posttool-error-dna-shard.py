#!/usr/bin/env python3
"""error-dna-shard.py — PostToolUse — daily sharding for error-dna.jsonl

Periodically splits error-dna.jsonl by date into daily/{date}.jsonl.
Runs every 50th PostToolUse to avoid per-call overhead.
"""
import json
import os
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
try:
    from harness_lib import hc_enabled, output_continue, PROJECT_ROOT
except ImportError:
    HOOKS_DIR = _HOOKS_DIR


def main():
    try:
        if not hc_enabled("error_dna_shard"):
            output_continue()
            return
    except Exception:
        pass

    # Only run every ~50th call (check counter)
    counter_file = _HOOKS_DIR.parent.parent / ".omc" / "state" / ".error-shard-counter"
    try:
        cnt = int(Path(counter_file).read_text().strip() or "0")
    except Exception:
        cnt = 0
    cnt = (cnt + 1) % 50
    try:
        Path(counter_file).write_text(str(cnt))
    except Exception:
        pass
    if cnt != 0:
        output_continue()
        return

    # Determine paths
    project_root = (_HOOKS_DIR / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    dna_file = state_dir / "error-dna.jsonl"
    daily_dir = project_root / ".claude" / "error-dna" / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    if not dna_file.exists():
        output_continue()
        return

    try:
        size = dna_file.stat().st_size
    except Exception:
        size = 0
    if size == 0:
        output_continue()
        return

    ts_now = int(time.time())
    sharded = {}
    try:
        with open(dna_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts = rec.get("ts", ts_now)
                    # Convert ts to date
                    import datetime
                    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                    date_key = dt.strftime("%Y-%m-%d")
                    sharded.setdefault(date_key, []).append(line)
                except (json.JSONDecodeError, Exception):
                    pass
    except Exception:
        pass

    if not sharded:
        output_continue()
        return

    for date_key, records in sharded.items():
        target = daily_dir / f"{date_key}.jsonl"
        try:
            with open(target, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(r + "\n")
        except Exception:
            pass

    output_continue()


if __name__ == "__main__":
    main()
