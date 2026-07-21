#!/usr/bin/env python3
"""finalize_page.py — C8a 定稿门禁（FINAL.md v3.1 §4.2/§4.4/§6）
退出：0=定稿完成 2=ERROR 3=FAILED_INVARIANT
"""
from __future__ import annotations
import json, sys, yaml
from pathlib import Path
from lib.common_lib import *

def main() -> int:
    regenerate = "--regenerate" in sys.argv
    args_list = [a for a in sys.argv[1:] if a != "--regenerate"]
    gates_parse_args(args_list)
    assert TARGET_REPO is not None, "需要 --target-repo"
    gates_preamble()
    started_at = gates_now()

    results_dir = gates_results_dir()
    summary_dir = NIGHT_DIR / "verification-summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_out = summary_dir / f"{PAGE_ID}.yaml"
    agg_file = NIGHT_DIR / "ac-aggregates" / f"{PAGE_ID}.yaml"
    token_file = NIGHT_DIR / "tokens" / f"{PAGE_ID}.token.json"

    if summary_out.is_file() and not regenerate:
        print(f"ERROR: verification-summary 已存在（immutable）: {summary_out}", file=sys.stderr)
        return 2

    try:
        latest = __import__("gate_result", fromlist=["reduce_latest"]).reduce_latest(str(results_dir))
    except Exception as e:
        print(f"FAILED_INVARIANT: gate-results 不可信: {e}", file=sys.stderr)
        return 3

    expected_producer = {
        "C0": "preflight.py", "C1": "scope_check.py", "C2": "run_gate.py",
        "C3": "c7_check.py", "C4": "run_gate.py", "C5": "run_gate.py",
        "C6": "run_gate.py", "C7": "evidence_check.py", "C8a": "finalize_page.py",
    }
    for g, e in latest.items():
        exp = expected_producer.get(g)
        if exp and e.get("producer") != exp:
            print(f"FAILED_INVARIANT: {g} 信封 producer={e.get('producer')!r}（期望 {exp}）", file=sys.stderr)
            return 3
        if e.get("control_plane_digest") != GATES_CP_DIGEST:
            print(f"FAILED_INVARIANT: {g} 信封控制面 digest 与当前不符", file=sys.stderr)
            return 3

    required_gates = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    gates_map = {g: (latest[g]["status"] if g in latest else None) for g in required_gates}
    missing = [g for g, s in gates_map.items() if s is None]
    failed = [g for g, s in gates_map.items() if s not in ("PASS", None)]

    qualified = False
    assumptions_present = False
    agg = {}
    if agg_file.is_file():
        agg = yaml.safe_load(agg_file.read_text(encoding="utf-8")) or {}
        qualified = bool(agg.get("qualified"))
    assump = results_dir.parent.parent / "assumptions.yaml"
    assumptions_present = assump.is_file() and assump.stat().st_size > 0

    contract_trust = "NONE"
    try:
        mdata = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
        page = next((p for p in mdata.get("pages") or [] if p.get("id") == PAGE_ID), {})
        acs = page.get("api_contract_status", "none")
        contract_trust = {"real": "TRUSTED", "inferred": "UNTRUSTED_CONTRACT"}.get(acs, "NONE")
    except Exception:
        contract_trust = "NONE"

    token_conflict = None
    if token_file.is_file():
        try:
            token = json.loads(token_file.read_text(encoding="utf-8"))
            claimed = (token.get("task") or {}).get("status", "")
            if claimed.lower() in ("done", "delivered") and (missing or failed):
                token_conflict = f"token 声称 {claimed} 但门禁缺失/失败: missing={missing} failed={failed}"
        except json.JSONDecodeError as e:
            token_conflict = f"token 损坏: {e}"
    if token_conflict:
        print(f"FAILED_INVARIANT: {token_conflict}", file=sys.stderr)
        return 3

    if missing:
        final_status, blocked_code = "BLOCKED", "BLOCKED_ENV"
        reason = f"门禁未齐: {missing}"
    elif failed:
        final_status, blocked_code = "FAILED", "FAILED_FIX_LOOP"
        reason = f"门禁失败: {failed}"
    elif not qualified:
        final_status, blocked_code = "BLOCKED", "BLOCKED_SCOPE"
        reason = "required_states 断言未全覆盖（qualified=false）"
    else:
        final_status, blocked_code = "DONE", None
        reason = "全门禁 PASS 且断言全覆盖"
    if final_status == "DONE" and contract_trust == "UNTRUSTED_CONTRACT":
        reason += "；含推断契约（UNTRUSTED_CONTRACT）"

    summary = {
        "schema": "verification-summary/v1",
        "page_id": PAGE_ID,
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
    evidence = [{"type": "verification_summary", "path": str(summary_out)}]
    gates_write_result("C8a", "PASS", 0, started_at, evidence=evidence)
    return 0

if __name__ == "__main__":
    sys.exit(main())
