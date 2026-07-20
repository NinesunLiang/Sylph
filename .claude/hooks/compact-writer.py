#!/usr/bin/env python3
"""
compact-writer.py — PostToolUse hook (triggered by .* matcher)

On every tool call, if this is a compact turn detected via environment
(CLAUDE_CODE_COMPACT=1) or known patterns, write the current active token
info into session-handoff.md so the next session can resume.

Target path: .omc/tokens/{YYYYMMDD}/{task_id}.json
Handoff path: .omc/state/session-handoff.md

Compatible with Python 3.9+ (no str | None syntax, no match/case).
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path.cwd()
OMC_STATE = PROJECT / ".omc" / "state"
OMC_TOKENS = PROJECT / ".omc" / "tokens"
HANDOFF_PATH = OMC_STATE / "session-handoff.md"


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


def _is_compact_turn():
    """Detect if this is a context compaction / handoff turn."""
    # Environment variable set by CLI during compact
    if os.environ.get("CLAUDE_CODE_COMPACT") == "1":
        return True
    # If CLAUDE_CODE_COMPACT_FILE exists with a recent timestamp
    compact_file = os.environ.get("CLAUDE_CODE_COMPACT_FILE", "")
    if compact_file:
        try:
            mtime = os.path.getmtime(compact_file)
            age = datetime.now(timezone.utc).timestamp() - mtime
            if age < 30:  # created within last 30 seconds
                return True
        except OSError:
            pass
    return False


def _get_compact_info():
    """Gather compact info from env vars."""
    info = {}
    info["compact_elapsed"] = os.environ.get("CLAUDE_CODE_ELAPSED", "?")
    info["compact_tokens"] = os.environ.get("CLAUDE_CODE_TOKENS", "?")
    # Parse turn count
    turns_str = os.environ.get("CLAUDE_CODE_TURNS", "")
    if turns_str:
        info["compact_turns"] = turns_str
    return info


def _build_handoff(active, compact_info):
    """Build session-handoff.md content."""
    lines = []
    lines.append("# Session Handoff")
    lines.append("")
    lines.append("Generated: {}".format(datetime.now(timezone.utc).isoformat()))
    lines.append("")

    if compact_info.get("compact_elapsed"):
        lines.append("Compact stats: elapsed={} tokens={} turns={}".format(
            compact_info.get("compact_elapsed", "?"),
            compact_info.get("compact_tokens", "?"),
            compact_info.get("compact_turns", "?"),
        ))
        lines.append("")

    if not active:
        lines.append("## Active Tokens")
        lines.append("")
        lines.append("No active tokens.")
        lines.append("")
        lines.append("## Resume")
        lines.append("")
        lines.append("Start a new task: `carros_base.py init --task-id <NAME>`")
        lines.append("")
        HANDOFF_PATH.write_text("\n".join(lines))
        return

    lines.append("## Active Tokens")
    lines.append("")
    for tid, date_str, fpath, tok in active:
        task = tok.get("task", {})
        phase = task.get("phase", "?")
        step = task.get("current_step", "?")
        status = task.get("status", "?")
        stats = tok.get("stats", {})
        done = stats.get("done", 0)
        total = stats.get("total", "?")

        lines.append("### {}".format(tid))
        lines.append("- Date: {}".format(date_str))
        lines.append("- Phase: {} / Step: {} / Status: {}".format(phase, step, status))
        lines.append("- Done: {}/{}".format(done, total))
        lines.append("- Token: {}".format(fpath))
        lines.append("- Resume: `tick --task-id {}` → `status --task-id {}`".format(tid, tid))
        lines.append("")

    lines.append("## Resume Instructions")
    lines.append("")
    if len(active) == 1:
        lines.append("1. `python3 .omc/scripts/carros_base.py status --task-id {}` — check current status".format(active[0][0]))
        lines.append("2. `python3 .omc/scripts/carros_base.py tick --task-id {}` — continue".format(active[0][0]))
    else:
        lines.append("Multiple active tasks found. Pick one:")
        for tid, date_str, fpath, tok in active:
            lines.append("- `{}` — date={}, phase={}".format(tid, date_str, tok.get("task", {}).get("phase", "?")))

    HANDOFF_PATH.write_text("\n".join(lines))
    print("  [compact-writer] handoff written: {} active token(s)".format(len(active)))


def main():
    # Only act on compact turns
    if not _is_compact_turn():
        return

    if not OMC_TOKENS.exists():
        print("  [compact-writer] no .omc/tokens/ dir")
        return

    compact_info = _get_compact_info()
    active = _find_active_tokens()

    OMC_STATE.mkdir(parents=True, exist_ok=True)
    _build_handoff(active, compact_info)


if __name__ == "__main__":
    main()
