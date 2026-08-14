"""TDD 回归: _check_omc_skeleton_readonly gate — .omc/**/*.md 骨架在 worktree 内只读。

Opus 裁决 + 设计文档 14 §3: 骨架只读是守护级约束, 必须进 _GATE_CORE(每次
Edit/Write 必过, 不因 L1/L2 跳过)。多智能体并发时, worktree 隔离任务不得
改写 .omc/ 骨架索引(会与主树/其他 worktree merge 冲突)。

约束: 只拦 .omc/**/*.md 的 Write/Edit/MultiEdit; 放行其他工具与其他路径。
"""
import sys
from pathlib import Path

# 与 pretool-gate.py 相同: hooks 目录进 sys.path, checks 以包方式加载(其内部用相对导入)
_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS))
sys.path.insert(0, str(_HOOKS.parent / ".claude" / "scripts"))

from pretool_gates import checks  # noqa: E402


def test_block_omc_skeleton_md():
    """Write .omc/tasks/index.md → BLOCK。"""
    payload = {"tool_name": "Write", "tool_input": {"file_path": ".omc/tasks/index.md", "content": "x"}}
    result = checks._check_omc_skeleton_readonly(payload)
    assert result is not None and result.startswith("BLOCK"), f"应 BLOCK, 实际: {result}"


def test_block_omc_nested_skeleton():
    """Edit .omc/state/index.md → BLOCK(绝对路径 + 嵌套)。"""
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "/abs/path/.omc/state/index.md", "new_string": "x"}}
    result = checks._check_omc_skeleton_readonly(payload)
    assert result is not None and result.startswith("BLOCK"), f"应 BLOCK, 实际: {result}"


def test_allow_src_file():
    """Write src/main.py → 放行。"""
    payload = {"tool_name": "Write", "tool_input": {"file_path": "src/main.py", "content": "x"}}
    assert checks._check_omc_skeleton_readonly(payload) is None


def test_allow_non_write_tool():
    """Bash 命令(非 Write/Edit)→ 放行。"""
    payload = {"tool_name": "Bash", "tool_input": {"command": "python3 x.py"}}
    assert checks._check_omc_skeleton_readonly(payload) is None


def test_allow_non_md_in_omc():
    """Write .omc/tasks/foo.json(非 .md)→ 放行(只锁骨架 .md)。"""
    payload = {"tool_name": "Write", "tool_input": {"file_path": ".omc/tasks/foo.json", "content": "{}"}}
    assert checks._check_omc_skeleton_readonly(payload) is None


def test_allow_task_doc_md():
    """index30 修复: 任务文档 executor.md 是模型按工作流必须写的——放行。"""
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": ".omc/tasks/20260815/index30-x/executor.md",
                              "content": "# Executor Evidence Ledger\n"}}
    assert checks._check_omc_skeleton_readonly(payload) is None, "任务文档被误拦(治理自噬)"


def test_allow_task_handoff_md():
    """任务目录 handoff.md 属于任务文档——放行。"""
    payload = {"tool_name": "Write",
               "tool_input": {"file_path": "/abs/.omc/tasks/20260815/index30-x/handoff.md",
                              "content": "# Handoff\n"}}
    assert checks._check_omc_skeleton_readonly(payload) is None


def test_block_archive_frozen_md():
    """index30: 归档文档冻结（archive 下 md 只读）。"""
    payload = {"tool_name": "Edit",
               "tool_input": {"file_path": ".omc/archive/20260815_x/x/executor.md", "new_string": "y"}}
    result = checks._check_omc_skeleton_readonly(payload)
    assert result is not None and result.startswith("BLOCK"), "归档冻结文档应 BLOCK"


def test_block_tokens_index_md():
    """tokens/index.md 导航索引仍只读。"""
    payload = {"tool_name": "Write", "tool_input": {"file_path": ".omc/tokens/index.md", "content": "x"}}
    result = checks._check_omc_skeleton_readonly(payload)
    assert result is not None and result.startswith("BLOCK"), "导航索引应 BLOCK"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
