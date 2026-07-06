#!/usr/bin/env python3
"""
oracle_gate.py — Oracle 门禁执行器

Usage:
    python3 .omc/scripts/oracle_gate.py --check <trigger_id> [--path <path>] [--command <cmd>]

Returns: JSON with verdict/reason
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TRIGGER_RULES = {
    "cross_system": {
        "pattern": r"^(/etc/|/usr/local/|/Applications/|/System/)",
        "type": "hard_block",
        "description": "跨系统操作",
    },
    "irreversible": {
        "pattern": r"\b(rm -rf|dd |diskutil |sudo |chmod 777|> /dev/)",
        "type": "hard_block",
        "description": "不可逆操作",
    },
    "security": {
        "pattern": r"(\.ssh/|/\.env|credentials|secret|id_rsa)",
        "type": "hard_block",
        "description": "安全/权限变更",
    },
    "deploy": {
        "pattern": r"\b(deploy|release|publish|push --force|npm publish)\b",
        "type": "soft_gate",
        "description": "发布动作",
    },
    "long_idle": {
        "type": "soft_gate",
        "description": "长时间无人",
        "check": "long_idle",
    },
}

BYPASS_DIR = Path(".omc/state/oracle_bypass")
BYPASS_TTL = 86400  # 24h


def _check_bypass(task_id):
    """检查是否有有效的 bypass 文件"""
    if not BYPASS_DIR.exists():
        return False
    for f in BYPASS_DIR.glob(f"{task_id}_approved.md"):
        mtime = f.stat().st_mtime
        if time.time() - mtime < BYPASS_TTL:
            return True
    return False


def _clean_expired_bypass():
    """删除过期 bypass 文件"""
    if not BYPASS_DIR.exists():
        return
    now = time.time()
    for f in BYPASS_DIR.iterdir():
        if now - f.stat().st_mtime > BYPASS_TTL:
            f.unlink()


def oracle_check(trigger_id, path=None, command=None):
    """执行 Oracle 门禁检查"""
    rule = TRIGGER_RULES.get(trigger_id)
    if not rule:
        return {"verdict": "ACCEPT", "reason": f"Unknown trigger: {trigger_id}"}

    _clean_expired_bypass()

    # 检查 bypass
    task_id = os.environ.get("CARROROS_TASK_ID", "unknown")
    if _check_bypass(task_id):
        return {"verdict": "ACCEPT", "reason": "Bypass file active"}

    if trigger_id == "long_idle":
        return {"verdict": "WARN", "reason": "长时间无人，建议确认后操作"}

    # 路径匹配
    check_target = command or path or ""
    pattern = rule["pattern"]
    if re.search(pattern, check_target):
        if rule["type"] == "hard_block":
            return {
                "verdict": "REJECT",
                "reason": f"[{rule['description']}] 操作被 Oracle 门禁拦截: {check_target[:80]}",
            }
        else:
            return {
                "verdict": "WARN",
                "reason": f"[{rule['description']}] 需要人工确认: {check_target[:80]}",
            }

    return {"verdict": "ACCEPT", "reason": "No trigger matched"}


def main():
    args = sys.argv[1:]
    trigger_id = None
    path = None
    command = None

    i = 0
    while i < len(args):
        if args[i] == "--check" and i + 1 < len(args):
            trigger_id = args[i + 1]
            i += 2
        elif args[i] == "--path" and i + 1 < len(args):
            path = args[i + 1]
            i += 2
        elif args[i] == "--command" and i + 1 < len(args):
            command = args[i + 1]
            i += 2
        else:
            i += 1

    if not trigger_id:
        print(json.dumps({"verdict": "ACCEPT", "reason": "No trigger specified"}))
        return 0

    result = oracle_check(trigger_id, path=path, command=command)
    print(json.dumps(result))

    if result["verdict"] == "REJECT":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
