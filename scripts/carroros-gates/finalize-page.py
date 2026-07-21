#!/usr/bin/env python3
"""
finalize-page.py — C8a 定稿门禁 (v6.0, .sh → .py 迁移)
从 gate-results 重算 final_status（唯一合法结论来源）。
DONE 条件：C1..C7 最新合法结果全 PASS 且 completion.qualified=true。
退出：0=定稿完成 2=ERROR 3=FAILED_INVARIANT
"""

import importlib.util
import json
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib import common

REGENERATE = "--regenerate" in sys.argv
extra_args = [a for a in sys.argv[1:] if a != "--regenerate"]
common.parse_args(extra_args)
if not common.TARGET_REPO:
    print("ERROR: 需要 --target-repo", file=sys.stderr)
    sys.exit(2)
common.preamble()
started_at = common.now_iso()

results_dir_val = common.results_dir()
summary_dir = Path(common.NIGHT_DIR) / "verification-summaries"
summary_dir.mkdir(parents=True, exist_ok=True)
summary_out = summary_dir / f"{common.PAGE_ID}.yaml"
agg_file = Path(common.NIGHT_DIR) / "ac-aggregates" / f"{common.PAGE_ID}.yaml"
token_file = Path(common.NIGHT_DIR) / "tokens" / f"{common.PAGE_ID}.token.json"

if summary_out.exists() and not REGENERATE:
    print(f"ERROR: verification-summary 已存在（immutable）: {summary_out}；确需重算用 --regenerate", file=sys.stderr)
    sys.exit(2)

# 动态加载 gate_result.py
gr_path = str(SCRIPT_DIR / "lib" / "gate_result.py")
spec = importlib.util.spec_from_file_location("gate_result", gr_path)
gr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gr)

try:
    latest = gr.reduce_latest(results_dir_val)
except gr.FailClosed as e:
    print(f"FAILED_INVARIANT: gate-results 不可信: {e}", file=sys.stderr)
    sys.exit(3)

EXPECTED_PRODUCER = {
    "C0": "preflight.py", "C1": "scope-check.py", "C2": "run-gate.py",
    "C3": "c7-check.py", "C4": "run-gate.py", "C5": "run-gate.py",
    "C6": "run-gate.py", "C7": "evidence-check.py", "C8a": "finalize-page.py",
}

for g, e in latest.items():
    exp = EXPECTED_PRODUCER.get(g)
    if exp and e.get("producer") != exp:
        print(f"FAILED_INVARIANT: {g} 信封 producer={e.get('producer')!r}（期望 {exp}）——非合法门禁链产物", file=sys.stderr)
        sys.exit(3)
    if e.get("control_plane_digest") != common.GATES_CP_DIGEST:
        print(f"FAILED_INVARIANT: {g} 信封控制面 digest 与当前不符", file=sys.stderr)
        sys.exit(3)

REQUIRED_GATES = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
gates_map = {g: (latest[g]["status"] if g in latest else None) for g in REQUIRED_GATES}
missing = [g for g, s in gates_map.items() if s is None]
failed = [g for g, s in gates_map.items() if s not in ("PASS", None)]

qualified = False
assumptions_present = False
agg = {}
if Path(agg_file).is_file():
    agg = yaml.safe_load(Path(agg_file).read_text(encoding="utf-8")) or {}
    qualified = bool(agg.get("qualified"))

assump = Path(results_dir_val).parent.parent / "assumptions.yaml"
assumptions_present = assump.is_file() and assump.stat().st_size > 0

# inferred 契约贴标
contract_trust = "NONE"
try:
    mdata = yaml.safe_load(Path(common.MANIFEST).read_text(encoding="utf-8")) or {}
    page = next((p for p in mdata.get("pages") or [] if p.get("id") == common.PAGE_ID), {})
    acs = page.get("api_contract_status", "none")
    contract_trust = {"real": "TRUSTED", "inferred": "UNTRUSTED_CONTRACT"}.get(acs, "NONE")
except Exception:
    contract_trust = "NONE"

# token 交叉校验
token_conflict = None
if Path(token_file).is_file():
    try:
        token = json.loads(Path(token_file).read_text(encoding="utf-8"))
        claimed = (token.get("task") or {}).get("status", "")
        if claimed in ("done", "delivered", "DONE", "DELIVERED") and (missing or failed):
            token_conflict = f"token 声称 {claimed} 但门禁缺失/失败: missing={missing} failed={failed}"
    except json.JSONDecodeError as e:
        token_conflict = f"token 损坏: {e}"

if token_conflict:
    print(f"FAILED_INVARIANT: {token_conflict}", file=sys.stderr)
    sys.exit(3)

if missing:
    final_status, blocked_code = "BLOCKED", "BLOCKED_ENV"
    reason = f"门禁未齐: {missing}"
elif failed:
    final_status, blocked_code = "FAILED", "FAILED_FIX_LOOP"
    reason = f"门禁失败: {failed}"
elif not qualified:
    final_status, blocked_code = "BLOCKED", "BLOCKED_SCOPE"
    reason = "required_states 断言未全覆盖（qualified=false → 强制 BLOCKED）"
else:
    final_status, blocked_code = "DONE", None
    reason = "全门禁 PASS 且断言全覆盖"

if final_status == "DONE" and contract_trust == "UNTRUSTED_CONTRACT":
    reason += "；含推断契约（UNTRUSTED_CONTRACT，API 文档到后须对账）"

summary = {
    "schema": "verification-summary/v1",
    "page_id": summary_out.stem,
    "final_status": final_status,
    "blocked_code": blocked_code,
    "failed_code": None if final_status != "FAILED" else "FAILED_FIX_LOOP",
    "completion": {"qualified": qualified, "assumptions_present": assumptions_present},
    "contract_trust": contract_trust,
    "gates": gates_map,
    "code_sha": agg.get("code_sha"),
    "ac_total": agg.get("ac_total"),
    "ac_covered": agg.get("ac_covered"),
    "reason": reason,
    "immutable": True,
}
summary_out.write_text(yaml.safe_dump(summary, allow_unicode=True, sort_keys=False), encoding="utf-8")

print(f"C8a: final_status={final_status} ({reason})")
print(f"summary: {summary_out}")

# 定稿成功（不管终态是否为 DONE）
summary_evidence = json.dumps([{"type": "verification_summary", "path": str(summary_out)}], ensure_ascii=False)
common.write_result("C8a", "PASS", 0, started_at, summary_evidence)
