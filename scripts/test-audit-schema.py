#!/usr/bin/env python3
"""test-audit-schema.py — Round7 PKG-4 audit schema 升级对抗套件

覆盖三处生产写点(GPT 纪律: 只调生产入口,禁复制判定逻辑自证):
  P1 pretool-gate._append_audit 注入 task_id/step_id(活跃 token 在库)
  P2 调用点显式 task_id 不被覆盖(setdefault 语义)
  P3 无活跃 token → 不注入(不炸,事件仍落盘)
  A1 verify_gate.write_audit VERIFIED → claim_id/evidence_ids/status 齐
  A2 verify_gate.write_audit 非 VERIFIED → status=unverified
  A3 carros_utils.write_audit verify 缺 step → 拒写(ValueError)
  A4 carros_utils.write_audit verify 缺 result → 拒写
  A5 carros_utils.write_audit verify 缺 task_id(falsy)→ 拒写
  A6 carros_utils.write_audit 非 claim 事件(如 scope_violation)缺字段 → 放行
     (机检只卡 claim 类,不误伤普通事件)
  A7 合法 verify 事件 → 正常落盘,字段完整

退出码: 0=全过, 1=有失败
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"{tag}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclass 内省需要 sys.modules 注册
    spec.loader.exec_module(mod)
    return mod


pg = _load("pretool_gate", ROOT / ".claude" / "hooks" / "pretool-gate.py")
vg = _load("verify_gate", ROOT / ".claude" / "scripts" / "verify_gate.py")
cu = _load("carros_utils", ROOT / ".claude" / "scripts" / "carros_utils.py")


def _write_token(tokens: Path, day: str, name: str, obj: dict, mtime_offset: float = 0.0) -> Path:
    p = tokens / day / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    ts = time.time() + mtime_offset
    os.utime(p, (ts, ts))
    return p


def _read_events(audit_dir: Path) -> list[dict]:
    events: list[dict] = []
    for f in sorted(audit_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


orig_pg_tokens, orig_pg_audit = pg.TOKENS, pg.AUDIT

# ── P1/P2/P3: pretool-gate._append_audit task_id/step_id 注入 ──
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    tokens, audit = tmp_path / "tokens", tmp_path / "audit"
    tokens.mkdir(); audit.mkdir()
    _write_token(tokens, "20260720", "live.json", {
        "session": {"id": "round7-joint"},
        "task": {"id": "t-joint", "status": "active", "current_step": "S4b"},
        "stats": {"done": 3, "total": 4},
    })
    pg.TOKENS, pg.AUDIT = tokens, audit
    try:
        pg._append_audit({"event_type": "scope_violation", "actor": "hook:pretool-gate",
                          "decision": "BLOCK", "reason": "token_scope_violation", "path": "/x"})
        events = _read_events(audit)
        ev = events[-1] if events else {}
        check("P1 inject-task-id", ev.get("task_id") == "round7-joint", f"got={ev.get('task_id')}")
        check("P1 inject-step-id", ev.get("step_id") == "S4b", f"got={ev.get('step_id')}")

        pg._append_audit({"event_type": "custom", "actor": "x", "decision": "BLOCK",
                          "task_id": "explicit-task", "step_id": "S9"})
        ev = _read_events(audit)[-1]
        check("P2 explicit-not-overridden", ev.get("task_id") == "explicit-task" and ev.get("step_id") == "S9",
              f"got task_id={ev.get('task_id')} step_id={ev.get('step_id')}")
    finally:
        pg.TOKENS, pg.AUDIT = orig_pg_tokens, orig_pg_audit

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    tokens, audit = tmp_path / "tokens", tmp_path / "audit"
    tokens.mkdir(); audit.mkdir()
    pg.TOKENS, pg.AUDIT = tokens, audit
    try:
        pg._append_audit({"event_type": "scope_violation", "actor": "hook:pretool-gate",
                          "decision": "BLOCK", "reason": "x", "path": "/y"})
        events = _read_events(audit)
        check("P3 no-token-still-writes", len(events) == 1 and events[0].get("event_type") == "scope_violation",
              f"events={len(events)}")
        check("P3 no-token-no-fake-id", "task_id" not in events[0] or events[0].get("task_id") in (None, "unknown"),
              f"task_id={events[0].get('task_id')}")
    finally:
        pg.TOKENS, pg.AUDIT = orig_pg_tokens, orig_pg_audit

# ── A1/A2: verify_gate.write_audit claim 字段 ──
with tempfile.TemporaryDirectory() as tmp:
    orig_cwd = os.getcwd()
    os.chdir(tmp)  # verify_gate 写 .omc/audit 相对 cwd
    try:
        token = {"session": {"id": "task-x", "level": "L1_BASE"}, "task": {"id": "task-x"}}
        d1 = vg.VerifyDecision("VERIFIED", "all_verify_rules_matched", "S4b", ["cmd matched"], [], [])
        vg.write_audit(d1, token)
        events = _read_events(Path(".omc/audit"))
        ev = events[-1] if events else {}
        check("A1 claim-id", ev.get("claim_id") == "verify:S4b", f"got={ev.get('claim_id')}")
        check("A1 status-verified", ev.get("status") == "verified", f"got={ev.get('status')}")
        check("A1 evidence-ids-nonempty", bool(ev.get("evidence_ids")), f"got={ev.get('evidence_ids')}")
        check("A1 task-id", ev.get("task_id") == "task-x", f"got={ev.get('task_id')}")

        d2 = vg.VerifyDecision("BLOCKED", "evidence_missing", "S5", [], ["missing rule"], [])
        vg.write_audit(d2, token)
        ev = _read_events(Path(".omc/audit"))[-1]
        check("A2 status-unverified", ev.get("status") == "unverified", f"got={ev.get('status')}")
        check("A2 claim-id", ev.get("claim_id") == "verify:S5", f"got={ev.get('claim_id')}")
    finally:
        os.chdir(orig_cwd)

# ── A3..A7: carros_utils.write_audit 写时 schema 机检 ──
with tempfile.TemporaryDirectory() as tmp:
    audit_dir = Path(tmp) / "audit"

    def expect_raise(name: str, event_type: str, data: dict):
        try:
            cu.write_audit(audit_dir, event_type, data)
            check(name, False, "no ValueError raised")
        except ValueError:
            check(name, True)
        except Exception as exc:
            check(name, False, f"wrong exception: {type(exc).__name__}: {exc}")

    expect_raise("A3 missing-step-reject", "verify", {"result": "VERIFIED", "task_id": "t"})
    expect_raise("A4 missing-result-reject", "verify", {"step": "S1", "task_id": "t"})
    expect_raise("A5 falsy-task-id-reject", "verify", {"step": "S1", "result": "VERIFIED", "task_id": ""})

    # A6: 非 claim 事件缺字段 → 放行(不误伤)
    try:
        cu.write_audit(audit_dir, "scope_violation", {"path": "/x"})
        check("A6 non-claim-pass", True)
    except Exception as exc:
        check("A6 non-claim-pass", False, f"raised: {exc}")

    # A7: 合法 verify → 落盘且字段完整
    try:
        cu.write_audit(audit_dir, "verify", {"step": "S4b", "result": "VERIFIED", "task_id": "round7-joint"})
        events = _read_events(audit_dir)
        verify_events = [e for e in events if e.get("event") == "verify"]
        check("A7 valid-verify-written", bool(verify_events)
              and verify_events[-1]["data"]["step"] == "S4b",
              f"events={len(verify_events)}")
    except Exception as exc:
        check("A7 valid-verify-written", False, f"raised: {exc}")

print("---")
if failures:
    print(f"FAILED: {len(failures)} 项: {failures}")
    sys.exit(1)
print("ALL PASS (PKG-4 audit schema 对抗套件)")
sys.exit(0)
