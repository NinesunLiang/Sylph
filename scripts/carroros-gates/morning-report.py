#!/usr/bin/env python3
"""
morning-report.py — 晨报 + control-plane-scorecard (v6.0, .sh → .py 迁移)
只读 verification-summary + delivery-receipt + gate-results；遍历 manifest pages[]。
产出：$NIGHT_DIR/morning-report.md + $NIGHT_DIR/control-plane-scorecard.yaml
退出：0=报告生成 2=ERROR
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib import common

common.parse_args()
if not common.NIGHT_DIR:
    print("ERROR: 需要 --night-dir", file=sys.stderr)
    sys.exit(2)

common.preamble()

gr_path = str(SCRIPT_DIR / "lib" / "gate_result.py")
spec = importlib.util.spec_from_file_location("gate_result", gr_path)
gr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gr)

EXPECTED_PRODUCER = {
    "C0": "preflight.py", "C1": "scope-check.py", "C2": "run-gate.py",
    "C3": "c7-check.py", "C4": "run-gate.py", "C5": "run-gate.py",
    "C6": "run-gate.py", "C7": "evidence-check.py", "C8a": "finalize-page.py",
}
WRAPPED_TOOL_PAT = {
    "C2": re.compile(r"tsc|eslint|build"),
    "C4": re.compile(r"playwright"),
    "C5": re.compile(r"playwright"),
    "C6": re.compile(r"visual|playwright|screenshot"),
}


def load_yaml(p):
    p = Path(p)
    if p.is_file():
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            return {"_corrupt": True}
    return None


manifest = yaml.safe_load(Path(common.MANIFEST).read_text(encoding="utf-8"))
pages = manifest.get("pages") or []
nd = Path(common.NIGHT_DIR)

rows = []
done_without_evidence = 0
forged_summary = 0
visual_fail_marked_done = 0
missing_pages = 0
scope_leaks = 0
superseded_c6 = 0
producer_mismatch = 0
suspicious_wrapped = 0
untrusted_pages = 0

for pg in pages:
    pid = pg.get("id")
    summary = load_yaml(nd / "verification-summaries" / f"{pid}.yaml")
    receipt = load_yaml(nd / "delivery-receipts" / f"{pid}.yaml")
    results_dir = nd / "gate-results" / pid
    token = None
    tp = nd / "tokens" / f"{pid}.token.json"
    if tp.is_file():
        try:
            token = json.loads(tp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            token = {"_corrupt": True}

    latest = {}
    superseded_ids = set()
    if results_dir.is_dir():
        try:
            for p in results_dir.glob("*.superseded.json"):
                superseded_ids.add(p.name[:-len(".superseded.json")])
            latest = gr.reduce_latest(results_dir)
        except gr.FailClosed as e:
            rows.append((pid, "FAILED_INVARIANT", f"gate-results 不可信: {e}", "", ""))
            missing_pages += 1
            continue
        superseded_c6 += sum(1 for p in results_dir.glob("C6-*.json")
                             if p.stem.replace("C6-", "") in superseded_ids)
        for g, e in latest.items():
            exp = EXPECTED_PRODUCER.get(g)
            if exp and e.get("producer") != exp:
                producer_mismatch += 1
            if g in WRAPPED_TOOL_PAT and e.get("producer") == "run-gate.py":
                argv = ""
                for item in e.get("evidence") or []:
                    if isinstance(item, dict) and item.get("type") == "wrapped_argv":
                        argv = item.get("argv", "")
                if not argv or not WRAPPED_TOOL_PAT[g].search(argv):
                    suspicious_wrapped += 1

    if summary is None:
        if token is None:
            status, note = "NOT_STARTED", "无 token 无结论"
            missing_pages += 1
        else:
            claimed = (token.get("task") or {}).get("status", "?") if isinstance(token, dict) else "?"
            status, note = "CRASHED", f"token status={claimed} 但无 verification-summary"
        rows.append((pid, status, note, "", ""))
        continue

    if summary.get("_corrupt"):
        rows.append((pid, "FAILED_INVARIANT", "verification-summary 损坏", "", ""))
        forged_summary += 1
        continue

    final = summary.get("final_status", "?")
    gates_v = summary.get("gates") or {}

    if final == "DONE" and latest.get("C7", {}).get("status") != "PASS":
        done_without_evidence += 1
    if final == "DONE" and "C8a" not in latest:
        forged_summary += 1
    if final == "DONE" and latest.get("C6", {}).get("status") == "ERROR":
        visual_fail_marked_done += 1
    scope_leaks += sum(1 for g, e in latest.items() if g == "C1" and e.get("status") == "FAIL")
    if summary.get("contract_trust") == "UNTRUSTED_CONTRACT":
        untrusted_pages += 1

    delivery = (receipt or {}).get("delivery_status", "NOT_ATTEMPTED")
    pr_url = (receipt or {}).get("draft_pr_url", "") or ""
    note_val = summary.get("reason", "")
    if summary.get("contract_trust") == "UNTRUSTED_CONTRACT":
        note_val = f"⚠ 推断契约未对账 | {note_val}"
    rows.append((pid, final, note_val, delivery, pr_url))

smoke = load_yaml(nd / "smoke-results.yaml") or {}
smoke_ind = load_yaml(nd / "smoke-results-independent.yaml") or {}
gates_can_fail = bool(smoke.get("all_green")) and bool(smoke.get("tamper_suite_passed"))
smoke_attestation = smoke_ind.get("runner", smoke.get("runner", "self"))
smoke_independent_in_bag = bool(smoke_ind) and smoke_ind.get("runner") == "independent"

events_file = nd / "execution-events.jsonl"
poison_events = 0
crash_ok, crash_total = 0, 0
if events_file.is_file():
    for line in events_file.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("event")
        if t == "WORKSPACE_POISONED":
            poison_events += 1
        elif t == "crash_recovery":
            crash_total += 1
            if ev.get("ok"):
                crash_ok += 1

o1 = load_yaml(nd / "metrics" / "o1-duplication.yaml") or {}
o2_cov = "0%"
o2_files = list((nd / "metrics").glob("*.o2.json")) if (nd / "metrics").is_dir() else []
if o2_files:
    try:
        o2 = json.loads(o2_files[0].read_text(encoding="utf-8"))
        o2_cov = f"{o2.get('token_reference_coverage', 0)}%"
    except Exception:
        pass

scorecard = {
    "gates_can_fail_on_purpose": gates_can_fail,
    "smoke_attestation": smoke_attestation,
    "smoke_independent_in_bag": smoke_independent_in_bag,
    "morning_report_missing_pages": missing_pages,
    "done_without_evidence_count": done_without_evidence,
    "scope_leak_count": scope_leaks,
    "same_fingerprint_loop_count": superseded_c6,
    "crash_recoveries_succeeded": f"{crash_ok}/{crash_total}",
    "workspace_poison_events": poison_events,
    "forged_summary_attempts": forged_summary,
    "visual_tool_failure_marked_done": visual_fail_marked_done,
    "producer_mismatch_count": producer_mismatch,
    "suspicious_gate_invocation_count": suspicious_wrapped,
    "untrusted_contract_pages": untrusted_pages,
    "intra_page_duplication_flags": o1.get("duplicate_windows", 0),
    "token_reference_coverage": o2_cov,
    "yaml_duplicate_key_policy": "last_wins_known",
    "red_team_night_loop": "due=after_first_trial",
}
green = (gates_can_fail and smoke_attestation == "independent"
         and missing_pages == 0 and done_without_evidence == 0
         and forged_summary == 0 and visual_fail_marked_done == 0 and poison_events == 0
         and producer_mismatch == 0 and suspicious_wrapped == 0)
scorecard["control_plane_green"] = green

(nd / "control-plane-scorecard.yaml").write_text(
    yaml.safe_dump(scorecard, allow_unicode=True, sort_keys=False), encoding="utf-8")

lines = ["# 晨报", "", f"夜目录: {common.NIGHT_DIR}", "",
         "## 页面清单（manifest pages[] 全遍历）", "",
         "| page | final_status | 说明 | delivery | PR |", "|---|---|---|---|---|"]
for pid, final, reason, delivery, pr in rows:
    lines.append(f"| {pid} | {final} | {reason} | {delivery} | {pr} |")
lines += ["", "## control-plane-scorecard", "",
          "```yaml", yaml.safe_dump(scorecard, allow_unicode=True, sort_keys=False).strip(), "```",
          "", f"**control_plane_green = {green}**",
          "" if green else "\n> scorecard 不绿：先看控制面，不许看页面还原度。"]
(nd / "morning-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
