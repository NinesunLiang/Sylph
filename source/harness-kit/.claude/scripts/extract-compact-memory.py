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

MAX_PROMPTS = 20
MAX_PROMPT_CHARS = 200
MAX_TODO_LINES = 15


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
    return prompts[-MAX_PROMPTS:]


def read_handoff(path: Path) -> dict:
    """Parse session-handoff.md for completed/pending tasks."""
    result = {"completed": [], "pending": []}
    if not path.exists():
        return result
    try:
        content = path.read_text(encoding="utf-8")
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
    """Write structured todo-queue.md atomically."""
    lines = ["# Todo Queue — Compact 记忆恢复", ""]

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
    if handoff["completed"]:
        for t in handoff["completed"]:
            lines.append(f"- {t}")
    else:
        lines.append("（无）")
    lines.append("")

    # Section 3: Pending tasks
    lines.append("## 待完成任务")
    lines.append("")
    # Filter out completed [x] items from dump_todos
    pending_dump = [t for t in dump_todos if not re.match(r'^\s*-\s*\[x\]', str(t))]
    items = handoff["pending"] + pending_dump
    if items:
        seen = set()
        for item in items:
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

    print(f"[extract-compact-memory] ✅ todo-queue.md 已写入 ({line_count} 行, {len(prompts)} 条询问, {len(handoff['completed'])} 已完成, {len(handoff['pending']) + len(dump_todos)} 待完成)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
