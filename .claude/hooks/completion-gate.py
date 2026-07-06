#!/usr/bin/env python3
"""
completion-gate.py — 软完成语检测

CC hook: PostToolUse
在模型响应中检测软完成语。如果检测到，输出警告但不断行。
"""

import json
import re
import sys


SOFT_COMPLETION_PATTERNS = [
    r"应该差不多了",
    r"基本上完成了",
    r"理论上没问题",
    r"大概可以了",
    r"看起来都好了",
    r"基本上都",
    r"理论上",
    r"应该没问题",
    r"一切正常",
    # English
    r"should be done",
    r"basically finished",
    r"theoretically",
    r"looks good to me",
    r"i think it's done",
    r"probably fine",
]


def main():
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not stdin_data:
        print(json.dumps({"continue": True}))
        return 0

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True}))
        return 0

    response = payload.get("response", "") or payload.get("content", "") or ""

    # ─── 检测软完成语 ───
    matches = []
    for pat in SOFT_COMPLETION_PATTERNS:
        if re.search(pat, response, re.IGNORECASE):
            matches.append(pat)

    if matches:
        msg = f"⚠ CompletionGate: soft completion detected: {matches[:3]}"
        print(json.dumps({"continue": True, "message": msg}))
        sys.stderr.write(msg + "\n")
        return 0

    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    main()
