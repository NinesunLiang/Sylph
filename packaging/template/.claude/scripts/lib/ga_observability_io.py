#!/usr/bin/env python3
"""I/O helpers for CarrorOS GA observability collection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def load_tokens(tokens_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    tokens: list[tuple[Path, dict[str, Any]]] = []
    if not tokens_dir.exists():
        return tokens
    for path in sorted(tokens_dir.glob("**/*.json")):
        data = read_json(path)
        if data is not None:
            tokens.append((path, data))
    return tokens


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
