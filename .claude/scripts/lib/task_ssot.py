#!/usr/bin/env python3
"""task_ssot.py — 活跃任务 token 单一真相源(Round7 PKG-1,三模型共识 P0)

所有 hook/脚本读取"当前活跃任务 token"必须经此模块,禁止各自 glob+mtime。

根因(2026-07-20 幻影 token 事件):mtime 取最新 + 每轮回写 → 陈旧任务自我续命,
劫持状态注入与 edit-scope 门禁。当时修复只覆盖两处 reader;排查又发现
session-start 与 statusline 两处裸 mtime 副本(共 4 源)——故收敛为单源。

语义契约:
  - 终态(archived/done/completed,顶层 status 或 task.status)永不复活;
  - 非任务 json(lx-goal 物理锁等无 task dict)不参与;
  - malformed JSON / 空文件跳过,不炸;
  - 无活跃任务 → None(调用方自行决定降级行为)。

stdlib only,无副作用,无 I/O 除读取 tokens_dir。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TERMINAL_STATUS = ("archived", "done", "completed")


def read_token(path: Path) -> dict[str, Any] | None:
    """读 token;malformed/非 dict/空 → None。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or not data:
        return None
    return data


def is_terminal(data: dict[str, Any]) -> bool:
    """终态判定:顶层 status 或 task.status 任一命中即终态。"""
    if str(data.get("status", "")).lower() in TERMINAL_STATUS:
        return True
    task = data.get("task")
    if isinstance(task, dict) and str(task.get("status", "")).lower() in TERMINAL_STATUS:
        return True
    return False


def is_task_token(data: dict[str, Any]) -> bool:
    """任务 token 判定:task 为 dict(lx-goal 物理锁等非任务 json 排除)。"""
    return isinstance(data.get("task"), dict)


def latest_active_token(tokens_dir: Path, *, require_stats: bool = False) -> Path | None:
    """mtime 降序扫描,返回第一个活跃任务 token;无 → None。

    require_stats=True: 额外要求 stats 为 dict(pretool-user-approve 水位回写需要)。
    """
    if not tokens_dir.exists():
        return None
    candidates = sorted(
        [p for p in tokens_dir.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        data = read_token(path)
        if data is None:
            continue
        if is_terminal(data):
            continue
        if not is_task_token(data):
            continue
        if require_stats and not isinstance(data.get("stats"), dict):
            continue
        return path
    return None


def latest_terminal_token(tokens_dir: Path) -> Path | None:
    """mtime 降序扫描,返回最新的「终态任务 token」;无 → None。

    Round7 PKG-3(E4 终态惯性 BLOCK):Gate 4 需要区分两种「无活跃 token」——
      a) 全新仓库/刚 archive,连终态 token 都没有 → auto-init 合法;
      b) 最新任务 token 已终态(done/archived/completed)→ 上一任务刚结束,
         auto-init 会在同一会话误生劫持 token(2026-07-20 劫持环路根因实证),
         必须 BLOCK,要求显式开工。
    只认任务 token(task 为 dict);malformed/非任务 json 跳过。
    """
    if not tokens_dir.exists():
        return None
    candidates = sorted(
        [p for p in tokens_dir.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        data = read_token(path)
        if data is None:
            continue
        if not is_task_token(data):
            continue
        if is_terminal(data):
            return path
    return None
