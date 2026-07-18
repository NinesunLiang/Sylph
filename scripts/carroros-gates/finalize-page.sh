#!/usr/bin/env bash
# finalize-page.sh — C8a 定稿门禁（FINAL.md v3.1 §4.2/§4.4/§6）
# 从 gate-results 重算 final_status（唯一合法结论来源；模型手写 summary = 篡改）。
# DONE 条件：C1..C7 最新合法结果全 PASS 且 completion.qualified=true。
# token.json 与 gate-results 冲突 → FAILED_INVARIANT（exit 3）。
# 产出：verification-summary.yaml（immutable；已存在且非 --regenerate → ERROR）。
# 退出：0=定稿完成（final_status 见 summary） 2=ERROR 3=FAILED_INVARIANT

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

REGENERATE=0
EXTRA_ARGS=()
for a in "$@"; do
  if [[ "$a" == "--regenerate" ]]; then REGENERATE=1; else EXTRA_ARGS+=("$a"); fi
done
gates_parse_args "${EXTRA_ARGS[@]}"
[[ -n "$TARGET_REPO" ]] || { echo "ERROR: 需要 --target-repo" >&2; exit 2; }
gates_preamble
STARTED_AT="$(gates_now)"

RESULTS_DIR="$(gates_results_dir)"
SUMMARY_DIR="$NIGHT_DIR/verification-summaries"
mkdir -p "$SUMMARY_DIR"
SUMMARY_OUT="$SUMMARY_DIR/$PAGE_ID.yaml"
AGG_FILE="$NIGHT_DIR/ac-aggregates/$PAGE_ID.yaml"
TOKEN_FILE="$NIGHT_DIR/tokens/$PAGE_ID.token.json"

if [[ -f "$SUMMARY_OUT" && $REGENERATE -eq 0 ]]; then
  echo "ERROR: verification-summary 已存在（immutable）: ${SUMMARY_OUT}；确需重算用 --regenerate（旧 gate-results 须已标 SUPERSEDED）" >&2
  exit 2
fi

python3 - "$RESULTS_DIR" "$AGG_FILE" "$SUMMARY_OUT" "$TOKEN_FILE" "$GATES_LIB/gate_result.py" "$GATES_CP_DIGEST" "$MANIFEST" "$PAGE_ID" << 'PY'
import importlib.util, json, sys
from pathlib import Path

import yaml

results_dir, agg_file, summary_out, token_file, gr_path, cp_digest, manifest_path, page_id = sys.argv[1:9]
spec = importlib.util.spec_from_file_location("gate_result", gr_path)
gr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gr)

try:
    latest = gr.reduce_latest(results_dir)
except gr.FailClosed as e:
    print(f"FAILED_INVARIANT: gate-results 不可信: {e}", file=sys.stderr)
    sys.exit(3)

# Grok §17a P0-3：信封必须来自合法门禁链——producer 按 gate_id 映射校验，
# 且信封签署时的控制面 digest 必须与当前一致（控制面夜里被改/信封伪造都会在此爆炸）。
EXPECTED_PRODUCER = {
    "C0": "preflight.sh", "C1": "scope-check.sh", "C2": "run-gate.sh",
    "C3": "c7-check.sh", "C4": "run-gate.sh", "C5": "run-gate.sh",
    "C6": "run-gate.sh", "C7": "evidence-check.sh", "C8a": "finalize-page.sh",
}
for g, e in latest.items():
    exp = EXPECTED_PRODUCER.get(g)
    if exp and e.get("producer") != exp:
        print(f"FAILED_INVARIANT: {g} 信封 producer={e.get('producer')!r}（期望 {exp}）——非合法门禁链产物", file=sys.stderr)
        sys.exit(3)
    if e.get("control_plane_digest") != cp_digest:
        print(f"FAILED_INVARIANT: {g} 信封控制面 digest 与当前不符——控制面夜里被改动或信封系伪造", file=sys.stderr)
        sys.exit(3)

REQUIRED_GATES = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
gates_map = {g: (latest[g]["status"] if g in latest else None) for g in REQUIRED_GATES}
missing = [g for g, s in gates_map.items() if s is None]
failed = [g for g, s in gates_map.items() if s not in ("PASS", None)]

# completion.qualified 来自 C7 的 ac 聚合
qualified = False
assumptions_present = False
agg = {}
if Path(agg_file).is_file():
    agg = yaml.safe_load(Path(agg_file).read_text(encoding="utf-8")) or {}
    qualified = bool(agg.get("qualified"))
assump = Path(results_dir).parent.parent / "assumptions.yaml"
assumptions_present = assump.is_file() and assump.stat().st_size > 0

# Grok §17a P1-6：inferred 契约贴标——DONE 可以给，但晨报红旗 + PR 强制清单，不许"当生产 DONE"
contract_trust = "NONE"
try:
    mdata = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8")) or {}
    page = next((p for p in mdata.get("pages") or [] if p.get("id") == page_id), {})
    acs = page.get("api_contract_status", "none")
    contract_trust = {"real": "TRUSTED", "inferred": "UNTRUSTED_CONTRACT"}.get(acs, "NONE")
except Exception:
    contract_trust = "NONE"

# token 交叉校验（R4 攻击集：手写 token 称 DELIVERED 但缺 C6）
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
    "page_id": Path(summary_out).stem,
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
Path(summary_out).write_text(yaml.safe_dump(summary, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(f"C8a: final_status={final_status} ({reason})")
print(f"summary: {summary_out}")
# 终态不是 DONE 也算定稿成功——定稿是"据实记录"，不是"必须成功"
sys.exit(0)
PY
RC=$?

case $RC in
  0) gates_write_result C8a PASS 0 "$STARTED_AT" "[{\"type\":\"verification_summary\",\"path\":\"$SUMMARY_OUT\"}]" >/dev/null; exit 0;;
  3) exit 3;;  # 权威链被碰时不写信封——现场保持原样供晨审
  *) exit 2;;
esac
