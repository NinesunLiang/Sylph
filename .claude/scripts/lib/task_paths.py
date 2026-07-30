#!/usr/bin/env python3
"""task_paths.py — 路径日期 SSOT（单一真相源）

语义契约:
  - canonical_path_date() → %Y%mdd (YYYYMMDD) — 所有路径/文件名使用此格式
  - display_date()        -> %Y-%m-%d (ISO 显示) — 所有人类可读时间戳使用此格式
  - is_canonical_dir(name) -> bool    判断是否为 YYYYMMDD 格式
  - is_legacy_dir(name)    -> bool    判断是否为 YYYY-MM-DD (legacy) 格式
  - resolve_date_dir(name) -> str|None 标准化为 YYYYMMDD; 未知格式返回 None

Reader API:
  - scan_task_dirs(root) -> list[TaskDirEntry]
  - find_conflicts(entries) -> list[conflict_dict]

Task7 Phase2 GREEN: 路径 CREATOR 只用 YYYYMMDD；Reader 兼容 legacy 不创建；
同 slug 冲突报告/拒绝覆盖。stdlib only, 无 I/O 副作用。
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── 正则 ────────────────────────────────────────────────────
_CANONICAL_RE = re.compile(r"^\d{8}$")
_LEGACY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def canonical_path_date(dt: Optional[datetime] = None) -> str:
    """YYYYMMDD — 用于所有路径/文件名创建。"""
    return (dt or datetime.now(timezone.utc)).strftime("%Y%m%d")


def display_date(dt: Optional[datetime] = None) -> str:
    """YYYY-MM-DD — 用于所有人类可读显示。"""
    return (dt or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def canonical_to_legacy(canonical: str) -> str:
    """YYYYMMDD -> YYYY-MM-DD"""
    if len(canonical) == 8 and canonical.isdigit():
        return f"{canonical[:4]}-{canonical[4:6]}-{canonical[6:8]}"
    raise ValueError(f"Not a valid canonical date: {canonical}")


def legacy_to_canonical(legacy: str) -> str:
    """YYYY-MM-DD -> YYYYMMDD"""
    if is_legacy_dir(legacy):
        return legacy.replace("-", "")
    raise ValueError(f"Not a valid legacy date: {legacy}")


def is_canonical_dir(name: str) -> bool:
    """判断目录名是否为 YYYYMMDD 格式。"""
    return bool(_CANONICAL_RE.match(name))


def is_legacy_dir(name: str) -> bool:
    """判断目录名是否为 YYYY-MM-DD (legacy) 格式。"""
    return bool(_LEGACY_RE.match(name))


def resolve_date_dir(name: str) -> Optional[str]:
    """标准化日期目录名为 YYYYMMDD; 未知格式返回 None。"""
    if is_canonical_dir(name):
        return name
    if is_legacy_dir(name):
        return name.replace("-", "")
    return None


# ─── 目录扫描器（Reader 兼容） ───────────────────────────────

@dataclass
class TaskDirEntry:
    """扫描到的 task 目录项"""
    date: str        # YYYYMMDD
    slug: str
    is_legacy: bool  # True = 来自 YYYY-MM-DD 旧目录
    path: Path       # 实际目录路径


def scan_task_dirs(
    tasks_root: Path,
    *,
    include_legacy: bool = True,
) -> list[TaskDirEntry]:
    """扫描 .omc/tasks/ 下的所有 task 目录。

    include_legacy=True: 同时扫描 legacy YYYY-MM-DD 目录（只读，不改 fs）。
    返回列表按 日期(倒序) + slug 排序。
    """
    entries: list[TaskDirEntry] = []

    if not tasks_root.exists():
        return entries

    for date_dir in sorted(tasks_root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        if not include_legacy and is_legacy_dir(date_dir.name):
            continue
        date_canonical = resolve_date_dir(date_dir.name)
        if date_canonical is None:
            continue  # 跳过未知格式目录
        is_legacy = is_legacy_dir(date_dir.name)

        for slug_dir in sorted(date_dir.iterdir()):
            if not slug_dir.is_dir():
                continue
            entries.append(TaskDirEntry(
                date=date_canonical,
                slug=slug_dir.name,
                is_legacy=is_legacy,
                path=slug_dir,
            ))

    return entries


def find_conflicts(entries: list[TaskDirEntry]) -> list[dict]:
    """查找同 slug 跨格式冲突（同时存在于 YYYYMMDD 和 YYYY-MM-DD）。

    返回冲突列表，每个元素:
      {slug, canonical_path, legacy_path, canonical_date, legacy_date}
    """
    by_slug: dict[str, list[TaskDirEntry]] = defaultdict(list)
    for e in entries:
        by_slug[e.slug].append(e)

    conflicts: list[dict] = []
    for slug, group in by_slug.items():
        has_canonical = any(not e.is_legacy for e in group)
        has_legacy = any(e.is_legacy for e in group)
        if has_canonical and has_legacy:
            canonical_entry = next(e for e in group if not e.is_legacy)
            legacy_entry = next(e for e in group if e.is_legacy)
            conflicts.append({
                "slug": slug,
                "canonical_path": str(canonical_entry.path),
                "legacy_path": str(legacy_entry.path),
                "canonical_date": canonical_entry.date,
                "legacy_date": legacy_to_canonical(legacy_entry.path.parent.name),
            })

    return conflicts
