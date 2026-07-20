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

# Round7 PKG-1: token 读取委托 SSOT(单一真相源,禁第二实现)
# 直插 lib 目录按顶层模块导入——hooks/lib 正规包会遮蔽 lib.* 包路径
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
try:
    from task_ssot import latest_active_token as _ssot_latest_active_token
except Exception:  # SSOT 不可用 → 降级 NO_TASK 显示(状态栏只读,永不炸)
    _ssot_latest_active_token = None


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def latest_token(root: Path) -> Path | None:
    """委托 task_ssot:终态(archived/done/completed)与非任务 token 永不复活。"""
    if _ssot_latest_active_token is None:
        return None
    return _ssot_latest_active_token(root / ".omc" / "tokens")


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

    # R7 修复(compact=unknown 根因):token 无 compact_strategy 字段时,
    # 回退到水位系统每轮实写的 context_watermark/compact_status——数据一直在,只是没认。
    watermark = session.get("context_watermark")
    if isinstance(watermark, (int, float)):
        level = session.get("compact_status", "")
        return f"wm={int(watermark)}%{('/' + str(level)) if level else ''}"

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
