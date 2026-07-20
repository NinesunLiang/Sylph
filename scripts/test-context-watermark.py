#!/usr/bin/env python3
"""Context Watermark 三段策略测试——owner 规格 50%提醒/70%只读/80%强制 验收

链路: 实测 pretool-user-approve.py(每轮尾读 transcript usage → 写 state)
     → 执行 pretool-gate.py(watermark 门,读 state 文件)
     → 决策 context_engine.py compact_decision(L2_ENHANCE)
     → 刷新 precompact-lifecycle.py(compact 前同步 compact-write)

场景:
  W1 SAFE(pct=30): 门放行(git status exit 0)
  W2 REMIND(50-70): _watermark_level 分级 + 注入行非空;门仍放行(pct=65 git status exit 0)
  W3 READONLY(pct=75): 阻断 Write(context_watermark_readonly),放行 Bash/Read
  W4 FORCE(pct=85): 阻断全部工具(context_watermark_force),含 Bash 与 Read
  W5 stale fail-open(pct=85 但 at 1 小时前): 数据过期 → 门放行
  W6 compact_decision 阈值(L2_ENHANCE): 49.9 CONTINUE / 50 COMPACT_SOON /
     80 COMPACT_NOW / 缺水位 DOWNGRADE_REQUIRED
  W7 precompact 刷新集成: precompact-lifecycle.py 跑通,compact_write=ok,
     handoff 刷新(备份/恢复真实文件,不吞生产状态)

副作用声明:
  - 备份并原样恢复 .omc/state/context-watermark.json(每轮 prompt 都会重写的生产文件)
  - 备份并原样恢复 goal 信号 autonomous.active 与 lx-goal.json(同 T1 基线口径)
  - W7 备份并原样恢复 .omc/session-handoff.md 与 .omc/state/last-user-prompt.md;
    删除测试产生的 precompact-*.json 快照
  - 门在 .omc/audit/<today>.jsonl 留测试 block 事件(惰性,无真实任务引用)

Usage: python3 scripts/test-context-watermark.py
Exit: 0 = PASS, 1 = FAIL
"""
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".claude" / "hooks" / "pretool-gate.py"
USER_APPROVE = ROOT / ".claude" / "hooks" / "pretool-user-approve.py"
PRECOMPACT = ROOT / ".claude" / "hooks" / "precompact-lifecycle.py"
WM_STATE = ROOT / ".omc" / "state" / "context-watermark.json"
SIGNAL = ROOT / ".omc" / "state" / "tokens" / "autonomous.active"
MODE_FILE = ROOT / ".omc" / "state" / "tokens" / "lx-goal.json"
HANDOFF = ROOT / ".omc" / "session-handoff.md"
LAST_PROMPT = ROOT / ".omc" / "state" / "last-user-prompt.md"
SNAP_GLOB = "precompact-*.json"
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


def run_gate(tool_name, tool_input):
    payload = {"tool_name": tool_name, "tool_input": tool_input}
    return subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(payload),
        capture_output=True, text=True, cwd=str(ROOT), timeout=30,
    )


def set_watermark(pct, age_s=0):
    at = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).isoformat()
    WM_STATE.parent.mkdir(parents=True, exist_ok=True)
    WM_STATE.write_text(json.dumps({
        "pct": pct, "used": int(pct * 1700), "limit": 170000,
        "level": "TEST", "at": at,
    }, ensure_ascii=False), encoding="utf-8")


def import_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclass 装饰器经 sys.modules[__module__] 反查,必须先注册
    spec.loader.exec_module(mod)
    return mod


# ── 备份真实状态(finally 原样恢复,绝不吞掉) ──
wm_backup = WM_STATE.read_bytes() if WM_STATE.exists() else None
signal_backup = SIGNAL.read_bytes() if SIGNAL.exists() else None
mode_backup = MODE_FILE.read_bytes() if MODE_FILE.exists() else None
handoff_backup = HANDOFF.read_bytes() if HANDOFF.exists() else None
prompt_backup = LAST_PROMPT.read_bytes() if LAST_PROMPT.exists() else None
snaps_before = set((ROOT / ".omc" / "state").glob(SNAP_GLOB))

