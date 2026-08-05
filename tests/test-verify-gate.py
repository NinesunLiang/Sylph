#!/usr/bin/env python3
"""VerifyGate Regression + Adversarial Test — PKG-A R2

三层验证（全部针对真实函数/真实 CLI，不再测内嵌副本）:
  U: _check_verified 单元 — step/task 双绑定、无通配、跨任务重放拒绝、历史无 task_id 事件拒绝
  C: verify_gate.py CLI — VERIFIED / REJECTED(软完成) / BLOCKED(无证据)
  E: carros_base.py verify 端到端 — 接线 verify_gate、task-bound audit、降级留痕、无证据硬阻断

副作用声明:
  - C 层会在 .omc/audit/<today>.jsonl 留下 3 条 task_id=tt-cli 的 verify_decision（惰性，无真实任务引用）
  - E 层创建/清理 .omc/tasks|tokens/<date>/tt-e2e-* 临时任务（finally 清理）

Usage: python3 scripts/test-verify-gate.py
Exit: 0 = PASS, 1 = FAIL
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


# ── import the modular helper used by the router ──
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
from pretool_gates.helpers import _check_verified as check_verified
os.chdir(ROOT)


def write_event(audit_dir, event):
    audit_dir.mkdir(parents=True, exist_ok=True)
    with (audit_dir / "test.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


print("=" * 64)
print("U: _check_verified 单元（真实函数 import）")
print("=" * 64)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    write_event(tdir / "state" / "audit",
                {"event": "verify", "data": {"step": "S1", "result": "VERIFIED", "task_id": "tt-u-a"}})
    ok("U1 新格式 VERIFIED+step+task 双匹配 → 放行",
       check_verified("S1", "tt-u-a", tdir) is True)
    ok("U2 step 不匹配 → 拒绝",
       check_verified("S2", "tt-u-a", tdir) is False)
    ok("U3 跨任务重放（task B 用 task A 的 VERIFIED） → 拒绝",
       check_verified("S1", "tt-u-b", tdir) is False)
    ok("U4 step_id=None 通配已死 → 拒绝",
       check_verified(None, "tt-u-a", tdir) is False)
    ok("U5 task_id=None → 拒绝",
       check_verified("S1", None, tdir) is False)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    write_event(tdir / "state" / "audit",
                {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1", "task_id": "tt-u-c"})
    ok("U6 legacy verify_decision+task 匹配 → 放行",
       check_verified("S1", "tt-u-c", tdir) is True)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    write_event(tdir / "state" / "audit",
                {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"})
    write_event(tdir / "state" / "audit",
                {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}})
    ok("U7 历史无 task_id 事件（两种格式） → 拒绝（fail-closed）",
       check_verified("S1", "tt-u-d", tdir) is False)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    write_event(tdir / "state" / "audit",
                {"event": "verify", "data": {"step": "S1", "result": "FAILED", "task_id": "tt-u-e"}})
    ok("U8 result=FAILED → 拒绝", check_verified("S1", "tt-u-e", tdir) is False)

with tempfile.TemporaryDirectory() as td:
    ok("U9 空审计 → 拒绝", check_verified("S1", "tt-u-f", Path(td)) is False)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    ad = tdir / "state" / "audit"
    ad.mkdir(parents=True)
    (ad / "test.jsonl").write_text(
        "NOT_JSON\n" + json.dumps(
            {"event": "verify", "data": {"step": "S1", "result": "VERIFIED", "task_id": "tt-u-g"}}) + "\n",
        encoding="utf-8")
    ok("U10 无效 JSON 行容错 → 仍命中有效行", check_verified("S1", "tt-u-g", tdir) is True)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    write_event(tdir / "state" / "audit", {"event": "verify", "data": "VERIFIED"})
    ok("U11 data 非 dict（畸形伪造） → 拒绝", check_verified("S1", "tt-u-h", tdir) is False)

print("=" * 64)
print("C: verify_gate.py CLI")
print("=" * 64)

VG = ROOT / ".claude/scripts/verify_gate.py"
PLAN_RULE = """# Plan

