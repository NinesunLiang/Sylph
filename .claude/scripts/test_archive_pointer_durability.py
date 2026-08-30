"""test_archive_pointer_durability.py — archive 时 unlink 时机

bug 1 描述：archive 时 unlink(active-resume) 过早——导致后续 verify 报
'No active task' 即使 token 本身还 active。

按铁律 #3 错误闭环：先红后绿。
"""
from __future__ import annotations

import inspect
import sys

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")
import carros_base as module


def test_unlink_after_all_validation():
    """cmd_archive 的 active-resume unlink 应在所有 validation 之后。"""
    # 读 carros_base.py 完整文件
    src = open(module.__file__).read()
    # 找 cmd_archive 函数范围
    import re
    m = re.search(r'^def cmd_archive\([^)]*\):', src, re.MULTILINE)
    assert m, "cmd_archive 函数未找到"
    start = m.start()
    # 找下一个 def 开头
    next_def = re.search(r'^def \w+', src[start+1:], re.MULTILINE)
    end = start + 1 + next_def.start() if next_def else len(src)
    archive_src = src[start:end]

    unlink_idx = archive_src.find("_aptr.unlink()")
    assert unlink_idx > 0, "cmd_archive 应有 active-resume unlink"

    # 找所有 validation 失败点（current_state != VERIFYING、require force、state_conflict 等）
    verifying_idx = archive_src.find("current_state != gsm.VERIFYING")
    assert verifying_idx > 0, "cmd_archive 应有 VERIFYING 校验"

    # unlink 必须在 VERIFYING 校验之后
    assert unlink_idx > verifying_idx, (
        f"BUG: unlink ({unlink_idx}) 在 VERIFYING 校验 ({verifying_idx}) 之前。\n"
        f"archive 失败时（VERIFYING handoff 未就绪）指针已清，后续 verify 报 'No active task'。"
    )


def test_unlink_after_all_sys_exits():
    """unlink 之后函数中不应有 sys.exit（避免 unlink 后又 exit）。"""
    src = open(module.__file__).read()
    import re
    m = re.search(r'^def cmd_archive\([^)]*\):', src, re.MULTILINE)
    start = m.start()
    next_def = re.search(r'^def \w+', src[start+1:], re.MULTILINE)
    end = start + 1 + next_def.start() if next_def else len(src)
    archive_src = src[start:end]
    unlink_idx = archive_src.find("_aptr.unlink()")
    after_unlink = archive_src[unlink_idx:]
    sys_exits = list(re.finditer(r'sys\.exit\s*\(', after_unlink))
    assert not sys_exits, (
        f"BUG: unlink 之后还有 sys.exit。已 unlink 但函数会 exit，状态不一致。"
    )