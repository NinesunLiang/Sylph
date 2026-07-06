#!/usr/bin/env python3
"""
CarrorOS OpenCode SQLite observer.

9.md §13 — OpenCode SQLite 只读观测

Purpose:
  Estimate context watermark from OpenCode SQLite in read-only mode.

Constraints:
  - Python 3.10+ standard library only
  - Read-only SQLite connection
  - Does not expose prompt content
  - Does not produce completion evidence
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


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


def estimate_chars(db_path: str) -> int:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.cursor()

        # 尝试常见的 OpenCode SQLite schema
        candidates = [
            "SELECT content FROM messages ORDER BY rowid DESC LIMIT 200",
            "SELECT text FROM messages ORDER BY rowid DESC LIMIT 200",
            "SELECT value FROM messages ORDER BY rowid DESC LIMIT 200",
        ]

        for query in candidates:
            try:
                total = 0
                for (value,) in cursor.execute(query):
                    if isinstance(value, str):
                        total += len(value)
                return total
            except sqlite3.Error:
                continue

        raise sqlite3.Error("no_supported_message_table")
    finally:
        conn.close()


def update_watermark(token_path: Path, watermark: int) -> None:
    token = read_json(token_path)
    token.setdefault("session", {})
    token["session"]["compact_strategy"] = "watermark"
    token["session"]["context_watermark"] = max(0, min(100, watermark))
    write_json_atomic(token_path, token)


def main() -> int:
    root = Path(os.environ.get("CARROROS_ROOT", ".")).resolve()
    db_path = os.environ.get("OPENCODE_SQLITE_PATH")

    if not db_path:
        print(json.dumps({"ok": False, "failure_type": "context_watermark_unobservable"}))
        return 1

    token_path = latest_token(root)
    if not token_path:
        print(json.dumps({"ok": False, "failure_type": "no_task"}))
        return 1

    max_tokens = int(os.environ.get("CARROROS_CONTEXT_MAX_TOKENS", "200000"))

    try:
        chars = estimate_chars(db_path)
        approx_tokens = chars // 4
        watermark = int((approx_tokens / max_tokens) * 100)
        update_watermark(token_path, watermark)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "failure_type": "context_watermark_unobservable"}))
        return 1

    print(json.dumps({"ok": True, "token_path": str(token_path), "watermark": watermark}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
