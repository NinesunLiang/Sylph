#!/usr/bin/env python3
"""
CarrorOS Prompt Collector + Lightweight Compact Hook — UserPromptSubmit

Purpose:
  1. Maintain rolling ring buffer of last 20 user prompts (.prompt-ring.json)
  2. Every 5 prompts: auto-run compact-write (update handoff + last-user-prompt)

  This is the "compact 前的 hook" — runs right before each UserPromptSubmit
  boundary. No PostToolUse polling, no watermark calculation, no tool counter.

Constraints:
  - Pure observation, never blocks
  - Only does I/O every 5th prompt (most calls return instantly)
  - handoff 更新只发生在有活跃任务时
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_script_path = Path(__file__).resolve()
ROOT = _script_path.parents[2]
if not (ROOT / ".claude").is_dir():
    ROOT = Path(".").resolve()
os.chdir(str(ROOT))

MAX_PROMPTS = 20
COMPACT_INTERVAL = 5   # 每 5 次用户输入触发 compact-write（手写 handoff）
WATERMARK_INTERVAL = 20  # 每 20 次用户输入估算一次水位（提醒用户 compact）
CONTEXT_LIMIT = 200_000
PROMPT_RING_PATH = ROOT / ".claude" / ".prompt-ring.json"


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


def find_active_token() -> Path | None:
    """查找最新活跃 token（token 存在 = 任务未结束）"""
    token_root = ROOT / ".omc" / "tokens"
    if not token_root.exists():
        return None
    candidates = sorted(
        [p for p in token_root.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    # 检查不是 tombstone/archive 状态
    try:
        token = json.loads(candidates[0].read_text(encoding="utf-8"))
        status = token.get("task", {}).get("status") or token.get("status", "")
        if status in ("archived", "blocked"):
            return None
        return candidates[0]
    except (json.JSONDecodeError, OSError):
        return None


def find_task_dir(token_path: Path) -> Path | None:
    if len(token_path.parts) >= 2:
        date = token_path.parent.name
        name = token_path.stem
        task_dir = ROOT / ".omc" / "tasks" / date / name
        if task_dir.exists():
            return task_dir
    return None


def run_compact_write(token_path: Path) -> None:
    """静默执行 compact-write，不阻塞，不抛出异常"""
    task_path = find_task_dir(token_path)
    if not task_path:
        return
    try:
        subprocess.run(
            [sys.executable, ".claude/scripts/context_engine.py",
             "compact-write", "--token", str(token_path),
             "--task", str(task_path)],
            capture_output=True, timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass  # 静默失败，不阻塞用户输入


def main() -> int:
    payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

    prompt = extract_prompt(payload)

    # Read or initialize ring
    ring = read_ring()

    if prompt:
        # Add new prompt
        ring.append({
            "ts": now_iso(),
            "prompt": prompt[:500],
        })
        # Trim to max 20
        if len(ring) > MAX_PROMPTS:
            ring = ring[-MAX_PROMPTS:]

    write_ring(ring)

    # 每 COMPACT_INTERVAL 次用户输入触发一次 compact-write
    if len(ring) > 0 and len(ring) % COMPACT_INTERVAL == 0:
        token_path = find_active_token()
        if token_path:
            run_compact_write(token_path)

    water_mark_hint = ""
    if len(ring) > 0 and len(ring) % WATERMARK_INTERVAL == 0:
        # 估算上下文水位：每轮约 7k（含累积历史），N轮 ≈ N × 7k
        n = len(ring)
        used_est = min(CONTEXT_LIMIT, n * 7000)
        pct = round((used_est / CONTEXT_LIMIT) * 100)
        if pct >= 70:
            water_mark_hint = (
                f"🔴 Context watermark ~{pct}%. "
                "运行 /compact 可压缩上下文，保持模型智力。"
            )
        elif pct >= 50:
            water_mark_hint = (
                f"🟡 Context watermark ~{pct}%. "
                "考虑运行 /compact 压缩上下文。"
            )

    if water_mark_hint:
        print(json.dumps({
            "continue": True,
            "message": "OK",
            "output_additional_context": [water_mark_hint],
        }))
        return 0

    print(json.dumps({"continue": True, "message": "OK"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