## Steps
- [ ] S1: demo
  - verify: command:echo ok
"""
EV_GOOD = """# Executor
## Conditions
- test fixture is isolated
## Key Changes
- no production files changed
## Decisions
- rationale: use the canonical verify command
## Acceptance Checklist
- [x] fixture is complete
## TDD Evidence
- dependency TDD command: echo dependency TDD → exit 0
- regression TDD command: echo regression TDD → exit 0
## S1
### EV-S1
- step: S1
- type: command
- source: echo ok
- exit_code: 0
- evidence_level: E3
"""
EV_SOFT = EV_GOOD + "- assertion: 完成了，应该没问题\n"


def run_vg(step, plan, executor, token):
    return subprocess.run(
        [sys.executable, str(VG), "--step", step,
         "--plan", str(plan), "--executor", str(executor), "--token", str(token)],
        capture_output=True, text=True, timeout=30)


def parse_decision(stdout):
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return {}


with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    (d / "plan.md").write_text(PLAN_RULE, encoding="utf-8")
    (d / "token.json").write_text(
        json.dumps({"session": {"id": "tt-cli", "level": "L1"}, "task": {}}), encoding="utf-8")
    (d / "executor.md").write_text(EV_GOOD, encoding="utf-8")
    r = run_vg("S1", d / "plan.md", d / "executor.md", d / "token.json")
    dec = parse_decision(r.stdout)
    ok("C1 有效 E3 证据 → VERIFIED(exit 0)",
       r.returncode == 0 and dec.get("decision") == "VERIFIED", r.stdout[:160])
    (d / "executor.md").write_text(EV_SOFT, encoding="utf-8")
    r = run_vg("S1", d / "plan.md", d / "executor.md", d / "token.json")
    dec = parse_decision(r.stdout)
    ok("C2 软完成证据 → REJECTED(exit 1)",
       r.returncode == 1 and dec.get("decision") == "REJECTED", r.stdout[:160])
    (d / "executor.md").write_text("# Executor\n## S1\n\n(no entries)\n", encoding="utf-8")
    r = run_vg("S1", d / "plan.md", d / "executor.md", d / "token.json")
    dec = parse_decision(r.stdout)
    ok("C3 有规则无证据 → BLOCKED(exit 1)",
       r.returncode == 1 and dec.get("decision") == "BLOCKED", r.stdout[:160])

print("=" * 64)
print("E: carros_base.py verify 端到端")
print("=" * 64)

_E2E_TMP = tempfile.TemporaryDirectory(prefix="carros-verify-e2e-")
E2E_ROOT = Path(_E2E_TMP.name)
(E2E_ROOT / ".omc").mkdir(parents=True, exist_ok=True)
shutil.copytree(ROOT / ".claude" / "scripts", E2E_ROOT / ".claude" / "scripts")
shutil.copytree(ROOT / ".claude" / "hooks", E2E_ROOT / ".claude" / "hooks")
CARROS = E2E_ROOT / ".claude/scripts/carros_base.py"
DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
E2E_TIDS = ["tt-e2e-pass", "tt-e2e-block", "tt-e2e-degrade"]
CURRENT_TOKEN = None


def run_cb(*args):
    env = os.environ.copy()
    if CURRENT_TOKEN is not None:
        env["CARROROS_TOKEN_PATH"] = str(CURRENT_TOKEN)
    return subprocess.run([sys.executable, str(CARROS), *args],
                          capture_output=True, text=True, cwd=str(E2E_ROOT), timeout=60, env=env)


def task_paths(tid):
    return (E2E_ROOT / ".omc/tokens" / DATE / f"{tid}.json", E2E_ROOT / ".omc/tasks" / DATE / tid)


def read_events(tdir):
    events = []
    adir = tdir / "state" / "audit"
    if adir.exists():
        for f in sorted(adir.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def verified_events(events):
    return [e for e in events
            if e.get("event") == "verify" and isinstance(e.get("data"), dict)
            and e["data"].get("result") == "VERIFIED"]


def cleanup():
    for tid in E2E_TIDS:
        tok, tdir = task_paths(tid)
        try:
            if tok.exists():
                tok.unlink()
            if tdir.exists():
                shutil.rmtree(tdir)
        except OSError:
            pass


# E2E 状态全部在临时 sandbox，避免当前 goal token 污染或被测试覆盖。
HANDOFF = E2E_ROOT / ".omc/session-handoff.md"

try:
    # E1/E2: 有规则+有证据 → exit 0 + [x] + task-bound VERIFIED
    tid = "tt-e2e-pass"
    CURRENT_TOKEN = None
    run_cb("init", "--task-id", tid, "--step", "S1")
    token_path, tdir = task_paths(tid)
    CURRENT_TOKEN = token_path
    (tdir / "plan.md").write_text(PLAN_RULE, encoding="utf-8")
    (tdir / "executor.md").write_text(EV_GOOD, encoding="utf-8")
    run_cb("tick", "--step", "S1")
    r = run_cb("verify", "--step", "S1")
    plan_after = (tdir / "plan.md").read_text(encoding="utf-8")
    ver = verified_events(read_events(tdir))
    ok("E1 有证据 verify → exit 0 + [x] + task-bound VERIFIED",
       r.returncode == 0 and "- [x] S1:" in plan_after
       and any(v["data"].get("task_id") == tid for v in ver),
       f"rc={r.returncode} out={r.stdout[-200:]}")
    ok("E2 Gate 回读： 本任务放行 / 他任务拒绝 / None 拒绝",
       check_verified("S1", tid, tdir) is True
       and check_verified("S1", "tt-e2e-other", tdir) is False
       and check_verified(None, tid, tdir) is False)

    # E3/E4: 有规则无证据 → exit 2 + 不标记 [x] + Gate 不放行
    tid = "tt-e2e-block"
    CURRENT_TOKEN = None
    run_cb("init", "--task-id", tid, "--step", "S1")
    token_path, tdir = task_paths(tid)
    CURRENT_TOKEN = token_path
    (tdir / "plan.md").write_text(PLAN_RULE, encoding="utf-8")
    run_cb("tick", "--step", "S1")
    r = run_cb("verify", "--step", "S1")
    plan_after = (tdir / "plan.md").read_text(encoding="utf-8")
    ok("E3 有规则无证据 → exit 2 + 不标记 [x]",
       r.returncode == 2 and "- [x] S1:" not in plan_after,
       f"rc={r.returncode} out={r.stdout[-200:]}")
    ok("E4 Gate 回读： 被阻 step 不放行", check_verified("S1", tid, tdir) is False)

    # E5/E6: L1 无验证规则 → 降级标记 + verify_degraded 留痕（非 VERIFIED）
    tid = "tt-e2e-degrade"
    CURRENT_TOKEN = None
    run_cb("init", "--task-id", tid, "--step", "S1")
    token_path, tdir = task_paths(tid)
    CURRENT_TOKEN = token_path
    (tdir / "plan.md").write_text("# Plan\n\n## Steps\n- [ ] S1: degrade\n", encoding="utf-8")
    r = run_cb("verify", "--step", "S1")
    plan_after = (tdir / "plan.md").read_text(encoding="utf-8")
    events = read_events(tdir)
    deg = [e for e in events if e.get("event") == "verify_degraded"]
    ver = verified_events(events)
    ok("E5 L1 无规则 → exit 0 + [x] + degraded 留痕",
       r.returncode == 0 and "- [x] S1:" in plan_after and len(deg) >= 1,
       f"rc={r.returncode} out={r.stdout[-200:]}")
    ok("E6 降级不产生 VERIFIED → Gate 不放行",
       len(ver) == 0 and check_verified("S1", tid, tdir) is False)
finally:
    CURRENT_TOKEN = None
    cleanup()
    _E2E_TMP.cleanup()

print("=" * 64)
total = PASS + FAIL
print(f"结果: {PASS}/{total} PASS, {FAIL} FAIL")
if FAIL > 0:
    print("❌ REGRESSION TEST FAILED")
    sys.exit(1)
print("✅ ALL PASS — verify 链（cmd_verify → verify_gate → task-bound audit → Gate6 回读）确认正确")
