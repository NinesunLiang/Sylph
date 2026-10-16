#!/usr/bin/env python3
"""telemetry-ttl.py — 遥测 TTL 自动清理（人类裁决 2026-10-16：.omc 日期相关资源只保留 7 天）

清理范围（按 mtime）：
  .omc/state/audit/*            审计 JSONL（按天分片）
  .omc/state/telemetry/**       遥测分片（gate-pass / hook-evidence / calibration）
  .omc/tasks/<task>/scripts/    任务脚本 7 天后整体删除（临时脚本生命周期规则）
  .omc/archive/                 归档 7 天滚动清理

设计：快速、永不阻断（exit 0）、失败静默。只扫指定目录，绝不全仓 rglob。
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]
os.chdir(str(ROOT))

KEEP_DAYS = 7
_OMC = ROOT / ".omc"


def _old_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)


def _prune_files(root: Path) -> int:
    """只删 root 直接子文件中超期的 *.jsonl/*.log（不递归）。"""
    root = Path(root)
    if not root.is_dir():
        return 0
    cutoff = _old_cutoff()
    removed = 0
    try:
        children = list(root.iterdir())
    except OSError:
        return 0
    for f in children:
        try:
            if not f.is_file() or f.suffix not in (".jsonl", ".log"):
                continue
            if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def _prune_tree(root: Path) -> int:
    """遥测树（体量小，安全递归）。"""
    root = Path(root)
    if not root.is_dir():
        return 0
    cutoff = _old_cutoff()
    removed = 0
    for f in root.rglob("*"):
        try:
            if not f.is_file() or f.suffix not in (".jsonl", ".log"):
                continue
            if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def _prune_task_scripts() -> int:
    tasks = _OMC / "tasks"
    if not tasks.is_dir():
        return 0
    cutoff = _old_cutoff()
    removed = 0
    try:
        tdirs = [td for td in tasks.iterdir() if td.is_dir()]
    except OSError:
        return 0
    for td in tdirs:
        sd = td / "scripts"
        if not sd.is_dir():
            continue
        try:
            files = [x for x in sd.iterdir() if x.is_file()]
        except OSError:
            continue
        if not files:
            continue
        newest = max(
            (datetime.fromtimestamp(x.stat().st_mtime, tz=timezone.utc) for x in files),
            default=cutoff,
        )
        if newest < cutoff:
            for x in files:
                try:
                    x.unlink()
                except OSError:
                    pass
            removed += 1
    return removed


def _prune_archive() -> int:
    archive = _OMC / "archive"
    if not archive.is_dir():
        return 0
    cutoff = _old_cutoff()
    removed = 0
    try:
        entries = list(archive.iterdir())
    except OSError:
        return 0
    for e in entries:
        try:
            if datetime.fromtimestamp(e.stat().st_mtime, tz=timezone.utc) < cutoff:
                if e.is_dir():
                    shutil.rmtree(e, ignore_errors=True)
                else:
                    e.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def main() -> None:
    try:
        sys.stdin.read()
    except Exception:
        pass
    n1 = _prune_files(_OMC / "state" / "audit")
    n2 = _prune_tree(_OMC / "state" / "telemetry")
    n3 = _prune_task_scripts()
    n4 = _prune_archive()
    if n1 or n2 or n3 or n4:
        print(
            f"🧹 [telemetry-ttl] audit={n1} telemetry={n2} task-scripts={n3} archive={n4}（保留 {KEEP_DAYS} 天）",
            file=sys.stderr, flush=True,
        )
    print('{"continue": true}')
    sys.exit(0)


if __name__ == "__main__":
    main()
