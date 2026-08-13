#!/usr/bin/env python3
"""alloc_report_index.py — 报告编号原子分配（C7 并发协调完整化）。

问题（index13 E11-004 / E13-004）：多会话同时产出 benchmark 报告时，
都"看到 index12 最新"→ 都写 index13 → 相互覆盖。

解法：用 fcntl.flock 保护下扫描 Benchmarking/index*.md，分配下一个唯一编号。
多会话并发时，flock 保证每次只有一个会话能分配，其它会话拿到下一个编号。

用法:
  python3 .claude/scripts/alloc_report_index.py                 # 分配下一编号
  python3 .claude/scripts/alloc_report_index.py --preview       # 只预览不写
"""
from __future__ import annotations

import fcntl
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKING = PROJECT_ROOT / "Benchmarking"
LOCK_FILE = PROJECT_ROOT / ".omc" / "state" / "report-index.lock"


def _existing_indexes() -> list[int]:
    if not BENCHMARKING.exists():
        return []
    indexes = []
    for p in BENCHMARKING.glob("index*.md"):
        m = re.search(r"index(\d+)\.md$", p.name)
        if m:
            indexes.append(int(m.group(1)))
    return sorted(indexes)


def next_index() -> int:
    """flock 保护下分配下一个报告编号。"""
    BENCHMARKING.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            existing = _existing_indexes()
            nxt = (existing[-1] + 1) if existing else 1
            # 原子占位：创建 index{nxt}.md，避免其它会话拿到同编号
            placeholder = BENCHMARKING / f"index{nxt}.md"
            if not placeholder.exists():
                placeholder.write_text(
                    "<!-- allocated: report index placeholder (atomic) -->\n",
                    encoding="utf-8",
                )
            return nxt
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def main() -> int:
    preview = "--preview" in sys.argv
    if preview:
        existing = _existing_indexes()
        nxt = (existing[-1] + 1) if existing else 1
        print(f"PREVIEW: next report index = {nxt} (existing: {existing})")
        return 0
    nxt = next_index()
    print(f"ALLOCATED_REPORT_INDEX={nxt}")
    print(f"  placeholder: {BENCHMARKING / f'index{nxt}.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
