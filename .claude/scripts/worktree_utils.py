#!/usr/bin/env python3
"""worktree_utils.py — worktree 隔离通用化工具（多智能体并发治理）。

提供 create_worktree / merge_worktree / list_isolated_worktrees / gc，
让任意 L2 任务可选 `--isolated` 在独立 git worktree 中执行，消除并发编辑冲突。

设计约束（Opus 裁决 + 设计文档 14）：
- 骨架只读由 pretool-gate 的 omc-skeleton-readonly gate 强制（本模块不管）。
- merge 失败 = 人类独占裁决，gc 不得自动删未归档 worktree（安全门）。
- 归档只写摘要到 .omc/state/audit/worktree-archive.jsonl（不复制完整 JSONL）。
- --isolated 仅人类 CLI 显式传入，hook/gate 不得自动触发。
- 纯函数、显式 PROJECT_ROOT（校准: 本文件在 .claude/scripts/, parents[2] 是仓库根）。
"""
from __future__ import annotations

import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]  # .claude/scripts/ -> 上2层 = 仓库根
WORKTREES_DIR = PROJECT_ROOT / ".claude" / "worktrees"
ARCHIVE_LOG = PROJECT_ROOT / ".omc" / "state" / "audit" / "worktree-archive.jsonl"

# gc 安全门: 默认 dry-run, 传 --execute 才真删; 未归档 worktree 永不自动删
DRY_RUN = True
STALE_DAYS = 3


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd or PROJECT_ROOT),
        capture_output=True, text=True, check=check, timeout=60,
    )


def create_worktree(task_id: str) -> tuple[Path, str]:
    """创建隔离 worktree，返回 (worktree_path, branch_name)。"""
    branch_name = f"task-isolated-{task_id}-{uuid.uuid4().hex[:8]}"
    worktree_path = WORKTREES_DIR / branch_name
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", str(worktree_path), "-b", branch_name])
    return worktree_path, branch_name


def merge_worktree(worktree_path: Path, branch_name: str, task_id: str) -> None:
    """将 isolated worktree 合并回主树并清理。

    不变式（Opus 裁决）：
      - worktree 有未提交变更 → raise（不得静默合并）
      - merge 冲突 → abort + raise（人类独占裁决）
      - 只写摘要到 worktree-archive.jsonl（不复制完整 JSONL）
      - 只有 merge 成功后才 remove worktree + 删分支
    """
    status = _run(["git", "status", "--porcelain"], cwd=worktree_path)
    if status.stdout.strip():
        raise RuntimeError(
            f"worktree {branch_name} has uncommitted changes; commit or stash before merge"
        )

    merge = _run(["git", "merge", "--no-ff", "--no-edit", branch_name], check=False)
    if merge.returncode != 0:
        _run(["git", "merge", "--abort"], check=False)
        raise RuntimeError(
            f"merge conflict on {branch_name}; human decision required.\nstderr:\n{merge.stderr}"
        )

    # 归档摘要（只记元数据，不复制完整 audit）
    ARCHIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "task_id": task_id,
        "branch": branch_name,
        "worktree_path": str(worktree_path),
        "merged_at": datetime.now(timezone.utc).isoformat(),
    }
    with ARCHIVE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    _run(["git", "worktree", "remove", "--force", str(worktree_path)])
    _run(["git", "branch", "-d", branch_name])


def list_isolated_worktrees() -> list[dict]:
    """解析 `git worktree list --porcelain`，返回 task-isolated-* worktree 列表。"""
    out = _run(["git", "worktree", "list", "--porcelain"])
    worktrees: list[dict] = []
    current: dict = {}
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch ") and "/task-isolated-" in line:
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line == "":
            if current:
                worktrees.append(current)
                current = {}
    if current:
        worktrees.append(current)
    return [w for w in worktrees if "branch" in w]


def _read_archive_branches(archive: Path) -> set[str]:
    """读取已归档 worktree 的 branch 集合（安全门判定用）。"""
    if not archive.exists():
        return set()
    branches: set[str] = set()
    for line in archive.read_text(encoding="utf-8").splitlines():
        try:
            branches.add(json.loads(line)["branch"])
        except (json.JSONDecodeError, KeyError):
            pass
    return branches


def _branch_age_days(branch: str) -> float:
    out = _run(["git", "log", "-1", "--format=%ct", branch], check=False)
    if not out.stdout.strip():
        return float("inf")  # 无 commit = 最老
    return (time.time() - int(out.stdout.strip())) / 86400


def gc(execute: bool = False) -> list[str]:
    """清理 isolated worktrees。

    安全门（Opus 裁决）：
      - 已归档 branch → 可安全 remove（merge 已完成，remove 是补救）
      - 未归档 + 超龄 → 只 WARN，人类决策后才删（gc 不自动删）
    默认 dry-run（execute=False 只打印不执行）。
    """
    archived = _read_archive_branches(ARCHIVE_LOG)
    messages: list[str] = []
    for wt in list_isolated_worktrees():
        branch = wt["branch"]
        age = _branch_age_days(branch)
        if branch in archived:
            action = "would remove" if not execute else "removed"
            messages.append(f"[{'DRY-RUN' if not execute else 'GC'}] {action} archived-stale: {branch} ({age:.1f}d)")
            if execute:
                _run(["git", "worktree", "remove", "--force", wt["path"]])
                _run(["git", "branch", "-d", branch], check=False)
        elif age > STALE_DAYS:
            messages.append(
                f"[WARN] stale unarchived worktree: {branch} ({age:.1f}d) at {wt['path']} "
                f"— HUMAN DECISION REQUIRED before gc"
            )
    return messages


if __name__ == "__main__":
    import sys
    execute = "--execute" in sys.argv
    for msg in gc(execute=execute):
        print(msg)
