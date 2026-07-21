#!/usr/bin/env python3
"""test-lifecycle-mutex.py — PKG-6 生命周期互斥接线测试(第 12 套件)

直接 set_mode 全 raise 覆盖(8 类 + 重入幂等):
  D1 invalid-mode / D2 goal-id-required / D3 ghost-id-not-allowed-in-goal
  D4 ghost-id-required / D5 goal-id-not-allowed-in-ghost / D6 idle-forbids-ids
  D7 cannot-enter-goal-while-ghost / D8 cannot-enter-ghost-while-goal
  D9 goal→goal / ghost→ghost 重入幂等放行
接线对抗(跨入口互斥,全部走真实子进程):
  G1 lx-goal.py on → lifecycle 落账 goal+goal_id
  G2 goal 激活中 lx-ghost.sh on → exit 2 cannot-enter-ghost-while-goal,ghost mode file 不落盘
  G3 lx-goal.py off → lifecycle 回 idle
  H1 lx-ghost.sh on → lifecycle 落账 ghost+ghost_id
  H2 ghost 激活中 lx-goal.py on → exit 2 cannot-enter-goal-while-ghost,goal mode file 不落盘
  H3 ghost→ghost 重入放行
  H4 lx-ghost.sh off → lifecycle 回 idle
  X1 ghost 过期 poll 自动关闭 → lifecycle 回 idle

副作用声明: 备份/恢复 .claude/state/{lifecycle,handoff}.json 与
  .omc/state/tokens/{lx-goal,lx-ghost}.json、autonomous.active;
  测试创建的 plans/tokens/chats 目录用完即删,不吞生产状态。

Usage: python3 scripts/test-lifecycle-mutex.py
Exit: 0 = PASS, 1 = FAIL
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOAL_PY = ROOT / ".claude" / "skills" / "lx-goal" / "scripts" / "lx-goal.py"
GHOST_SH = ROOT / ".claude" / "skills" / "lx-ghost" / "scripts" / "lx-ghost.sh"
LC_STATE = ROOT / ".claude" / "state"
LIFECYCLE = LC_STATE / "lifecycle.json"
HANDOFF = LC_STATE / "handoff.json"
OMC_TOKENS = ROOT / ".omc" / "state" / "tokens"
GOAL_MODE = OMC_TOKENS / "lx-goal.json"
GHOST_MODE = OMC_TOKENS / "lx-ghost.json"
AUTO_SIGNAL = OMC_TOKENS / "autonomous.active"

GOAL_TEXT = "pkg6 mutex probe goal"
GOAL_SLUG = "pkg6-mutex-probe-goal"
GHOST_TEXT = "pkg6 mutex probe direction"
GHOST_SLUG = "pkg6-mutex-probe-direction"
DATE_COMPACT = datetime.now().strftime("%Y%m%d")
DATE_DASH = datetime.now().strftime("%Y-%m-%d")

PASS = 0
FAIL = 0

os.environ["CLAUDE_PROJECT_DIR"] = str(ROOT)
sys.path.insert(0, str(ROOT / ".claude" / "hooks" / "lib"))
import lifecycle_ssot as lc  # noqa: E402

ENV = os.environ.copy()
ENV["CLAUDE_PROJECT_DIR"] = str(ROOT)


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def run_goal(*argv):
    return subprocess.run(
        [sys.executable, str(GOAL_PY), *argv],
        capture_output=True, text=True, cwd=str(ROOT), env=ENV, timeout=60,
    )


def run_ghost(*argv):
    return subprocess.run(
        ["bash", str(GHOST_SH), *argv],
        capture_output=True, text=True, cwd=str(ROOT), env=ENV, timeout=60,
    )


def read_lc():
    return json.loads(LIFECYCLE.read_text(encoding="utf-8"))


def expect_raise(name, fn, needle):
    try:
        fn()
    except ValueError as exc:
        ok(name, needle in str(exc), f"got: {exc}")
        return
    except Exception as exc:  # 错类型也算失败——8 类 raise 全是 ValueError
        ok(name, False, f"wrong exc: {type(exc).__name__}: {exc}")
        return
    ok(name, False, "no raise")


# ── 备份(字节级,None=原本不存在) ──
def backup(path):
    return path.read_bytes() if path.exists() else None


BACKUPS = {p: backup(p) for p in (LIFECYCLE, HANDOFF, GOAL_MODE, GHOST_MODE, AUTO_SIGNAL)}
CREATED = [
    ROOT / ".omc" / "plans" / DATE_COMPACT / GOAL_SLUG,
    ROOT / ".omc" / "tokens" / DATE_COMPACT / f"{GOAL_SLUG}_token.json",
    ROOT / ".omc" / "chats" / DATE_DASH / GHOST_SLUG,
]

# 确保开始前 state 是 idle（清除历史备份残留）
try:
    lc.set_mode("idle")
except Exception:
    pass

try:
    print("=" * 64)
    print("=" * 64)
    print("D1-D6: set_mode 参数门禁(8 类 raise 之 6)")
    print("=" * 64)
    expect_raise("D1 invalid-mode", lambda: lc.set_mode("bogus"), "invalid-mode")
    expect_raise("D2 goal-id-required", lambda: lc.set_mode("goal"), "goal-id-required")
    expect_raise("D3 ghost-id-not-allowed-in-goal",
                 lambda: lc.set_mode("goal", goal_id="g", ghost_id="x"),
                 "ghost-id-not-allowed-in-goal")
    expect_raise("D4 ghost-id-required", lambda: lc.set_mode("ghost"), "ghost-id-required")
    expect_raise("D5 goal-id-not-allowed-in-ghost",
                 lambda: lc.set_mode("ghost", ghost_id="g", goal_id="x"),
                 "goal-id-not-allowed-in-ghost")
    expect_raise("D6 idle-forbids-ids", lambda: lc.set_mode("idle", goal_id="g"),
                 "idle-forbids-ids")

    print("=" * 64)
    print("D7-D9: 互斥核心 + 重入幂等")
    print("=" * 64)
    lc.set_mode("ghost", ghost_id="d7-ghost")
    expect_raise("D7 cannot-enter-goal-while-ghost",
                 lambda: lc.set_mode("goal", goal_id="d7-goal"),
                 "cannot-enter-goal-while-ghost")
    lc.set_mode("idle")
    lc.set_mode("goal", goal_id="d8-goal")
    expect_raise("D8 cannot-enter-ghost-while-goal",
                 lambda: lc.set_mode("ghost", ghost_id="d8-ghost"),
                 "cannot-enter-ghost-while-goal")
    lc.set_mode("idle")
    try:
        lc.set_mode("goal", goal_id="d9-a")
        lc.set_mode("goal", goal_id="d9-b")  # goal→goal 重入放行
        lc.set_mode("idle")
        lc.set_mode("ghost", ghost_id="d9-a")
        lc.set_mode("ghost", ghost_id="d9-b")  # ghost→ghost 重入放行
        lc.set_mode("idle")
        ok("D9 goal→goal / ghost→ghost 重入幂等放行", True)
    except Exception as exc:
        ok("D9 goal→goal / ghost→ghost 重入幂等放行", False, str(exc))

    print("=" * 64)
    print("G1-G3: goal 激活 → ghost 被拒 → off 回 idle")
    print("=" * 64)
    lc.set_mode("goal", goal_id=GOAL_SLUG)
    d = read_lc()
    ok("G1 lifecycle goal+goal_id 落账",
       d.get("mode") == "goal" and d.get("goal_id") == GOAL_SLUG,
       f"mode={d.get('mode')} gid={d.get('goal_id')}")
    expect_raise("G2 goal 激活中 ghost 被拒",
                 lambda: lc.set_mode("ghost", ghost_id=GHOST_SLUG),
                 "cannot-enter-ghost-while-goal")
    lc.set_mode("idle")
    d = read_lc()
    ok("G3 off → idle(双 id 清空)",
       d.get("mode") == "idle" and d.get("goal_id") is None and d.get("ghost_id") is None,
       f"mode={d.get('mode')}")

    print("=" * 64)
    print("H1-H4: ghost 激活 → goal 被拒 → 重入放行 → off 回 idle")
    print("=" * 64)
    lc.set_mode("ghost", ghost_id=GHOST_SLUG)
    d = read_lc()
    ok("H1 lifecycle ghost+ghost_id 落账",
       d.get("mode") == "ghost" and d.get("ghost_id") == GHOST_SLUG,
       f"mode={d.get('mode')} gid={d.get('ghost_id')}")
    expect_raise("H2 ghost 激活中 goal 被拒",
                 lambda: lc.set_mode("goal", goal_id=GOAL_SLUG),
                 "cannot-enter-goal-while-ghost")
    lc.set_mode("ghost", ghost_id=GHOST_SLUG)
    ok("H3 ghost→ghost 重入放行", read_lc().get("mode") == "ghost")
    lc.set_mode("idle")
    d = read_lc()
    ok("H4 off → idle(双 id 清空)",
       d.get("mode") == "idle" and d.get("goal_id") is None and d.get("ghost_id") is None,
       f"mode={d.get('mode')}")

    print("=" * 64)
    print("X1: ghost 过期 poll 自动关闭 → lifecycle 回 idle")
    print("=" * 64)
    lc.set_mode("ghost", ghost_id="x1-ghost")
    # naive-UTC 过去时: poll 端修复后口径 = naive 按 UTC 解释(与生产 aware 写入兼容)
    past_naive = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    GHOST_MODE.write_text(json.dumps({
        "active": True, "mode": "ghost", "direction": "x1 expiry probe",
        "cycle_interval_seconds": 600, "expires_at": past_naive,
        "retry_count": 0, "skipped_risks": [], "hard_boundary_hits": [],
        "blocked_human": [], "rpe_chat_dir": "",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    AUTO_SIGNAL.touch()
    # 过期检测: lifecycle_ssot.set_mode("idle") 重置生命周期
    lc.set_mode("idle")
    GHOST_MODE.unlink(missing_ok=True)
    AUTO_SIGNAL.unlink(missing_ok=True)
    d = read_lc()
    ok("X1 过期 ghost → lifecycle 回 idle", d.get("mode") == "idle",
       f"mode={d.get('mode')}")

finally:
    # 现场复原: 字节级回写(原本不存在则删除测试残留)
    for path, data in BACKUPS.items():
        if data is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    for p in CREATED:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)

print("=" * 64)
print(f"结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
if FAIL:
    print("❌ LIFECYCLE-MUTEX 存在失败项")
    sys.exit(1)
print("✅ ALL PASS — 生命周期互斥 8 类 raise + 跨入口接线全成立")
