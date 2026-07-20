#!/usr/bin/env python3
"""
pretool-compact-writer.py — compact 时自动写 handoff

扫描 .omc/tokens/{YYYYMMDD}/ 下所有 active token，
写入 handoff 到 .claude/session-handoff.md + .omc/state/session-handoff.md
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
TOKENS_DIR = PROJECT / ".omc" / "tokens"
HANDOFF_CLAUDE = PROJECT / ".claude" / "session-handoff.md"
HANDOFF_STATE = PROJECT / ".omc" / "state" / "session-handoff.md"
COMPACT_STATE = PROJECT / ".omc" / "state" / "token-compact-state.json"


def read_stdin():
    raw = sys.stdin.read()
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def has_compact(data):
    """Check if any message content contains /compact."""
    checks = [data.get("content", "")]
    for msg in data.get("messages", []):
        c = msg.get("content", "")
        if isinstance(c, str):
            checks.append(c)
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict):
                    checks.append(str(b.get("text", "")))
    return any("/compact" in c for c in checks)


def _iter_all():
    """Yields (task_id, date_str, Path) for every token file."""
    if not TOKENS_DIR.exists():
        return
    for d in sorted(TOKENS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        for f in sorted(d.glob("*.json")):
            if f.name == "token-writer.log":
                continue
            yield f.stem, d.name, f


def find_active():
    """Returns list of (task_id, date_str, token_dict)."""
    out = []
    for tid, ds, fp in _iter_all():
        try:
            tok = json.loads(fp.read_text())
            if tok.get("task", {}).get("status") not in ("completed", "archived"):
                out.append((tid, ds, tok))
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    return out


def make_handoff(tokens):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = ["# Session Handoff", "", "Compacted: " + now, "", "## Active Tasks", ""]
    if not tokens:
        lines.append("(none)")
        lines.append("")
        return "\n".join(lines)

    for tid, ds, tok in tokens:
        task = tok.get("task", {})
        stats = tok.get("stats", {})
        session = tok.get("session", {})
        lines += [
            "### " + tid, "",
            "- **Date**: " + ds,
            "- **Status**: " + task.get("status", "?"),
            "- **Phase**: " + task.get("phase", "?"),
            "- **Current Step**: " + task.get("current_step", "?"),
            "- **Level**: " + session.get("level", "?"),
            "- **Progress**: {} / {}".format(stats.get("done", 0), stats.get("total", "?")),
            "- **Turns**: " + str(stats.get("turns", 0)),
            "- **Scope**: " + ", ".join(task.get("scope", ["(none)"])),
            "- **Token**: `.omc/tokens/{}/{}`".format(ds, tid + ".json"), "",
        ]
        audit = tok.get("audit", [])
        if audit:
            lines.append("Recent Audit:")
            for e in audit[-3:]:
                lines.append("  - [{}] {}: {}".format(e.get("by", "?"), e.get("event", "?"), e.get("detail", "")))
            lines.append("")

    lines += ["## Resume", "", "```", "python3 .omc/scripts/carros_base.py status --task-id <TASK_ID>", "```", ""]
    return "\n".join(lines)


def main():
    data = read_stdin()
    if not has_compact(data):
        print(json.dumps({"continue": True}))
        return

    active = find_active()
    content = make_handoff(active)

    for p in (HANDOFF_CLAUDE, HANDOFF_STATE):
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        except OSError:
            pass

    try:
        COMPACT_STATE.parent.mkdir(parents=True, exist_ok=True)
        COMPACT_STATE.write_text(json.dumps({
            "compacted_at": datetime.now().isoformat(),
            "active": [{"task_id": tid, "date": ds, "status": tok.get("task", {}).get("status")} for tid, ds, tok in active],
        }, indent=2))
    except OSError:
        pass

    summary = ", ".join("{} ({})".format(tid, ds) for tid, ds, _ in active) or "none"
    print(json.dumps({"continue": True, "output": {"type": "compact_handoff", "active": len(active), "tasks": summary}}))


if __name__ == "__main__":
    main()
