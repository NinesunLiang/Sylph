"""TDD 回归: worktree_utils.py — worktree 隔离通用化工具。

校准差异(施工前核查): Opus diff 用 parents[1] 定位根错误(carros_base 在
.claude/scripts/, parents[2] 才是根); orchestrator 不可 import(merge 不放那);
worktree_gc 放 .claude/scripts/(治理脚本真源)而非 .omc/scripts/。

安全门(Opus 裁决): gc 不得删未归档 worktree(merge 失败=人类独占裁决)。
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import worktree_utils  # noqa: E402


def test_project_root_is_repo_root():
    """worktree_utils 在 .claude/scripts/, PROJECT_ROOT 应为仓库根。"""
    assert worktree_utils.PROJECT_ROOT.name == "Carror_Base_OS", \
        f"PROJECT_ROOT 应为仓库根, 实际: {worktree_utils.PROJECT_ROOT.name}"


def test_list_isolated_parses_porcelain():
    """list_isolated_worktrees 能解析 git worktree list --porcelain。"""
    # 用真实 git 输出测试(当前仓库无 task-isolated worktree → 空列表, 不崩)
    wts = worktree_utils.list_isolated_worktrees()
    assert isinstance(wts, list)
    # 若仓库有 task-isolated worktree, 应解析出 branch
    for wt in wts:
        assert "branch" in wt and "task-isolated-" in wt["branch"]


def test_get_archived_branches_handles_missing_file():
    """worktree-archive.jsonl 不存在时, get_archived_branches 返回空集不崩。"""
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "worktree-archive.jsonl"
        branches = worktree_utils._read_archive_branches(archive)
        assert branches == set()


def test_gc_requires_execute_flag():
    """gc 默认 DRY_RUN, 不传 --execute 不执行删除(安全门)。"""
    # 直接调 main 会跑 git; 这里验证模块级 DRY_RUN 常量语义
    assert worktree_utils.DRY_RUN is True, "gc 默认必须 dry-run(守护安全门)"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