try:
    # 统一用交互基线口径(goal 信号临时移开,同 test-goal-mode-gate T1)
    SIGNAL.unlink(missing_ok=True)
    MODE_FILE.unlink(missing_ok=True)

    print("=" * 64)
    print("W1: SAFE(pct=30) — 门放行")
    print("=" * 64)
    set_watermark(30)
    r = run_gate("Bash", {"command": "git status"})
    ok("W1 pct=30 git status → exit 0", r.returncode == 0,
       f"rc={r.returncode} out={r.stdout[:120]}")

    print("=" * 64)
    print("W2: REMIND(50-70) — 分级/注入行 + 门放行")
    print("=" * 64)
    pua = import_module("pua_watermark", USER_APPROVE)
    ok("W2 _watermark_level 49.9→SAFE", pua._watermark_level(49.9) == "SAFE")
    ok("W2 _watermark_level 50→REMIND", pua._watermark_level(50.0) == "REMIND")
    ok("W2 _watermark_level 70→READONLY", pua._watermark_level(70.0) == "READONLY")
    ok("W2 _watermark_level 80→FORCE", pua._watermark_level(80.0) == "FORCE")
    line = pua._watermark_injection_line({"level": "REMIND", "pct": 55})
    ok("W2 REMIND 注入行含 🟡 与 /compact", "🟡" in line and "/compact" in line, line)
    line = pua._watermark_injection_line({"level": "SAFE", "pct": 30})
    ok("W2 SAFE 无注入行", line == "", repr(line))
    set_watermark(65)
    r = run_gate("Bash", {"command": "git status"})
    ok("W2 pct=65 git status → exit 0(提醒层不阻断)", r.returncode == 0,
       f"rc={r.returncode} out={r.stdout[:120]}")

    print("=" * 64)
    print("W3: READONLY(pct=75) — 阻断写工具,放行只读")
    print("=" * 64)
    set_watermark(75)
    r = run_gate("Write", {"file_path": "/tmp/tt-watermark.txt", "content": "x"})
    ok("W3 Write → exit 2", r.returncode == 2, f"rc={r.returncode}")
    ok("W3 原因 context_watermark_readonly",
       "context_watermark_readonly" in r.stdout, r.stdout[:200])
    r = run_gate("Edit", {"file_path": "/tmp/tt-watermark.txt",
                          "old_string": "a", "new_string": "b"})
    ok("W3 Edit → exit 2(同属写工具)", r.returncode == 2,
       f"rc={r.returncode} out={r.stdout[:120]}")
    r = run_gate("Bash", {"command": "git status"})
    ok("W3 git status → exit 0(只读放行)", r.returncode == 0,
       f"rc={r.returncode} out={r.stdout[:120]}")
    r = run_gate("Read", {"file_path": str(ROOT / ".claude" / "rules" / "bash-style.md")})
    ok("W3 Read → exit 0(只读放行)", r.returncode == 0,
       f"rc={r.returncode} out={r.stdout[:120]}")

    print("=" * 64)
    print("W4: FORCE(pct=85) — 全工具阻断")
    print("=" * 64)
    set_watermark(85)
    r = run_gate("Bash", {"command": "git status"})
    ok("W4 git status → exit 2", r.returncode == 2, f"rc={r.returncode}")
    ok("W4 原因 context_watermark_force",
       "context_watermark_force" in r.stdout, r.stdout[:200])
    r = run_gate("Read", {"file_path": str(ROOT / ".claude" / "rules" / "bash-style.md")})
    ok("W4 Read → exit 2(全阻断含只读)", r.returncode == 2,
       f"rc={r.returncode} out={r.stdout[:120]}")

    print("=" * 64)
    print("W5: stale fail-open(pct=85, at 1 小时前) — 数据过期门放行")
    print("=" * 64)
    set_watermark(85, age_s=3600)
    r = run_gate("Bash", {"command": "git status"})
    ok("W5 过期 FORCE 数据 → exit 0(fail-open)", r.returncode == 0,
       f"rc={r.returncode} out={r.stdout[:120]}")

    print("=" * 64)
    print("W6: compact_decision 阈值(L2_ENHANCE)")
    print("=" * 64)
    ce = import_module("ce_watermark", ROOT / ".claude" / "scripts" / "context_engine.py")

    def decision(wm):
        tok = {"task": {"id": "tt-wm"},
               "session": {"level": "L2_ENHANCE", "context_watermark": wm}}
        return ce.compact_decision(tok)

    ok("W6 49.9 → CONTINUE", decision(49.9)[0] == "CONTINUE", decision(49.9))
    ok("W6 50 → COMPACT_SOON", decision(50)[0] == "COMPACT_SOON", decision(50))
    ok("W6 79.9 → COMPACT_SOON", decision(79.9)[0] == "COMPACT_SOON", decision(79.9))
    ok("W6 80 → COMPACT_NOW", decision(80)[0] == "COMPACT_NOW", decision(80))
    d = decision(None)
    ok("W6 缺水位 → DOWNGRADE_REQUIRED + requires_fallback",
       d[0] == "DOWNGRADE_REQUIRED" and d[3] is True, d)

    print("=" * 64)
    print("W7: precompact 刷新集成(compact_write 先刷 handoff 再快照)")
    print("=" * 64)
    payload = {"session_id": "tt-watermark", "transcript_path": "/tmp/tt-nonexistent.jsonl"}
    proc = subprocess.run(
        [sys.executable, str(PRECOMPACT)],
        input=json.dumps(payload),
        capture_output=True, text=True, cwd=str(ROOT), timeout=30,
    )
    ok("W7 precompact → exit 0", proc.returncode == 0,
       f"rc={proc.returncode} err={proc.stderr[:200]}")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    ok("W7 compact_write=ok", out.get("compact_write") == "ok",
       f"out={proc.stdout[:200]}")
    ok("W7 handoff 已刷新(含 Session Handoff)",
       HANDOFF.exists() and "Session Handoff" in HANDOFF.read_text(encoding="utf-8"))
finally:
    if wm_backup is not None:
        WM_STATE.parent.mkdir(parents=True, exist_ok=True)
        WM_STATE.write_bytes(wm_backup)
    else:
        WM_STATE.unlink(missing_ok=True)
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
    if handoff_backup is not None:
        HANDOFF.write_bytes(handoff_backup)
    else:
        HANDOFF.unlink(missing_ok=True)
    if prompt_backup is not None:
        LAST_PROMPT.parent.mkdir(parents=True, exist_ok=True)
        LAST_PROMPT.write_bytes(prompt_backup)
    else:
        LAST_PROMPT.unlink(missing_ok=True)
    for snap in set((ROOT / ".omc" / "state").glob(SNAP_GLOB)) - snaps_before:
        snap.unlink(missing_ok=True)

print("=" * 64)
print(f"结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
if FAIL:
    print("❌ CONTEXT WATERMARK 存在失败项")
    sys.exit(1)
print("✅ ALL PASS — 50%提醒/70%只读/80%强制 三段策略全链路成立")
