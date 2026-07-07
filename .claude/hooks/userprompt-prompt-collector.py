#!/usr/bin/env python3
"""
CarrorOS Prompt Collector — UserPromptSubmit Hook

Purpose:
  Maintain a rolling ring buffer of the last 20 user prompts
  in .claude/.prompt-ring.json for compact-write to consume.

  When context_engine compact-write runs, it reads this buffer
  and writes .claude/last-user-prompt.md with the recent history.

Constraints:
  - Pure observation, never blocks
  - No stamp, no startup cost
  - Keeps at most 20 entries (minimal disk I/O)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_PROMPTS = 20
PROMPT_RING_PATH = Path(".claude") / ".prompt-ring.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_ring() -> list[dict]:
    if PROMPT_RING_PATH.exists():
        try:
            data = json.loads(PROMPT_RING_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def write_ring(ring: list[dict]) -> None:
    PROMPT_RING_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_RING_PATH.write_text(
        json.dumps(ring, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def extract_prompt(payload: dict) -> str:
    """Extract user prompt from hook stdin payload."""
    for key in ("prompt", "text", "message", "input"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("prompt", "text", "message", "input"):
            val = tool_input.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def main() -> int:
    payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

    prompt = extract_prompt(payload)
    if not prompt:
        # Still need to respond valid JSON even on empty
        print(json.dumps({"continue": True, "message": "PromptCollector: no_prompt"}))
        return 0

    # Read or initialize ring
    ring = read_ring()

    # Add new prompt
    ring.append({
        "ts": now_iso(),
        "prompt": prompt[:500],  # cap at 500 chars per prompt
    })

    # Trim to max 20
    if len(ring) > MAX_PROMPTS:
        ring = ring[-MAX_PROMPTS:]

    write_ring(ring)

    print(json.dumps({"continue": True, "message": "PromptCollector: OK"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
