#!/usr/bin/env python3
"""
context_watermark.py — 三段式水位检测

Usage:
    python3 .omc/scripts/context_watermark.py [--used <N>] [--limit <N>]

如果不传参数，尝试从环境变量或默认值计算。
默认 limit: 200000 (Anthropic 标准上下文窗口)
默认 used: 尝试从 tiktoken 或字符数/4 估算
"""
import json
import os
import sys

DEFAULT_LIMIT = 200_000


def detect_level(pct: float) -> dict:
    """返回水位级别和对应行为"""
    if pct < 40:
        return {
            "level": "SAFE",
            "icon": "🟢",
            "remark": "0-40%: 安全",
            "action": "none",
        }
    elif pct < 70:
        return {
            "level": "WARNING",
            "icon": "🟡",
            "remark": "40-70%: 警戒",
            "action": "inject_warning",
        }
    else:
        return {
            "level": "CRITICAL",
            "icon": "🔴",
            "remark": "70%+: 临界",
            "action": "block_complex",
        }


def calc_watermark(used: int = None, limit: int = None) -> dict:
    """计算水位"""
    if limit is None:
        limit = DEFAULT_LIMIT
    if used is None:
        # 优先 tiktoken
        try:
            import tiktoken

            # 估算当前进程上下文消耗
            # 在实际使用时，应该由 hooks 传递真实 token 数
            used = 0
        except ImportError:
            used = 0

    pct = round((used / limit) * 100, 1) if limit > 0 else 0
    level_info = detect_level(pct)

    return {
        "used": used,
        "limit": limit,
        "pct": pct,
        "level": level_info["level"],
        "icon": level_info["icon"],
        "remark": level_info["remark"],
        "action": level_info["action"],
    }


def main():
    args = sys.argv[1:]
    used = None
    limit = None
    i = 0
    while i < len(args):
        if args[i] == "--used" and i + 1 < len(args):
            used = int(args[i + 1])
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        else:
            i += 1

    result = calc_watermark(used=used, limit=limit)
    print(json.dumps(result))

    if result["action"] == "block_complex":
        print(f"{result['icon']} W: {result['pct']}% — {result['remark']}")
        return 2
    elif result["action"] == "inject_warning":
        print(f"{result['icon']} W: {result['pct']}% — {result['remark']}")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
