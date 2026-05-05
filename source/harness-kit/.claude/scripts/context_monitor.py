#!/usr/bin/env python3

import json, sys, os

from pathlib import Path


def get_project_root():
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd()


def check_context():
    root = get_project_root()
    state_file = root / ".omc" / "state" / "token-tracking-index.json"
    usage = 0
    limit = 200000

    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            usage = data.get("usage", 0)
            limit = data.get("limit", 200000)
        except Exception:
            pass

    if limit == 0:
        limit = 200000
    ratio = usage / limit

    # 50% Hand-off Alert (stdout for humans)
    if 0.5 <= ratio < 0.8:
        print(f"[context_alert]: 当前上下文已达黄金甜点区上限 ( {ratio:.1%} )。", file=sys.stderr)
        print("请立即打断当前长上下文对话！运行 /compact 压缩会话或开启新分支。", file=sys.stderr)

    # JSON output for the bash hook to consume
    output = {
        "usage": usage,
        "limit": limit,
        "percentage": ratio * 100,
        "is_danger": ratio >= 0.8
    }
    print(json.dumps(output))


if __name__ == "__main__":
    check_context()
