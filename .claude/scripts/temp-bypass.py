#!/usr/bin/env python3
"""
temp-bypass.py — 为 PretoolGate 创建临时授权跳过令牌

用法:
  python3 .claude/scripts/temp-bypass.py --minutes 60 --reason "测试需要"

功能:
  1. 生成一个有效期 N 分钟的临时授权令牌
  2. 写入 .omc/state/temp-bypass.json
  3. 门禁检测到令牌有效时，BLOCK 降级为 BYPASS_ALLOW

安全约束:
  - 默认为 60 分钟，最长 1440 分钟 (24h)
  - 超时自动失效
  - 仅用于测试/人工授权场景
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BYPASS_PATH = Path(".omc/state/temp-bypass.json")

def usage():
    print("用法: python3 .claude/scripts/temp-bypass.py --minutes <分钟数> --reason <原因>")
    print("示例: python3 .claude/scripts/temp-bypass.py --minutes 60 --reason \"人工验收需要\"")
    sys.exit(1)

def main():
    minutes = 60
    reason = ""

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--minutes" and i + 1 < len(args):
            try:
                minutes = int(args[i + 1])
            except ValueError:
                print("ERROR: --minutes 需要整数", file=sys.stderr)
                return 1
            i += 2
        elif args[i] == "--reason" and i + 1 < len(args):
            reason = args[i + 1]
            i += 2
        else:
            print(f"ERROR: 未知参数 {args[i]}", file=sys.stderr)
            return 1

    if minutes < 1:
        minutes = 1
    if minutes > 1440:
        minutes = 1440

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=minutes)

    data = {
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "minutes": minutes,
        "reason": reason,
    }

    BYPASS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BYPASS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    msg = (
        f"\n"
        f"✅ 临时授权已创建\n"
        f"   有效期: {minutes} 分钟\n"
        f"   过期时间: {expires.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"   原因: {reason or '(未填写)'}\n"
        f"   文件: {BYPASS_PATH}\n"
        f"\n"
        f"在这期间任意 gate 检查都会自动降级为 BYPASS_ALLOW。\n"
    )
    print(msg)
    return 0

if __name__ == "__main__":
    sys.exit(main())
