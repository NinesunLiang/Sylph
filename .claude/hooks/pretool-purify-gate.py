#!/usr/bin/env python3
"""pretool-purify-gate.py — PreToolUse:Edit|Write — 编辑治理文件时注入哲学纯度提醒
Role: 编辑治理文件时注入哲学纯度提醒到 AI 上下文 (不阻断)
"""
import json
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("pretool_purify_gate"):
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
    file_path = tool_input.get("file_path", "") or ""

    if not file_path:
        print('{"continue": true}')
        sys.exit(0)

    # ── Check if path matches governance files ──
    gov_patterns = (".claude/", ".opencode/", ".cursor/", "AGENTS.md", "CLAUDE.md", "VERSION.json")
    matched = False
    for p in gov_patterns:
        if p in file_path:
            matched = True
            break

    if not matched:
        print('{"continue": true}')
        sys.exit(0)

    # ── Emit ──
    flywheel_event("pretool_purify_gate", "triggered", "P2")

    result = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                f"[lx-purify] 编辑治理文件 {file_path}. "
                "哲学#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less). "
                "确认改动不违反铁律且已通过 Oracle+Meta-Oracle 双审."
            )
        }
    }
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0)


if __name__ == "__main__":
    main()
