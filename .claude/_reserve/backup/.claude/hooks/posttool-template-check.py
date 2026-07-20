#!/usr/bin/env python3
"""posttool-template-check.py — PostToolUse — 模板文件写入后输出 schema 提醒
Role: 检测是否写入了 .claude/task_sys/templates/ 下的模板文件，输出 schema 提醒
"""
import json
import re
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("posttool_template_check"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Read stdin ──
    input_str = sys.stdin.read()
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        print('{"continue": true}')
        sys.exit(0)

    # ── Extract file_path ──
    tool_input = input_data.get("tool_input", {}) or {}
    args = input_data.get("args", {}) or {}
    file_path = tool_input.get("file_path", "") or args.get("filePath", "") or ""

    if not file_path:
        print('{"continue": true}')
        sys.exit(0)

    # ── Check if path matches template pattern ──
    if not re.search(r"\.claude/task_sys/templates/", file_path):
        print('{"continue": true}')
        sys.exit(0)

    # ── Emit reminder ──
    flywheel_event("posttool_template_check", "checked", "P2")

    result = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"[task_sys] Template written: {file_path}. "
                "Required fields: goal, acceptance_criteria, steps, verification. "
                "See .claude/task_sys/unified_delivery_schema.md"
            )
        }
    }
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0)


if __name__ == "__main__":
    main()
