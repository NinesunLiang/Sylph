#!/usr/bin/env python3
"""subagent-guard.py — PreToolUse:Task — 约束子 agent 用量，防账单雪崩（软约束+事后对账）

Role: 约束子 agent 用量，防账单雪崩（软约束+事后对账）

R25 产品策略:
- Task 工具 schema 没有 max_turns 字段，AI 无法在 tool_input 合法传入。
- 三级 fallback: (1) tool_input.max_turns (未来 schema 支持)
  (2) description/prompt 中 max_turns=N 正则提取 (3) 默认值 (harness.yaml 可配)
- 危险 agent (executor/designer/scientist) 有默认上限即可放行 + additionalContext 提示
"""

import json
import os
import re
import sys
from pathlib import Path

# 添加 hooks 目录到 sys.path，以便导入 harness_lib
_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))

from harness_lib import (
    flywheel_event,
    hc_emit_hook_json,
    hc_enabled,
    hc_get,
    is_mode_active,
)

PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"

# 默认值（与 shell 版本一致）
DANGEROUS_TYPES = ["executor", "designer", "scientist"]
DEFAULT_MAX_TURNS = "20"


def extract_fields(raw_input: str) -> dict:
    """从 stdin JSON 提取 agent_type, max_turns, effective_source。

    三级 fallback:
      1. tool_input.max_turns (未来 schema 支持)
      2. description/prompt 中 max_turns=N
      3. 默认值 (harness.yaml subagent_guard.default_max_turns 或 20)
    """
    result = {
        "agent_type": "",
        "max_turns": "",
        "effective_source": "default",
    }

    try:
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        result["max_turns"] = DEFAULT_MAX_TURNS
        return result

    tool_input = data.get("tool_input", {}) or {}

    # Agent 类型
    agent_type = str(tool_input.get("subagent_type", "") or "")
    result["agent_type"] = re.sub(r"[^a-zA-Z0-9_:\-]", "", agent_type)

    # 第一级: tool_input.max_turns
    max_turns = str(tool_input.get("max_turns", "") or "")
    if max_turns and max_turns != "None":
        result["max_turns"] = re.sub(r"[^0-9]", "", max_turns)
        if result["max_turns"]:
            result["effective_source"] = "explicit"
            return result

    # 第二级: description/prompt 中 max_turns=N
    description = str(tool_input.get("description", "") or "")
    prompt = str(tool_input.get("prompt", "") or "")
    combined = description + " " + prompt
    match = re.search(r"max_turns[\s]*[=:][\s]*(\d+)", combined)
    if match:
        result["max_turns"] = match.group(1)
        result["effective_source"] = "explicit"
        return result

    # 第三级: 默认值
    try:
        default_mt = hc_get("subagent_guard.default_max_turns", DEFAULT_MAX_TURNS)
        result["max_turns"] = str(default_mt) if default_mt else DEFAULT_MAX_TURNS
    except Exception:
        result["max_turns"] = DEFAULT_MAX_TURNS
    result["effective_source"] = "default"
    return result


def is_dangerous_type(agent_type: str) -> bool:
    """检查 agent 类型是否属于危险类型列表（从 harness.yaml 读取）。"""
    try:
        dangerous_raw = hc_get("subagent_guard.dangerous_types", "executor designer scientist")
        dangerous_types = dangerous_raw.split()
        if not dangerous_types:
            dangerous_types = DANGEROUS_TYPES
    except Exception:
        dangerous_types = DANGEROUS_TYPES

    for dtype in dangerous_types:
        if dtype in agent_type:
            return True
    return False


def main():
    # ── 功能开关 ──
    if not hc_enabled("subagent_guard"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 模式检测: ghost/goal 降级为 log+skip ──
    mode = is_mode_active(str(STATE_DIR))
    if mode != "normal":
        print(f"[{mode}] subagent-guard 已记录（模式降级，不阻断）", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 读取 stdin ──
    raw_input = sys.stdin.read()
    if not raw_input:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 提取字段 ──
    fields = extract_fields(raw_input)
    agent_type = fields["agent_type"]
    max_turns = fields["max_turns"]
    effective_source = fields["effective_source"]

    # Fail-open: 无法解析 agent 类型 → 放行
    if not agent_type:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 判断是否为危险类型 ──
    if not is_dangerous_type(agent_type):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 危险类型处理 ──
    # 获取配置中的默认上限（用于提示文案）
    try:
        default_mt = hc_get("subagent_guard.default_max_turns", DEFAULT_MAX_TURNS)
        default_max_turns = str(default_mt) if default_mt else DEFAULT_MAX_TURNS
    except Exception:
        default_max_turns = DEFAULT_MAX_TURNS

    max_turns_int = 0
    try:
        max_turns_int = int(max_turns) if max_turns else 0
    except (ValueError, TypeError):
        max_turns_int = 0

    # 显式 max_turns → 直接放行
    if max_turns_int > 0 and effective_source == "explicit":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 默认值或空值 → 使用默认上限放行 + additionalContext 提示
    flywheel_event("subagent_guard", "default_cap", "P2")

    msg = (
        f"[subagent-guard] {agent_type} "
        f"{'未声明 max_turns，使用' if max_turns_int <= 0 else '使用'} "
        f"默认上限 {default_max_turns} 轮。"
        f"建议显式声明: executor ≤25, designer ≤20, scientist ≤15"
    )
    result = hc_emit_hook_json(msg, event="PreToolUse", continue_val=True)
    print(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
