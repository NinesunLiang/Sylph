#!/usr/bin/env python3
"""
session-health-check.py — 抗衰减: 会话健康检查
Cross-platform Python resolution (DG-105)

Compares last-audit date with current date; flags if >7 days stale.
Also checks for stale lock files, large error-dna, and flywheel P0 backlog.

Commands:
  status   — Print health check report
  mark     — Mark current time as last audit timestamp
  inject   — Inject health warnings (for SessionStart hook)
"""
import sys
import os
import json
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
HEALTH_FILE = STATE_DIR / "session-health.json"
MAX_AGE_DAYS = 7
STATE_DIR.mkdir(parents=True, exist_ok=True)


def init_health():
    if not HEALTH_FILE.exists():
        with open(HEALTH_FILE, "w") as f:
            json.dump({"last_audit": None, "created": int(time.time())}, f)


def days_since_audit():
    init_health()
    try:
        with open(HEALTH_FILE) as f:
            d = json.load(f)
        last = d.get("last_audit")
        if last is None:
            return 999.0
        age = (time.time() - last) / 86400
        return age
    except Exception:
        return 999.0


def check_stale_locks():
    stale = 0
    msgs = []
    for lock_file in list(STATE_DIR.glob("*.lock")) + [STATE_DIR / "locks.json"]:
        if lock_file.exists():
            age = int(time.time() - lock_file.stat().st_mtime)
            if age > 3600:
                stale += 1
                msgs.append(f"  · {lock_file.name}: {age}s stale")
    return stale, "\n".join(msgs)


def check_error_dna_size():
    edna = STATE_DIR / "error-dna.json"
    if edna.exists():
        size = edna.stat().st_size
        if size > 102400:
            return 1, f"error-dna.json: {size} bytes (>100KB, may indicate unfixed errors)"
        else:
            return 0, ""
    return 0, ""


def check_flywheel_p0():
    flywheel = Path.home() / ".claude" / "flywheel-buffer.jsonl"
    if flywheel.exists():
        count = sum(1 for _ in flywheel.open() if _.strip())
        if count > 0:
            return 1, f"flywheel P0: {count} pending events"
        else:
            return 0, ""
    return 0, ""


cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

if cmd == "status":
    init_health()
    days = days_since_audit()
    print("═══════════════════════════════════════")
    print("  Session Health Check")
    print("═══════════════════════════════════════")
    if days > MAX_AGE_DAYS or days == 999:
        print(f"  🔴 审计年龄: {days:.1f}天 (阈值: {MAX_AGE_DAYS}天)")
        print("  建议: 运行审计脚本进行全面检查")
    else:
        print(f"  🟢 审计年龄: {days:.1f}天 (阈值: {MAX_AGE_DAYS}天)")

    stale_count, stale_msg = check_stale_locks()
    if stale_count > 0:
        print(f"  🟡 过期锁: {stale_count}个")
        if stale_msg:
            print(stale_msg)
    else:
        print("  🟢 锁状态: 正常")

    dna_warn, dna_msg = check_error_dna_size()
    if dna_warn:
        print(f"  🟡 {dna_msg}")

    fly_warn, fly_msg = check_flywheel_p0()
    if fly_warn:
        print(f"  🟡 {fly_msg}")
    print("═══════════════════════════════════════")

elif cmd == "mark":
    ts = int(time.time())
    with open(HEALTH_FILE, "w") as f:
        json.dump({"last_audit": ts, "created": ts}, f)
    now_str = time.strftime("%a %b %d %H:%M:%S %Z %Y", time.localtime(ts))
    print(f"[Health] 审计时间已标记: {now_str}")

elif cmd == "inject":
    init_health()
    days = days_since_audit()
    if days > MAX_AGE_DAYS or days == 999:
        print(f"[Health Warning] 上次审计已是 {days:.1f} 天前 (阈值: {MAX_AGE_DAYS}天)")
        print("  运行 .claude/scripts/session-health-check.py status 查看详情")

    stale_count, _ = check_stale_locks()
    if stale_count > 0:
        print(f"[Health Warning] {stale_count} 个过期锁文件")

else:
    print("Usage: session-health-check.py {status|mark|inject}")
    sys.exit(1)
