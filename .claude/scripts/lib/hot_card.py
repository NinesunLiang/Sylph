#!/usr/bin/env python3
"""
hot_card.py — CarrorOS Hot Card 渲染器

输出 ≤ 4.5K chars 的极简状态卡片，字段顺序固定。
status --hot 默认输出，--full 才出完整状态。
"""

import json
from pathlib import Path
from typing import Optional, List

HOT_MAX_CHARS = 4500


def load_token(path: Path) -> Optional[dict]:
    """Read token.json; return None if not found."""
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_plan_step(plan_path: Path, step_id: Optional[str] = None) -> dict:
    """Read current step from plan.md. Returns minimal fields."""
    if not plan_path or not plan_path.exists():
        return {}
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    step = {}
    capture = False
    for line in lines:
        if step_id and f"### {step_id}" in line:
            capture = True
            continue
        if capture and line.startswith("### "):
            break
        if not capture:
            continue
        if line.startswith("- **intent**:") or line.startswith("intent:"):
            step["intent"] = line.split(":", 1)[1].strip()[:160]
        elif line.startswith("- **files**:") or line.startswith("files:"):
            raw = line.split(":", 1)[1].strip()
            step["files"] = [f.strip() for f in raw.split(",") if f.strip()]
        elif line.startswith("- **verify**:") or line.startswith("verify:"):
            raw = line.split(":", 1)[1].strip()
            step["verify"] = [v.strip() for v in raw.split(",") if v.strip()]
    return step


def load_last_events(executor_path: Path, n: int = 3) -> List[str]:
    """Read last N lines from executor.md as event short strings."""
    if not executor_path or not executor_path.exists():
        return []
    text = executor_path.read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-n:]


def render_hot_card(
    token: dict,
    step: Optional[dict] = None,
    last_events: Optional[List[str]] = None,
    max_chars: int = HOT_MAX_CHARS,
) -> str:
    """Render Hot Card — deterministic, field order fixed."""
    lines = []

    sid = token.get("session", {}).get("id", "?")
    lev = token.get("session", {}).get("level", "?")
    cs = token.get("task", {}).get("current_step", "?")
    lines.append("# CarrorOS Hot Card")
    lines.append("task: {} | level: {} | step: {}".format(sid, lev, cs))

    stats = token.get("stats", {})
    done = stats.get("done", 0)
    total = stats.get("total", 0)
    tick = stats.get("tick", 0)
    lines.append("ticks: {} | verified: {}/{}".format(tick, done, total))

    status_top = token.get("status", "?")
    blocked = token.get("task", {}).get("blocked")
    status_str = "status: {}".format(status_top)
    if blocked:
        status_str += " | blocked: {}".format(blocked)
    lines.append(status_str)

    if step:
        intent = step.get("intent", "")[:160]
        if intent:
            lines.append("next: {}".format(intent))
        files = step.get("files", [])
        if files:
            lines.append("files: {}".format(", ".join(files[:4])))

    events = last_events or []
    if events:
        lines.append("last:")
        for e in events[-3:]:
            lines.append("  - {}".format(e[:120]))

    lines.append("rules: one_action | no_full_plan | verify_only_done")

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n...[TRUNCATED]"
    return text


def cmd_status_hot(token: dict, token_path: Path, plan_path: Path, executor_path: Path) -> str:
    """Hot Card as default status output."""
    step = load_plan_step(plan_path, token.get("task", {}).get("current_step"))
    events = load_last_events(executor_path)
    return render_hot_card(token, step, events)


def cmd_status_full(token: dict, token_path: Path, plan_path: Path, executor_path: Path) -> str:
    """Full status output (original format)."""
    lines = []
    sid = token.get("session", {}).get("id", "?")
    lev = token.get("session", {}).get("level", "?")
    status_top = token.get("status", "?")
    stats = token.get("stats", {})
    lines.append("● Task: {} [{}]".format(sid, lev))
    lines.append("   Status: {}".format(status_top))
    lines.append("   Progress: {}/{}".format(stats.get("done", 0), stats.get("total", 0)))
    current = token.get("task", {}).get("current_step", "?")
    lines.append("   Current Step: {}".format(current))
    lines.append("   Ticks: {}".format(stats.get("tick", 0)))
    blocked = token.get("task", {}).get("blocked")
    if blocked:
        lines.append("   Blocked: {}".format(blocked))
    return "\n".join(lines)
