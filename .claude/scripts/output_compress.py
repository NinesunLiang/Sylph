#!/usr/bin/env python3
"""
CarrorOS Output Compression

Purpose:
  Truncate large command outputs to save context window.
  Keeps head + tail, removes middle when output exceeds threshold.

Usage:
  python3 output_compress.py <input_text> [max_chars] [head_chars] [tail_chars]

Constraints:
  - Python 3.10+ standard library only
  - Does not alter semantic meaning of success/failure
  - Preserves error messages and exit status
"""

from __future__ import annotations

import sys

DEFAULT_MAX_CHARS = 2000
DEFAULT_HEAD_CHARS = 800
DEFAULT_TAIL_CHARS = 800


def compress_output(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    head_chars: int = DEFAULT_HEAD_CHARS,
    tail_chars: int = DEFAULT_TAIL_CHARS,
) -> str:
    """Compress a large output string by keeping head and tail."""
    if len(text) <= max_chars:
        return text

    head = text[:head_chars]
    tail = text[-tail_chars:]
    truncated_chars = len(text) - head_chars - tail_chars

    return f"{head}\n... [truncated {truncated_chars} chars / {len(text)} total] ...\n{tail}"


def main() -> int:
    if len(sys.argv) < 2:
        text = sys.stdin.read()
    else:
        text = sys.argv[1]

    max_chars = int(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_MAX_CHARS
    head_chars = int(sys.argv[3]) if len(sys.argv) >= 4 else DEFAULT_HEAD_CHARS
    tail_chars = int(sys.argv[4]) if len(sys.argv) >= 5 else DEFAULT_TAIL_CHARS

    compressed = compress_output(text, max_chars, head_chars, tail_chars)
    sys.stdout.write(compressed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
