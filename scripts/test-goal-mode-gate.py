#!/usr/bin/env python3
"""Goal 模式门行为测试——lx-goal 无人值守断裂点修复验收

断裂点: goal 模式(autonomous.active)下,pretool-gate 的 BLOCK/ASK_USER 拦截文案
唯一出路是「请用户跑 temp-bypass」→ 模型停下来求人,违反无人值守设计。
修复: goal 模式下拦截保持 fail-closed(exit 2,危险操作绝不执行),
但文案改为指引模型 blocked-human/skip-risk 记录后继续其他任务。

场景:
  T1 交互模式(无信号): ASK_USER 门 → exit 2 + temp-bypass 提示(默认行为不变)
  T2 goal 模式: ASK_USER 门(npm install) → exit 2 + goal 指引 + 无 temp-bypass 提示
  T3 goal 模式: oracle ESCALATE(L2 token + 不可解析高危) → exit 2 + goal 指引
  T4 goal 模式: 硬 BLOCK(git push --force) → exit 2 + goal 指引(fail-closed 不放行)
  T5 goal 模式: 安全命令 → exit 0 放行(不误伤)

副作用声明:
  - 备份并原样恢复 .omc/state/tokens/autonomous.active 与 lx-goal.json(不吞真实状态)
  - T3 创建/清理 .omc/tokens/<today>/tt-goal-mode.json(finally 清理)
  - 各门在 .omc/audit/<today>.jsonl 留测试事件(惰性,无真实任务引用)

Usage: python3 scripts/test-goal-mode-gate.py
Exit: 0 = PASS, 1 = FAIL
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "pretool-gate.py"
SIGNAL = ROOT / ".omc" / "state" / "tokens" / "autonomous.active"
MODE_FILE = ROOT / ".omc" / "state" / "tokens" / "lx-goal.json"
PASS = 0
FAIL = 0


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def run_hook(cmd):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, cwd=str(ROOT), timeout=30,
    )


today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
tok_dir = ROOT / ".omc" / "tokens" / today
tok_path = tok_dir / "tt-goal-mode.json"

# ── 备份真实状态(finally 原样恢复,绝不吞掉) ──
signal_backup = SIGNAL.read_bytes() if SIGNAL.exists() else None
mode_backup = MODE_FILE.read_bytes() if MODE_FILE.exists() else None

try:
    print("=" * 64)
    print("T1: 交互模式基线（临时移开 goal 状态）")
    print("=" * 64)
    SIGNAL.unlink(missing_ok=True)
    MODE_FILE.unlink(missing_ok=True)
    r = run_hook("npm install lodash")
    ok("T1 ASK_USER → exit 2", r.returncode == 2, f"rc={r.returncode}")
    ok("T1 含 temp-bypass 用户提示", "temp-bypass" in r.stdout, r.stdout[:160])
    ok("T1 无 goal 指引", "blocked-human" not in r.stdout, r.stdout[:160])

    print("=" * 64)
    print("T2-T5: goal 模式（未过期信号 + mode file）")
    print("=" * 64)
    SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    SIGNAL.write_text(json.dumps({"activated": now.isoformat()}), encoding="utf-8")
    MODE_FILE.write_text(json.dumps({
        "active": True, "mode": "goal", "goal": "tt-goal-mode-test",
        "activated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }, ensure_ascii=False), encoding="utf-8")

    r = run_hook("npm install lodash")
    ok("T2 ASK_USER → exit 2(fail-closed 保持)", r.returncode == 2, f"rc={r.returncode}")
    ok("T2 含 goal 记录指引", "blocked-human" in r.stdout, r.stdout[:200])
    ok("T2 不再指向 temp-bypass 求助", "temp-bypass" not in r.stdout, r.stdout[:200])

    tok_dir.mkdir(parents=True, exist_ok=True)
    tok_path.write_text(json.dumps({
        "task": {"current_step": "S1", "status": "active"},
        "session": {"id": "tt-goal-mode", "level": "L2_ENHANCE",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()},
    }, ensure_ascii=False), encoding="utf-8")
    r = run_hook("bash -c 'SKIP_VERIFY")
    ok("T3 oracle ESCALATE → exit 2", r.returncode == 2, f"rc={r.returncode} out={r.stdout[:120]}")
    ok("T3 含 goal 记录指引", "blocked-human" in r.stdout, r.stdout[:200])

    r = run_hook("git push --force origin main")
    ok("T4 硬 BLOCK → exit 2(危险操作绝不放行)", r.returncode == 2, f"rc={r.returncode}")
    ok("T4 含 goal 记录指引", "blocked-human" in r.stdout, r.stdout[:200])

    r = run_hook("git status")
    ok("T5 安全命令 → exit 0 放行", r.returncode == 0, f"rc={r.returncode} out={r.stdout[:120]}")

    print("=" * 64)
    print("T6: 过期 goal 模式 → 按交互模式处理（DG-46 半态防护）")
    print("=" * 64)
    MODE_FILE.write_text(json.dumps({
        "active": True, "mode": "goal", "goal": "tt-goal-mode-expired",
        "activated_at": (now - timedelta(hours=7)).isoformat(),
        "expires_at": (now - timedelta(hours=1)).isoformat(),
    }, ensure_ascii=False), encoding="utf-8")
    r = run_hook("npm install lodash")
    ok("T6 过期模式 → exit 2 且含 temp-bypass 提示(交互口径)", r.returncode == 2 and "temp-bypass" in r.stdout, f"rc={r.returncode} out={r.stdout[:160]}")
finally:
    if signal_backup is not None:
        SIGNAL.parent.mkdir(parents=True, exist_ok=True)
        SIGNAL.write_bytes(signal_backup)
    else:
        SIGNAL.unlink(missing_ok=True)
    if mode_backup is not None:
        MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        MODE_FILE.write_bytes(mode_backup)
    else:
        MODE_FILE.unlink(missing_ok=True)
    tok_path.unlink(missing_ok=True)

print("=" * 64)
print(f"结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
if FAIL:
    print("❌ GOAL-MODE GATE 存在失败项")
    sys.exit(1)
print("✅ ALL PASS — goal 模式拦截 fail-closed 且不再指向求人,无人值守流恢复")
