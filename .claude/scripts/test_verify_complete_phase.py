"""test_verify_complete_phase.py — bug 2 修复

bug 2 描述：归档报 'VERIFYING handoff 未就绪' 卡死。
根因：cmd_verify 只调 start_phase(VERIFYING) 不调 complete_phase(VERIFYING)，
所以 handoff status 永远不是 'ready'。

修法：cmd_verify 末尾调 complete_phase(VERIFYING) 让 handoff 就绪。
"""
from __future__ import annotations

import inspect
import sys

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")
import carros_base as module


def test_cmd_verify_calls_complete_phase_for_VERIFYING():
    """cmd_verify 应在 EXECUTING complete 后调 complete_phase(VERIFYING)。"""
    src = inspect.getsource(module.cmd_verify)
    # 必须有 'complete_phase(TASK_DIR, "VERIFYING"' 调用
    assert 'complete_phase(TASK_DIR, "VERIFYING"' in src, (
        "cmd_verify 应调 complete_phase(VERIFYING) 让 handoff 就绪。"
        f"实际 cmd_verify 源码:\n{src[:3000]}"
    )


def test_cmd_verify_complete_phase_AFTER_start_phase():
    """complete_phase(VERIFYING) 应在 start_phase(VERIFYING) 之后。"""
    src = inspect.getsource(module.cmd_verify)
    start_idx = src.find('start_phase(TASK_DIR, "VERIFYING")')
    complete_idx = src.find('complete_phase(TASK_DIR, "VERIFYING"')
    if complete_idx > 0:
        assert complete_idx > start_idx, (
            f"complete_phase(VERIFYING) ({complete_idx}) 必须在 "
            f"start_phase(VERIFYING) ({start_idx}) 之后"
        )


def test_no_duplicate_VERIFYING_complete():
    """不应重复 complete VERIFYING（避免覆盖证据）。"""
    src = inspect.getsource(module.cmd_verify)
    count = src.count('complete_phase(TASK_DIR, "VERIFYING"')
    # 只应 1 次
    assert count == 1, f"complete_phase(VERIFYING) 出现 {count} 次，应只 1 次"