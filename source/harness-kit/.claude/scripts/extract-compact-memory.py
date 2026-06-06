#!/usr/bin/env python3
"""
extract-compact-memory.py — Stop hook helper: writes structured todo-queue.md
with recent user prompts + task summary for compact recovery.

Called from stop-drain.sh on Stop event.
Writes to .omc/state/todo-queue.md (atomically via .tmp + rename).

Usage:
    python3 .claude/scripts/extract-compact-memory.py \\
        --transcript <path> \\
        --handoff <path> \\
        --dump <path> \\
        --output <path>
"""

import json, os, re, sys
from pathlib import Path

# Defaults — overridable via harness.yaml compact_query_window
MAX_PROMPTS = 20
_HARNESS_LOADED = False

def _load_config_from_harness() -> dict:
    """Read numeric config values from .claude/harness.yaml (simple key: value parsing)."""
    config = {}
    harness_candidates = [
        os.path.join(os.path.dirname(__file__), '..', 'harness.yaml'),
        os.path.join(os.path.dirname(__file__), '..', '..', '.claude', 'harness.yaml'),
    ]
    for path in harness_candidates:
        path = os.path.abspath(path)
        if os.path.isfile(path):
            try:
                with open(path, encoding='utf-8') as f:
                    for line in f:
                        # match key: value patterns (simple)
                        m = re.match(r'^\s*([a-z_]+)\s*:\s*(.+?)\s*$', line)
                        if m:
                            key, val = m.group(1), m.group(2).strip()
                            # Only pick numeric config keys relevant to compact
                            if key == 'compact_query_window' and val.isdigit():
                                config['compact_query_window'] = int(val)
                            elif key == 'compact_query_chars' and val.isdigit():
                                config['compact_query_chars'] = int(val)
                            elif key == 'todo_max_lines' and val.isdigit():
                                config['todo_max_lines'] = int(val)
            except Exception:
                pass
            break
    return config

def _get_config(key: str, default: int) -> int:
    global _HARNESS_LOADED
    if not _HARNESS_LOADED:
        cfg = _load_config_from_harness()
        globals()['_CONFIG_CACHE'] = cfg
        _HARNESS_LOADED = True
    cfg = globals().get('_CONFIG_CACHE', {})
    return cfg.get(key, default)

def _get_max_prompts() -> int:
    return _get_config('compact_query_window', 20)

def _get_max_chars() -> int:
    return _get_config('compact_query_chars', 200)

def _get_max_todo() -> int:
    return _get_config('todo_max_lines', 15)

MAX_PROMPT_CHARS = _get_max_chars()
MAX_TODO_LINES = _get_max_todo()


def parse_args():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--transcript", required=True)
    p.add_argument("--handoff", default=".omc/state/session-handoff.md")
    p.add_argument("--dump", default=".omc/state/session-dump.json")
    p.add_argument("--output", default=".omc/state/todo-queue.md")
    return p.parse_args()


def extract_user_prompts(transcript_path: str) -> list[str]:
    """Extract last N non-empty user prompts from transcript JSONL."""
    prompts = []
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") != "user":
                        continue
                    # Claude Code transcript: user prompt is at top-level content key (plain string)
                    content = entry.get("content", "")
                    if isinstance(content, str) and content.strip():
                        text = content.strip()[:MAX_PROMPT_CHARS]
                        prompts.append(text)
                    elif isinstance(content, list):
                        texts = []
                        for c in content:
                            if isinstance(c, dict) and c.get("type") in ("text",):
                                texts.append(c.get("text", ""))
                        combined = " ".join(texts).strip()[:MAX_PROMPT_CHARS]
                        if combined:
                            prompts.append(combined)
                    # Fallback: message.content as list (OpenCode etc.)
                    elif isinstance(entry.get("message"), dict):
                        mc = entry["message"].get("content", "")
                        if isinstance(mc, list):
                            texts = []
                            for c in mc:
                                if isinstance(c, dict) and c.get("type") in ("text",):
                                    texts.append(c.get("text", ""))
                            combined = " ".join(texts).strip()[:MAX_PROMPT_CHARS]
                            if combined:
                                prompts.append(combined)
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, IOError):
        pass
    return prompts[-_get_max_prompts():]


