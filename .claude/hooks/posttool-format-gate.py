#!/usr/bin/env python3
"""
posttool-format-gate.py — PostToolUse:TaskUpdate — 以人为本输出格式门禁（哲学 #5 物化）
检查任务输出是否符合"以人为本"原则：有方向感、结构化、认知负担低
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, flywheel_event, hc_emit_hook_json


def main():
    if not hc_enabled("posttool_output_format"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    # 模式检测: ghost/goal 模式下跳过
    mode = is_mode_active()
    if mode != "normal":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 解析 TaskUpdate 响应的 result 字段
    result = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            result = parsed.get("tool_response", {}).get("result", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not result:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # #5 质量检查
    has_direction = bool(re.search(
        r'下一步|下一[步個]|建议|推荐|next|suggest|recommend|you can|you should|try|action|步骤|你可以',
        result, re.IGNORECASE
    ))
    has_structure = bool(re.search(
        r'^#{1,4}\s|^[-*]\s|^\d+\.\s',
        result, re.MULTILINE
    ))
    has_summary = bool(re.search(
        r'总结|摘要|概括|综上所述|overview|summary|in short|to summarize|conclusion',
        result, re.IGNORECASE
    ))

    hints = []
    if not has_direction:
        hints.append("- 欠缺方向感：建议在回复中给出下一步/建议/行动项")
    if not has_structure:
        hints.append("- 欠缺结构化：建议用标题/列表/编号使信息更易消化")
    if not has_summary:
        hints.append("- 欠缺摘要：长回复前提供一句话总结")

    if hints:
        flywheel_event("posttool_output_format", "feedback", "P2")
        hint_text = "\n".join(hints)
        stderr_msg = f"📋 #5 以人为本 — 输出格式反馈:\n{hint_text}"
        print(stderr_msg, file=sys.stderr)
        print(hc_emit_hook_json(stderr_msg, "PostToolUse", True))

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
