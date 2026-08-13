#!/usr/bin/env python3
"""gatekeeper_digest.py — 门禁事件消费端

聚合 skipped-risks.jsonl + gatekeeper-events.jsonl + error-dna.jsonl
供退出报告消费。Sonnet-5 要求: "skipped-risks非空超过一次会话应阻断".
Grok 要求: "JSONL加size limit和定期摘要alert"。

用法:
  python3 scripts/gatekeeper_digest.py
  python3 scripts/gatekeeper_digest.py --alert
  python3 scripts/gatekeeper_digest.py --check
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / ".omc" / "state"
MAX_EVENTS = 1000  # size limit


def _read_jsonl(path: Path, max_lines: int = MAX_EVENTS) -> list[dict]:
    if not path.exists():
        return []
    events = []
    try:
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        pass
    return events


def _truncate_jsonl(path: Path, keep: int = 200) -> int:
    """Truncate JSONL to last N entries. Returns number removed."""
    events = _read_jsonl(path, keep + 1000)
    if len(events) <= keep:
        return 0
    removed = len(events) - keep
    tail = events[-keep:]
    try:
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in tail) + "\n", encoding="utf-8")
    except OSError:
        pass
    return removed


def digest() -> dict:
    """Produce digest of all gate events."""
    skipped = _read_jsonl(STATE_DIR / "skipped-risks.jsonl")
    gate_events = _read_jsonl(STATE_DIR / "gatekeeper-events.jsonl")
    error_dna = _read_jsonl(ROOT / ".omc" / "error-dna.jsonl")

    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "skipped_risks": {
            "count": len(skipped),
            "items": skipped[-20:] if skipped else [],
        },
        "gatekeeper_events": {
            "count": len(gate_events),
            "by_decision": {},
            "items": gate_events[-10:] if gate_events else [],
        },
        "error_dna": {
            "count": len(error_dna),
        },
        "digest_version": 1,
    }

    # Aggregate by decision type
    for ev in gate_events:
        dec = ev.get("decision", "unknown")
        result["gatekeeper_events"]["by_decision"][dec] = \
            result["gatekeeper_events"]["by_decision"].get(dec, 0) + 1

    return result


def check() -> int:
    """Check if any gate events need attention. Returns exit code (0=ok, 1=warn, 2=block)."""
    d = digest()

    # Rule: skipped_risks non-empty across sessions
    if d["skipped_risks"]["count"] > 0:
        print(f"⚠️ GATE DIGEST: {d['skipped_risks']['count']} skipped risks pending review")
        # Truncate after alerting
        removed = _truncate_jsonl(STATE_DIR / "skipped-risks.jsonl", 200)
        if removed:
            print(f"   truncated {removed} old entries from skipped-risks.jsonl")
        return 1

    # Rule: gatekeeper events with BLOCK threshold
    blocks = d["gatekeeper_events"]["by_decision"].get("block", 0)
    if blocks > 10:
        print(f"⚠️ GATE DIGEST: {blocks} BLOCK events in gatekeeper log")
        return 1

    return 0


def alert() -> None:
    """Alert with full digest."""
    d = digest()
    print("=" * 50)
    print("GateKeeper Event Digest")
    print(f"  skipped_risks:       {d['skipped_risks']['count']}")
    print(f"  gatekeeper_events:   {d['gatekeeper_events']['count']}")
    print(f"  error_dna entries:   {d['error_dna']['count']}")

    dec = d["gatekeeper_events"]["by_decision"]
    if dec:
        print(f"  by decision: {json.dumps(dec)}")

    if d["skipped_risks"]["items"]:
        print("\n  Recent skipped risks:")
        for item in d["skipped_risks"]["items"][-5:]:
            action = item.get("action", item.get("reason", "?"))[:80]
            print(f"    · {action}")
    print("=" * 50)


if __name__ == "__main__":
    if "--alert" in sys.argv:
        alert()
    elif "--check" in sys.argv:
        sys.exit(check())
    else:
        print(json.dumps(digest(), ensure_ascii=False, indent=2))
