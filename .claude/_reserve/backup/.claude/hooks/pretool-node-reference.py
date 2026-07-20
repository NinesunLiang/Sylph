#!/usr/bin/env python3
"""pretool-node-reference.py — PreToolUse — Agent 工具调用时注入可用 nodes 列表
Role: 检测 Agent 工具调用，注入 .claude/nodes/ 目录下可用 node 列表到上下文
"""
import json
import os
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("pretool_node_reference"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Read stdin ──
    input_str = sys.stdin.read()
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        print('{"continue": true}')
        sys.exit(0)

    # ── Check if tool_name is "Agent" ──
    tool_name = input_data.get("tool_name", "")
    if tool_name != "Agent":
        print('{"continue": true}')
        sys.exit(0)

    # ── List available nodes ──
    hooks_dir = Path(__file__).resolve().parent
    nodes_dir = (hooks_dir / ".." / "nodes").resolve()
    node_list = []
    if nodes_dir.is_dir():
        for f in sorted(nodes_dir.iterdir()):
            if f.suffix == ".md":
                node_list.append(f.stem)

    node_str = " ".join(node_list)

    # ── Emit ──
    flywheel_event("pretool_node_reference", "injected", "P2")

    result = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": f"[nodes] Available: {node_str}"
        }
    }
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0)


if __name__ == "__main__":
    main()
