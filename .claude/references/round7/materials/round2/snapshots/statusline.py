#!/usr/bin/env python3
"""
CarrorOS statusline renderer.

9.md §8 — Statusline 渲染器

Purpose:
  Render one-line task status for Claude Code Statusline.

Constraints:
  - Python 3.10+ standard library only
  - Read-only except fallback is handled by fallback_engine
  - Does not decide completion
  - Does not expose sensitive content
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def latest_token(root: Path) -> Path | None:
    token_root = root / ".omc" / "tokens"
    if not token_root.exists():
        return None

    candidates = sorted(
        [p for p in token_root.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def compact_label(token: dict[str, Any]) -> str:
    session = token.get("session", {})
    strategy = session.get("compact_strategy")

    if strategy == "watermark":
        watermark = session.get("context_watermark")
        if isinstance(watermark, (int, float)):
            return f"wm={int(watermark)}%"
        return "wm=unknown"

    if strategy == "rounds":
        turn = session.get("turn", "?")
        threshold = session.get("compact_threshold", [15, 20])
        if isinstance(threshold, list) and len(threshold) == 2:
            return f"turn={turn}/{threshold[1]}"
        return f"turn={turn}"

    return "compact=unknown"


def safe_text(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value)
    text = text.replace("\n", " ").replace("\r", " ")
    return text[:48]


def render(root: Path) -> str:
    token_path = latest_token(root)
    if not token_path:
        return "CarrorOS L1_BASE NO_TASK"

    token = read_json(token_path)
    task = token.get("task", {})
    session = token.get("session", {})
    stats = token.get("stats", {})

    level = safe_text(session.get("level", "L1_BASE"))
    status = safe_text(task.get("status", "active"))
    task_id = safe_text(task.get("id", token_path.stem))
    current_step = safe_text(task.get("current_step", "-"))

    done = stats.get("done", 0)
    total = stats.get("total", 0)
    compact = compact_label(token)

    if status == "blocked":
        reason = safe_text(task.get("blocked", "blocked"))
        return f"CarrorOS {level} BLOCKED {task_id} {current_step} {done}/{total} reason={reason}"

    if status == "waiting_user":
        fallback = task.get("fallback", {}) or {}
        reason = safe_text(fallback.get("reason", "requires_user"))
        return f"CarrorOS {level} WAITING_USER {task_id} {current_step} reason={reason}"

    return f"CarrorOS {level} OK {task_id} {current_step} {done}/{total} {compact}"


def main() -> int:
    root = Path(os.environ.get("CARROROS_ROOT", ".")).resolve()
    output = render(root)
    print(output[:160])  # 9.md §15: max 160 chars
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
