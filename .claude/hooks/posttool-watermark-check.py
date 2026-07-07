#!/usr/bin/env python3
"""
CarrorOS PostToolUse Watermark Check Hook

Purpose:
  Periodically (every ~5 tool calls) runs context_watermark.py to estimate
  current context usage. At threshold triggers compact preparation:

  🟡 SAFE (0-40%):   normal
  🟡 WARNING (40-70%):  output_additional_context hint about compact
  🔴 CRITICAL (70%+):   auto-run compact-write, then suggest user run /compact

Constraints:
  - Observation/guardrail only, does not block execution
  - Does not auto-compact (user must /compact)
  - Uses turn-estimated watermark (no real token API)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Estimate ~800 tokens per average tool call
TOKENS_PER_CALL = 800
DEFAULT_LIMIT = 200_000
CHECK_INTERVAL = 10  # every 10th tool call, check watermark
COUNTER_PATH = Path(".claude") / ".tool-call-count.json"


def read_counter() -> int:
    if COUNTER_PATH.exists():
        try:
            return json.loads(COUNTER_PATH.read_text(encoding="utf-8")).get("count", 0)
        except (json.JSONDecodeError, OSError):
            return 0
    return 0


def write_counter(count: int) -> None:
    COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    COUNTER_PATH.write_text(
        json.dumps({"count": count}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_watermark(used: int, limit: int) -> dict:
    result = subprocess.run(
        [sys.executable, ".claude/scripts/context_watermark.py",
         "--used", str(used), "--limit", str(limit)],
        capture_output=True, text=True, timeout=10,
    )
    try:
        first_line = result.stdout.strip().split("\n")[0]
        return json.loads(first_line)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"level": "SAFE", "pct": 0, "action": "none"}


def main() -> int:
    # Read and increment tool call counter
    count = read_counter() + 1
    write_counter(count)

    # Only check watermark periodically
    if count % CHECK_INTERVAL != 0:
        print(json.dumps({"continue": True, "message": f"WatermarkCheck: SKIP count={count}"}))
        return 0

    # Estimate token usage
    used_est = min(DEFAULT_LIMIT, count * TOKENS_PER_CALL)
    result = run_watermark(used_est, DEFAULT_LIMIT)

    pct = result.get("pct", 0)
    level = result.get("level", "SAFE")
    action = result.get("action", "none")

    hints = []
    if pct >= 70:
        # CRITICAL: find active token and auto compact-write
        token_path = _find_active_token()
        if token_path:
            task_path = _find_task_dir(token_path)
            if task_path:
                subprocess.run(
                    [sys.executable, ".claude/scripts/context_engine.py",
                     "compact-write", "--token", str(token_path),
                     "--task", str(task_path)],
                    capture_output=True, timeout=15,
                )
        hints.append(
            f"🔴 Context watermark {pct}% — CRITICAL. "
            "请立即运行 /compact 压缩上下文。我已写好了 session-handoff 和 last-user-prompt。"
        )
    elif pct >= 50:
        hints.append(
            f"🟡 Context watermark {pct}% — WARNING. "
            "建议准备 compact：运行 /compact 前我会自动写入恢复信息。"
        )

    output = {"continue": True, "message": f"WatermarkCheck: {level} {pct}%"}
    if hints:
        output["output_additional_context"] = hints

    print(json.dumps(output, ensure_ascii=False))
    return 0


def _find_active_token() -> Path | None:
    """Find the most recent token JSON."""
    token_root = Path(".omc") / "tokens"
    if not token_root.exists():
        return None
    candidates = sorted(
        [p for p in token_root.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _find_task_dir(token_path: Path) -> Path | None:
    """Derive task directory from token path."""
    if len(token_path.parts) >= 2:
        date = token_path.parent.name
        name = token_path.stem
        task_dir = Path(".omc") / "tasks" / date / name
        if task_dir.exists():
            return task_dir
    return None


if __name__ == "__main__":
    raise SystemExit(main())
