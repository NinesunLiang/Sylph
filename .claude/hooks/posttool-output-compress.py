#!/usr/bin/env python3
"""
CarrorOS PostToolUse Output Compression Hook

Purpose:
  When Bash tool produces large output (>2000 chars),
  add compressed version as additional context to save window.

Constraints:
  - Does not block execution
  - Does not alter tool result
  - Adds compressed hint as output_additional_context
"""

from __future__ import annotations

from carroros_hooklib import (
    extract_tool_name,
    hook_continue,
    read_stdin_json,
    sanitize_text,
)

from carroros_hooklib import ROOT

MAX_OUTPUT_CHARS = 2000
HEAD_CHARS = 800
TAIL_CHARS = 800
COMPRESS_SCRIPT = ROOT / ".claude" / "scripts" / "output_compress.py"


def main() -> int:
    payload = read_stdin_json()
    tool = extract_tool_name(payload).lower()

    # Only process Bash tool output
    if tool not in ("bash", "terminal"):
        return hook_continue("OutputCompress: ALLOW non_bash_tool")

    result = str(payload.get("result", "") or payload.get("tool_result", "") or "")
    if len(result) <= MAX_OUTPUT_CHARS:
        return hook_continue("OutputCompress: ALLOW output_small")

    # Sanitize and truncate
    safe_result = sanitize_text(result, 99999)
    head = safe_result[:HEAD_CHARS]
    tail = safe_result[-TAIL_CHARS:]
    original_len = len(result)
    truncated = original_len - HEAD_CHARS - TAIL_CHARS

    compressed = (
        f"[Output compressed: {original_len} chars → {HEAD_CHARS}+{TAIL_CHARS} chars "
        f"({truncated} truncated)]\n"
        f"--- HEAD ({HEAD_CHARS} chars) ---\n"
        f"{head}\n"
        f"--- ... {truncated} chars truncated ... ---\n"
        f"--- TAIL ({TAIL_CHARS} chars) ---\n"
        f"{tail}"
    )

    return hook_continue(
        "OutputCompress: compressed",
        [
            compressed,
            f"Note: original output was {original_len} chars. The middle section was truncated.",
        ],
    )


if __name__ == "__main__":
    raise SystemExit(main())
