#!/usr/bin/env python3
"""
session-resume.py — SessionStart hook

On new session start:
  1. Scan .omc/tokens/{date}/ for active tokens (task state recovery)
  2. Read .omc/state/last-user-prompts for recent user queries (context recovery)
  3. Write a combined context block so the agent can resume seamlessly after /compact

Target path: .omc/tokens/{YYYYMMDD}/{task_id}.json
Recovery file: .omc/state/last-user-prompts

Compatible with Python 3.9+ (no str | None syntax, no match/case).
"""

import json
import os
import sys
from pathlib import Path

PROJECT = Path.cwd()
OMC_TOKENS = PROJECT / ".omc" / "tokens"
STATE_DIR = PROJECT / ".omc" / "state"
PROMPTS_DIR = STATE_DIR / "last-user-prompts"


# ─── Token helpers ───


def _all_date_dirs():
    """List date subdirs under .omc/tokens/, newest first."""
    if not OMC_TOKENS.exists():
        return []
    dirs = sorted(
        (d for d in OMC_TOKENS.iterdir() if d.is_dir() and not d.name.startswith(".")),
        key=lambda p: p.name,
        reverse=True,
    )
    return dirs


def _iter_tokens():
    """Iterate all token files across date dirs."""
    for d in _all_date_dirs():
        date_str = d.name
        for f in sorted(d.glob("*.json")):
            if f.name == "token-writer.log":
                continue
            yield (f.stem, date_str, f)


def _find_active_tokens():
    """Return list of (task_id, date_str, path, token_dict) for non-completed tasks."""
    active = []
    for tid, date_str, fpath in _iter_tokens():
        try:
            tok = json.loads(fpath.read_text())
            status = tok.get("task", {}).get("status", "")
            if status not in ("completed", "archived"):
                active.append((tid, date_str, fpath, tok))
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return active


def _get_terminal_id():
    """Get terminal identifier for multi-terminal isolation.
    Priority: tty > OPENCODE_SESSION_ID > CLAUDE_SESSION_ID > PID
    """
    try:
        tty_id = os.popen("tty 2>/dev/null").read().strip()
        if tty_id and tty_id != "not a tty":
            return tty_id.replace("/dev/", "")
    except Exception:
        pass
    oc_id = os.environ.get("OPENCODE_SESSION_ID", "")
    if oc_id:
        return "oc-" + oc_id[:8]
    cc_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if cc_id:
        return "cc-" + cc_id[:8]
    return "pid-" + str(os.getpid())


def _read_last_prompts():
    """Read last user prompts (up to 20 most recent) for current terminal."""
    term_id = _get_terminal_id()
    prompts_file = PROMPTS_DIR / term_id
    if not prompts_file.exists():
        return []
    try:
        lines = prompts_file.read_text(encoding="utf-8", errors="replace").splitlines()
        lines = [l.strip() for l in lines if l.strip()]
        return lines[-20:]
    except OSError:
        return []


def _build_context(active, prompts):
    """Build a combined context message: active tokens + recent user prompts."""
    lines = []
    lines.append("── CarrorOS 会话恢复（/compact 后/新会话）──")
    lines.append("")

    # ── Section 1: Active Tokens ──
    lines.append("## Active Tasks（任务状态恢复）")
    lines.append("")

    if not active:
        lines.append("  No active tasks found.")
        lines.append("  Start a new task: `carros_base.py init --task-id <NAME>`")
    else:
        for tid, date_str, fpath, tok in active:
            task = tok.get("task", {})
            phase = task.get("phase", "?")
            step = task.get("current_step", "?")
            status = task.get("status", "?")
            stats = tok.get("stats", {})
            done = stats.get("done", 0)
            total = stats.get("total", "?")
            scope = task.get("scope", [])

            lines.append("  [{}/{}] {} — {} ({})".format(date_str, tid, phase, status, step))
            lines.append("    Done: {}/{}".format(done, total))
            if scope:
                lines.append("    Scope: {}".format(", ".join(scope)))
            lines.append("    Token: {}".format(fpath))

        if len(active) == 1:
            tid = active[0][0]
            lines.append("")
            lines.append("  ⏩ Resume: `carros_base.py status --task-id {}` → `tick --task-id {}`".format(tid, tid))

    lines.append("")

    # ── Section 2: Recent User Prompts ──
    lines.append("## Recent User Prompts（最近用户询问）")
    lines.append("")

    if prompts:
        lines.append("  以下是最新的 {} 条用户消息（时间倒序）：".format(len(prompts)))
        lines.append("")
        for i, p in enumerate(reversed(prompts), 1):
            # Truncate long prompts for display
            display = p if len(p) <= 120 else p[:117] + "..."
            lines.append("  {}. {}".format(i, display))
    else:
        lines.append("  （无最近询问记录）")

    lines.append("")
    lines.append("── 恢复结束，请继续工作 ──")

    return "\n".join(lines)


def main():
    # ── Part A: Read active tokens ──
    active = []
    has_tokens = False

    if OMC_TOKENS.exists():
        for d in _all_date_dirs():
            json_files = [f for f in d.glob("*.json") if f.name != "token-writer.log"]
            if json_files:
                has_tokens = True
                break

        if has_tokens:
            active = _find_active_tokens()

    # ── Part B: Read recent prompts ──
    prompts = _read_last_prompts()

    # If neither has content, bail
    if not has_tokens and not prompts:
        return

    # ── Build combined context ──
    context = _build_context(active, prompts)

    # Write context block for CC
    cc_path = PROJECT / ".claude" / "last_response.txt"
    try:
        cc_path.parent.mkdir(parents=True, exist_ok=True)
        cc_path.write_text(context + "\n")
    except OSError:
        pass

    print(context)


if __name__ == "__main__":
    main()
