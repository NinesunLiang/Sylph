"""index49 S2：worktree 隔离接入 —— 隔离**代码**，共享**账本**。

背景（实测风险）：
  `git worktree add` 不会复制被 gitignore 的 `.omc/`。探针实测：worktree 内只有 `.claude/`，
  **没有 `.omc/`**。而任务文档 / 令牌 / 审计全在 `.omc/`。
  若 goal 直接在 worktree 里跑，证据会写进一个 merge 后即被删除的目录 → **证据永久丢失**。

处置：`create_worktree` 后在 worktree 内建 `.omc` → 符号链接到主树 `.omc`。
  - 代码改动 → 隔离在 worktree（可 merge、可丢弃）
  - 账本/证据 → 留在主树（多进程共享、用户可见、merge 后不丢）

既有安全门保持不变：worktree 有未提交变更时 merge 必须拒绝（Opus 裁决）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import worktree_utils  # noqa: E402


@pytest.fixture
def sandbox_worktree():
    """建一个真实 worktree，用后强制清理（含分支）。"""
    created: list[tuple[Path, str]] = []

    def _make(task_id: str):
        path, branch = worktree_utils.create_worktree(task_id)
        created.append((path, branch))
        return path, branch

    yield _make

    for path, branch in created:
        subprocess.run(["git", "worktree", "remove", "--force", str(path)],
                       cwd=str(worktree_utils.PROJECT_ROOT), capture_output=True, text=True)
        subprocess.run(["git", "branch", "-D", branch],
                       cwd=str(worktree_utils.PROJECT_ROOT), capture_output=True, text=True)


def test_worktree_gets_omc_symlink(sandbox_worktree):
    path, branch = sandbox_worktree("idx49-omc-link")
    link = path / ".omc"
    assert link.exists(), "worktree 内 .omc 不存在（证据会写进即将被删的目录）"
    assert link.is_symlink(), ".omc 应为符号链接（共享主树账本）"
    assert link.resolve() == (worktree_utils.PROJECT_ROOT / ".omc").resolve(), \
        f".omc 应指向主树，实际指向 {link.resolve()}"


def test_ledger_write_lands_in_main_tree(sandbox_worktree):
    """在 worktree 内写账本 → 必须落到主树（merge/删 worktree 后仍在）。"""
    path, _branch = sandbox_worktree("idx49-omc-write")
    probe = path / ".omc" / "state" / "_idx49_probe.txt"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("hello", encoding="utf-8")
    main_probe = worktree_utils.PROJECT_ROOT / ".omc" / "state" / "_idx49_probe.txt"
    try:
        assert main_probe.exists(), "worktree 内的账本写入没有落到主树"
        assert main_probe.read_text(encoding="utf-8") == "hello"
    finally:
        probe.unlink(missing_ok=True)


def test_branch_isolation_still_intact(sandbox_worktree):
    """隔离本身不变：worktree 内新增文件属该分支工作区，主树看不到。"""
    path, _branch = sandbox_worktree("idx49-iso")
    marker = path / "_idx49_iso_marker.txt"
    marker.write_text("x", encoding="utf-8")
    assert not (worktree_utils.PROJECT_ROOT / "_idx49_iso_marker.txt").exists(), \
        "worktree 内的代码改动不应出现在主树"


def test_merge_still_refuses_uncommitted(sandbox_worktree):
    """既有安全门回归：有未提交变更时 merge 必须拒绝（Opus 裁决，不得静默合并）。"""
    path, branch = sandbox_worktree("idx49-merge-guard")
    (path / "_idx49_dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(RuntimeError, match="uncommitted"):
        worktree_utils.merge_worktree(path, branch, "idx49-merge-guard")
