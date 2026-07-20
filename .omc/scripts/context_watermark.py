#!/usr/bin/env python3
"""
context_watermark.py — 三段式水位检测(owner 2026-07-20 规格)

| 水位 | 范围 | 行为 |
|------|------|------|
| 🟢 SAFE | 0-50% | 无操作 |
| 🟡 REMIND | 50-70% | 注入提醒,建议 /compact |
| 🟠 READONLY | 70-80% | 只读: 禁文件写工具(Write/Edit/MultiEdit/NotebookEdit) |
| 🔴 FORCE | 80%+ | 强制: 全工具阻断,立即 /compact |

Usage:
    python3 .omc/scripts/context_watermark.py [--used <N>] [--limit <N>]

如果不传参数，尝试从环境变量或默认值计算。
默认 limit: 1000000 (2026-07-19 实测 auto-compact 触发点 preTokens=170,508;
模型标称 1M 为宣传上限,有效窗口以实测为准;env CARROROS_CONTEXT_LIMIT 可覆盖)
生产集成: 实测在 pretool-user-approve.py(每轮尾读 transcript usage),
门执行在 pretool-gate.py(watermark 门);本脚本为离线计算/调试入口。
"""
import json
import os
import sys

DEFAULT_LIMIT = 170_000


def detect_level(pct: float) -> dict:
    """返回水位级别和对应行为(owner 规格 50/70/80)"""
    if pct >= 80:
        return {
            "level": "FORCE",
            "icon": "🔴",
            "remark": "80%+: 强制 compact",
            "action": "block_all",
        }
    elif pct >= 70:
        return {
            "level": "READONLY",
            "icon": "🟠",
            "remark": "70-80%: 只读",
            "action": "block_writes",
        }
    elif pct >= 50:
        return {
            "level": "REMIND",
            "icon": "🟡",
            "remark": "50-70%: 提醒",
            "action": "inject_warning",
        }
    else:
        return {
            "level": "SAFE",
            "icon": "🟢",
            "remark": "0-50%: 安全",
            "action": "none",
        }


def calc_watermark(used: int | None = None, limit: int | None = None) -> dict:
    """计算水位"""
    if limit is None:
        limit = int(os.environ.get("CARROROS_CONTEXT_LIMIT", "") or DEFAULT_LIMIT)
    if used is None:
        # 生产实测由 pretool-user-approve.py 尾读 transcript 完成;
        # 本入口仅离线计算/调试,未传 --used 时按 0 处理
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

    if result["action"] in ("block_all", "block_writes"):
        print(f"{result['icon']} W: {result['pct']}% — {result['remark']}")
        return 2
    elif result["action"] == "inject_warning":
        print(f"{result['icon']} W: {result['pct']}% — {result['remark']}")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
