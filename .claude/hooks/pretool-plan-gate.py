#!/usr/bin/env python3
"""
pretool-plan-gate.py — Goal/ghost 模式 Phase 0 → Edit/Write 门禁

CC hook: PreToolUse (Edit|Write)
检测 goal/ghost 模式激活但 Phase 0 未完成时阻断代码变更。

Goal 模式:
  - .omc/state/tokens/lx-goal.json 存在 + phase0_passed_at 缺失 → 阻断
  - .omc/state/tokens/autonomous.active 存在 + lx-goal.json 无 phase0_passed_at → 阻断

Ghost 模式:
  - .omc/state/tokens/ghost.json 存在 + phase0_passed_at 缺失 → 阻断

输出:
  {"continue": true}          → 放行（未激活 / Phase 0 已完成 / 非 Edit|Write）
  {"continue": false, ...}    → 阻断 + 提示

精简设计：~100行，只做一件事。
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── 信号文件路径 ───
OMC_TOKENS = Path.cwd() / ".omc" / "state" / "tokens"
LX_GOAL_JSON = OMC_TOKENS / "lx-goal.json"
GHOST_JSON   = OMC_TOKENS / "ghost.json"
AUTONOMOUS   = OMC_TOKENS / "autonomous.active"


def _read_mode_file(path: Path) -> dict:
    """读取 mode JSON 文件，不存在或解析失败返回 {}"""
    try:
        if path.exists() and path.stat().st_size > 0:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _is_edit_write():
    """检测当前工具调用是否为 Edit 或 Write"""
    try:
        raw = sys.stdin.read()
        if not raw:
            return False
        data = json.loads(raw)
        tool_name = (data.get("tool_name", "") or "").lower().strip()
        return tool_name in ("edit", "write")
    except (json.JSONDecodeError, OSError):
        return False


def _check_goal_mode():
    """检查 goal 模式 Phase 0 状态。返回 None=放行，str=阻断理由"""
    # 1. 检查 lx-goal.json
    if not LX_GOAL_JSON.exists():
        return None  # goal 模式未激活，放行

    mode_data = _read_mode_file(LX_GOAL_JSON)
    if mode_data.get("phase0_passed_at"):
        return None  # Phase 0 已完成，放行

    # 2. 检查 autonomous.active 是否也激活（double check）
    autonomous_active = AUTONOMOUS.exists()

    goal = mode_data.get("goal", "？")
    return (
        "⛔ Goal 模式已激活但 Phase 0 未完成\n"
        f"   目标: {goal}\n"
        "   AI 必须先完成前置澄清:\n"
        f"   1. 确认 8 维度已覆盖 (SKILL.md §Phase 0)\n"
        f"   2. 运行: lx-goal.py phase0-done\n"
        f"   3. 验证: phase0_passed_at 已写入\n"
        + ("   autonomous.active 存在 — 无人值守模式需先 phase0-done\n" if autonomous_active else "")
    )


def _check_ghost_mode():
    """检查 ghost 模式 Phase 0 状态"""
    if not GHOST_JSON.exists():
        return None

    mode_data = _read_mode_file(GHOST_JSON)
    if mode_data.get("phase0_passed_at"):
        return None

    return (
        "⛔ Ghost 模式已激活但 Phase 0 未完成\n"
        "   AI 必须先完成前置澄清再执行代码变更"
    )


def main():
    # 只拦截 Edit|Write
    if not _is_edit_write():
        print(json.dumps({"continue": True}))
        return

    # goal 模式检查
    reason = _check_goal_mode()
    if not reason:
        reason = _check_ghost_mode()

    if reason:
        result = {
            "continue": False,
            "message": reason.strip(),
            "stderr": reason.strip(),
        }
    else:
        result = {"continue": True}

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
