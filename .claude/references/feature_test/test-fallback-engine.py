#!/usr/bin/env python3
"""test-fallback-engine.py — Fallback Engine 15种失败分类 × 4种决策 全面验收

覆盖:
  D: decide() 决策矩阵 (15 failure types × 3 风险等级)
  T: token 提取 (task_id, step, level, risk)
  N: None/null token 防护 (已修 bug 回归)
  H: HIGH_RISK_HINTS 风险提示词
  M: diff_summary 自动风险推导
  I: update_token / task_paths / write_audit IO
  C: main() CLI 入口

用法: python3 scripts/test-fallback-engine.py
退出码: 0=全过, 1=有失败
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))
import fallback_engine as fe

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


def make_token(
    task_id: str = "test-task",
    status: str = "active",
    level: str = "L1_BASE",
    risk_hints: list[str] | None = None,
    files: int = 0,
    insertions: int = 0,
    deletions: int = 0,
    goal_id: str = "",
) -> dict:
    t: dict[str, Any] = {
        "task": {"id": task_id, "status": status, "risk_hints": risk_hints or [],
                 "diff_summary": {"files_changed": files, "insertions": insertions, "deletions": deletions}},
        "session": {"id": f"session-{task_id}", "level": level, "goal_id": goal_id},
    }
    # Ensure current_step exists for tests that check it
    t["task"]["current_step"] = "S1"
    return t


def token_path(name: str) -> Path:
    return Path(tempfile.mkdtemp()) / f"{name}.json"


def none_token() -> None:
    return None


print("=" * 64)
print("D: decide() 决策矩阵 — 15 failure types × 风险等级")
print("=" * 64)

# D1-D6: Non-downgradeable block types (always BLOCKED regardless of risk)
NON_DOWNGRADEABLE = [
    "audit_write_failed", "state_conflict", "verify_not_completed",
    "scope_violation", "production_approval_missing",
    "resume_state_unrecoverable", "python_script_failed", "unknown_failure",
]
for ft in NON_DOWNGRADEABLE:
    d = fe.decide(ft, make_token())
    is_not_verify = ft != "verify_not_completed"
    exp_user = is_not_verify
    ok(f"D1 {ft} → BLOCKED", d.decision == "BLOCKED", f"got={d.decision}")
    ok(f"D1 {ft} requires_user={exp_user}", d.requires_user == exp_user, f"got={d.requires_user}")

# D7: cli_hook_failed → CONTINUE (status display only)
d = fe.decide("cli_hook_failed", make_token())
ok("D7 cli_hook_failed → CONTINUE", d.decision == "CONTINUE", f"got={d.decision}")
ok("D7 requires_user=False", not d.requires_user)

# D8: context_watermark_unobservable → DOWNGRADE_TO_BASE
d = fe.decide("context_watermark_unobservable", make_token())
ok("D8 watermark → DOWNGRADE_TO_BASE", d.decision == "DOWNGRADE_TO_BASE", f"got={d.decision}")
ok("D8 level_after=L1_BASE", d.level_after == "L1_BASE")

# D9-D11: Enhance/oracle/meta_oracle unavailable (risk-dependent)
for ft in ("enhance_model_unavailable", "oracle_unavailable", "meta_oracle_unavailable"):
    # High risk → BLOCKED
    tok = make_token(risk_hints=["production"])
    d = fe.decide(ft, tok)
    ok(f"D9 {ft} high_risk → BLOCKED", d.decision == "BLOCKED", f"got={d.decision}")

    # Medium risk → ASK_USER (via diff_summary files>=5, NOT HIGH_RISK_HINTS)
    tok = make_token(risk_hints=[], files=5)
    d = fe.decide(ft, tok)
    ok(f"D10 {ft} medium_risk → ASK_USER", d.decision == "ASK_USER", f"got={d.decision}")

    # Low risk → DOWNGRADE_TO_BASE
    tok = make_token()
    d = fe.decide(ft, tok)
    ok(f"D11 {ft} low_risk → DOWNGRADE_TO_BASE", d.decision == "DOWNGRADE_TO_BASE", f"got={d.decision}")

# D12-D13: authorization_missing, dependency_risk_unreviewed
for ft in ("authorization_missing", "dependency_risk_unreviewed"):
    # High risk → BLOCKED
    tok = make_token(risk_hints=["permission_change"])
    d = fe.decide(ft, tok)
    ok(f"D12 {ft} high → BLOCKED", d.decision == "BLOCKED", f"got={d.decision}")

    # Low risk → ASK_USER
    tok = make_token()
    d = fe.decide(ft, tok)
    ok(f"D13 {ft} low → ASK_USER", d.decision == "ASK_USER", f"got={d.decision}")

# D14: unknown failure type → mapped to unknown_failure → BLOCKED
d = fe.decide("nonexistent_type", make_token())
ok("D14 unknown_type → BLOCKED", d.decision == "BLOCKED", f"got={d.decision}")

print()
print("=" * 64)
print("T: token 提取函数")
print("=" * 64)

tok = make_token(task_id="my-task", level="L2_ENHANCE")
ok("T1 task_id_from_token", fe.task_id_from_token(tok) == "my-task", f"got={fe.task_id_from_token(tok)}")
ok("T2 level_from_token", fe.level_from_token(tok) == "L2_ENHANCE", f"got={fe.level_from_token(tok)}")
ok("T3 current_step_from_token", fe.current_step_from_token(tok) == "S1", f"got={fe.current_step_from_token(tok)}")

print()
print("=" * 64)
print("N: None/null token 防护 (bug 回归)")
print("=" * 64)

ok("N1 task_id_from_token(None)",
   fe.task_id_from_token(none_token()) == "unknown_task",
   f"got={fe.task_id_from_token(none_token())}")
ok("N2 level_from_token(None)",
   fe.level_from_token(none_token()) == "L1_BASE",
   f"got={fe.level_from_token(none_token())}")
ok("N3 current_step_from_token(None)",
   fe.current_step_from_token(none_token()) is None,
   f"got={fe.current_step_from_token(none_token())}")
ok("N4 risk_from_token(None) → low",
   fe.risk_from_token(none_token()) == "low",
   f"got={fe.risk_from_token(none_token())}")
ok("N5 decide with None token (no crash)",
   fe.decide("scope_violation", {}).decision == "BLOCKED",
   f"got={fe.decide('scope_violation', {}).decision}")

# Token with null task field (real-world: .omc/state/token.json has "task": null)
tok_null = {"session": {"clean": True}, "task": None}
d = fe.decide("scope_violation", tok_null)
ok("N6 decide with task=null (no crash)",
   d.decision == "BLOCKED",
   f"got={d.decision}")

print()
print("=" * 64)
print("H: HIGH_RISK_HINTS 风险提示词")
print("=" * 64)

for hint in fe.HIGH_RISK_HINTS:
    tok = make_token(risk_hints=[hint])
    d = fe.decide("oracle_unavailable", tok)
    ok(f"H1 hint={hint} → BLOCKED", d.decision == "BLOCKED", f"got={d.decision}")

# No matching hint → low risk wake
tok = make_token(risk_hints=["unrelated"])
d = fe.decide("oracle_unavailable", tok)
ok("H2 no matching hint → DOWNGRADE_TO_BASE", d.decision == "DOWNGRADE_TO_BASE", f"got={d.decision}")

# Explicit risk override (should take precedence over hints)
tok = make_token(risk_hints=["production"])
d = fe.decide("oracle_unavailable", tok, explicit_risk="low")
ok("H3 explicit risk=low overrides hints → DOWNGRADE_TO_BASE",
   d.decision == "DOWNGRADE_TO_BASE",
   f"got={d.decision}")

print()
print("=" * 64)
print("M: diff_summary 自动风险推导")
print("=" * 64)

# files_changed >= 5
tok = make_token(files=5)
ok("M1 files=5 → medium risk",
   fe.risk_from_token(tok) == "medium",
   f"got={fe.risk_from_token(tok)}")

# insertions + deletions >= 500
tok = make_token(files=0, insertions=300, deletions=200)
ok("M2 changes=500 → medium risk",
   fe.risk_from_token(tok) == "medium",
   f"got={fe.risk_from_token(tok)}")

# Small change → low
tok = make_token(files=1, insertions=10, deletions=5)
ok("M3 small change → low risk",
   fe.risk_from_token(tok) == "low",
   f"got={fe.risk_from_token(tok)}")

print()
print("=" * 64)
print("I: IO 函数 (update_token / task_paths / write_audit)")
print("=" * 64)

with tempfile.TemporaryDirectory() as tmp:
    old_cwd = os.getcwd()
    os.chdir(tmp)
    try:
        tp = Path(tmp) / ".omc" / "state" / "token.json"
        tp.parent.mkdir(parents=True)
        tok = make_token(task_id="io-test")
        tp.write_text(json.dumps(tok))

        d = fe.decide("scope_violation", tok)
        handoff_path, executor_path, audit_paths = fe.task_paths(tok)

        ok("I1 task_paths returns 3 paths", len(audit_paths) == 3, f"got={len(audit_paths)}")

        # update_token writes BLOCKED status
        fe.update_token(tp, tok, d)
        reloaded = json.loads(tp.read_text())
        ok("I2 update_token sets blocked status",
           reloaded.get("task", {}).get("status") == "blocked",
           f"got={reloaded.get('task',{}).get('status')}")

        # append_handoff
        fe.append_handoff(handoff_path, d)
        ok("I3 append_handoff writes to handoff",
           handoff_path.exists() and handoff_path.stat().st_size > 0,
           f"exists={handoff_path.exists()}")

        # append_executor_note
        fe.append_executor_note(executor_path, tok, d)
        ok("I4 append_executor_note writes to executor",
           executor_path.exists() and executor_path.stat().st_size > 0,
           f"exists={executor_path.exists()}")

        # write_audit
        fe.write_audit(tok, d, audit_paths)
        audit_dir = Path(".omc/audit")
        audit_files = list(audit_dir.glob("*.jsonl"))
        ok("I5 write_audit creates audit log entry",
           len(audit_files) >= 1,
           f"count={len(audit_files)}")

    finally:
        os.chdir(old_cwd)

# I6: update_token with null task (regression)
with tempfile.TemporaryDirectory() as tmp:
    tp = Path(tmp) / "token.json"
    tp.write_text(json.dumps({"session": {}, "task": None}))
    d = fe.decide("scope_violation", {"session": {}, "task": None})
    fe.update_token(tp, {"session": {}, "task": None}, d)
    reloaded = json.loads(tp.read_text())
    ok("I6 update_token with task=null (no crash)",
       reloaded.get("task", {}).get("status") == "blocked",
       f"got={reloaded.get('task',{}).get('status')}")

print()
print("=" * 64)
print("C: CLI 入口")
print("=" * 64)

# save and restore argv
old_argv = sys.argv
sys.argv = ["fallback_engine.py", "scope_violation"]
try:
    rc = fe.main()
    ok("C1 scope_violation CLI → exit 1 (BLOCKED)", rc == 1, f"got={rc}")
except Exception as e:
    ok("C1 scope_violation CLI (no crash)", False, f"exception={e}")

sys.argv = ["fallback_engine.py", "cli_hook_failed"]
try:
    rc = fe.main()
    ok("C2 cli_hook_failed CLI → exit 0 (CONTINUE)", rc == 0, f"got={rc}")
except Exception as e:
    ok("C2 cli_hook_failed CLI (no crash)", False, f"exception={e}")

sys.argv = ["fallback_engine.py", "unknown_failure"]
try:
    rc = fe.main()
    ok("C3 unknown_failure CLI → exit 1 (BLOCKED)", rc == 1, f"got={rc}")
except Exception as e:
    ok("C3 unknown_failure CLI (no crash)", False, f"exception={e}")

sys.argv = old_argv

print()
print("=" * 64)
print(f"结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
if FAIL:
    print("❌ FALLBACK-ENGINE 存在失败项")
    sys.exit(1)
print("✅ ALL PASS — fallback engine 15 failure types × risk × IO 全成立")