def read_handoff(path: Path) -> dict:
    """Parse session-handoff.md for completed/pending tasks.
    Returns dict with completed/pending lists and 'empty' flag.
    """
    result = {"completed": [], "pending": [], "empty": True}
    if not path.exists():
        return result
    try:
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return result  # empty content → flag as empty
        result["empty"] = False
        # Match only task items (lines starting with - [x] or - ✅), not progress headers like "✅ 16 完成"
        result["completed"] = re.findall(r'^\s*-\s*\[x\].*|^\s*-\s*✅.*', content, re.MULTILINE)[:MAX_TODO_LINES]
        # Match pending task items (lines starting with - [·] or - [ ]), not status lines like "🔄 0 进行中"
        result["pending"] = re.findall(r'^\s*-\s*\[[·\s]\].*', content, re.MULTILINE)[:MAX_TODO_LINES]
    except Exception:
        pass
    return result


def read_session_dump(path: Path) -> list:
    """Read todo_queue from session-dump.json."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("todo_queue", [])[:MAX_TODO_LINES]
    except Exception:
        return []


def write_todo_queue(prompts: list, handoff: dict, dump_todos: list, output: Path):
    """Write structured todo-queue.md atomically.
    Falls back to session-dump.json if session-handoff.md is empty/missing.
    """
    lines = ["# Todo Queue — Compact 记忆恢复", ""]

    # Determine if handoff is empty → use dump as fallback
    handoff_empty = handoff.get("empty", True)
    completed_items = []
    pending_items = []

    if handoff_empty and dump_todos:
        # Fallback: use session-dump.json as primary source
        for t in dump_todos:
            t_str = str(t).strip()
            if t_str and not re.match(r'^\s*-\s*\[x\]', t_str):
                pending_items.append(t_str)
    else:
        completed_items = handoff.get("completed", [])
        pending_items = handoff.get("pending", [])

    # Filter out completed [x] items from dump_todos and merge
    pending_dump = [str(t).strip() for t in dump_todos if not re.match(r'^\s*-\s*\[x\]', str(t))]
    all_pending = pending_items + pending_dump

    # Section 1: Recent user prompts
    lines.append("## 最近用户询问")
    lines.append("")
    if prompts:
        for i, p in enumerate(reversed(prompts), 1):
            lines.append(f"{i}. {p}")
    else:
        lines.append("（无最近询问记录）")
    lines.append("")

    # Section 2: Completed tasks
    lines.append("## 已完成任务")
    lines.append("")
    if completed_items:
        for t in completed_items:
            lines.append(f"- {t}")
    else:
        lines.append("（无）")
    lines.append("")

    # Section 3: Pending tasks
    lines.append("## 待完成任务")
    lines.append("")
    if all_pending:
        seen = set()
        for item in all_pending:
            item_str = str(item).strip()
            if item_str and item_str not in seen:
                seen.add(item_str)
                lines.append(f"- {item_str}")
    else:
        lines.append("（无）")
    lines.append("")

    # Write atomically
    tmp = output.with_suffix(".md.tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.rename(output)
    return len(lines)


def main():
    args = parse_args()
    transcript_path = args.transcript
    handoff_path = Path(args.handoff)
    dump_path = Path(args.dump)
    output_path = Path(args.output)

    # 1. Extract recent user prompts
    prompts = extract_user_prompts(transcript_path)

    # 2. Read handoff for task summary
    handoff = read_handoff(handoff_path)

    # 3. Read session dump for todo queue
    dump_todos = read_session_dump(dump_path)

    # 4. Write todo-queue.md
    line_count = write_todo_queue(prompts, handoff, dump_todos, output_path)

    print(f"[extract-compact-memory] ✅ todo-queue.md 已写入 ({line_count} 行, {len(prompts)} 条询问, {len(handoff.get('completed', []))} 已完成, {len(handoff.get('pending', [])) + len(dump_todos)} 待完成)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
