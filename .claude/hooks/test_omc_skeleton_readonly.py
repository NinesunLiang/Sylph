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


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
