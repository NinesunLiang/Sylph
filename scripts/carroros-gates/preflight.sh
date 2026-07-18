#!/usr/bin/env bash
# preflight.sh — 起飞前总门禁（FINAL.md v3.1 §6/§14/§18）= C0
# lx-goal on 之前必须全绿。任何一项不过 → NO-GO（fail-closed）。
# 检查：signoff 字节哈希 / control_plane_lock 自验 / first_night_selection 机判 /
#   assertion 词表封闭 / 模型路由真身 / 预算非空 / S1 签署 / 环境指纹 /
#   五类 smoke 实跑绿 + 独立复跑 attest 入袋（9b, Opus P1-10）/ gh auth（仅警告）。
# 产出：C0 信封 + $NIGHT_DIR/smoke-results.yaml + 夜会话标记 .omc/state/night-session.active
# 退出：0=GO 1=NO-GO 2=ERROR 3=FAILED_INVARIANT

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
gates_parse_args "$@"
[[ -n "$NIGHT_DIR" ]] || { echo "ERROR: 需要 --night-dir" >&2; exit 2; }
[[ -n "$TARGET_REPO" ]] || { echo "ERROR: 需要 --target-repo" >&2; exit 2; }

FAILS=()
note() { echo "  ✗ $1"; FAILS+=("$1"); }
ok()   { echo "  ✓ $1"; }

echo "== preflight =="

# 1. signoff 字节哈希（S2 detached）
SIGNOFF="${MANIFEST%.yaml}.signoff.yaml"
if [[ ! -f "$SIGNOFF" ]]; then
  note "signoff 缺失: $SIGNOFF"
else
  RECORDED="$(python3 "$CARROS_BASE" manifest-json --manifest "$SIGNOFF" --get manifest_sha256 2>/dev/null || true)"
  DECISION="$(python3 "$CARROS_BASE" manifest-json --manifest "$SIGNOFF" --get decision 2>/dev/null || true)"
  ACTUAL="$(gates_sha256_file "$MANIFEST")"
  if [[ -z "$RECORDED" || "$RECORDED" != "$ACTUAL" ]]; then
    note "signoff 哈希不匹配（manifest 签后被改动？） recorded=${RECORDED:0:12} actual=${ACTUAL:0:12}"
  elif [[ "$DECISION" != "GO" && "$DECISION" != "CONDITIONAL_GO" ]]; then
    note "signoff decision=${DECISION}（需要 GO|CONDITIONAL_GO）"
  else
    ok "signoff 字节哈希匹配，decision=$DECISION"
  fi
fi

# 2. control_plane_lock 自验（S1/GPT#3）
if gates_verify_control_plane_lock >/dev/null; then
  ok "control_plane_lock 自验通过"
else
  note "control_plane_lock 自验失败（控制面被改动）"
fi

# 3. first_night_selection 机判（O5）
PAGES_COUNT="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --pages | grep -c . || true)"
[[ "$PAGES_COUNT" == "1" ]] && ok "pages==1" || note "pages=${PAGES_COUNT}（首夜硬规则 ==1）"
for f in input_completeness complexity prototype_accessible acceptance_contract_complete happy_path_testable; do
  v="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --get "first_night_selection.$f" 2>/dev/null || echo MISSING)"
  case "$f" in
    input_completeness) [[ "$v" == "complete" ]] && ok "selection.$f=$v" || note "selection.${f}=${v}（需 complete）";;
    complexity) [[ "$v" == "V0_or_V1" ]] && ok "selection.$f=$v" || note "selection.${f}=${v}（需 V0_or_V1）";;
    *) [[ "$v" == "true" ]] && ok "selection.$f=$v" || note "selection.${f}=${v}（需 true）";;
  esac
done

# 4. assertion 词表封闭（O3/GPT#2）：manifest 引用的 ID 全部在 catalog 内
CATALOG="$GATES_DIR/assertion-catalog.yaml"
CAT_VER="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --get assertion_catalog_version 2>/dev/null || echo MISSING)"
FILE_VER="$(grep -m1 '^version:' "$CATALOG" | awk '{print $2}' | tr -d '\"')"
[[ "$CAT_VER" == "$FILE_VER" ]] && ok "catalog version=$CAT_VER" || note "catalog 版本不符 manifest=$CAT_VER file=$FILE_VER"
python3 - "$MANIFEST" "$CATALOG" << 'PY' || note "assertion 词表校验失败（见上）"
import sys, yaml
manifest = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
catalog = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
known = set((catalog.get("state_assertions") or {})) | set((catalog.get("overlay_assertions") or {}))
unknown = []
for pg in manifest.get("pages") or []:
    for state, spec in (pg.get("required_states") or {}).items():
        if isinstance(spec, dict):
            for k in ("assert", "not", "and"):
                aid = spec.get(k)
                if aid and aid not in known:
                    unknown.append(f"{pg.get('id')}.{state}.{k}={aid}")
    for ov in (pg.get("overlay_contract") or {}).get("items") or []:
        for aid in ov.get("asserts") or []:
            if aid not in known:
                unknown.append(f"{pg.get('id')}.overlay.{ov.get('selector','?')}={aid}")
if unknown:
    print("  未知 assertion ID:", file=sys.stderr)
    for u in unknown: print(f"    {u}", file=sys.stderr)
    sys.exit(1)
print("  ✓ assertion 词表封闭")
PY

# 4b. catalog 每条 id 有可执行绑定（Grok §17a P1-4）：helper 文件逐个 grep，未知/未绑定 → NO-GO
HELPERS="$TARGET_REPO/tests/e2e/helpers/assertions.ts"
if [[ ! -f "$HELPERS" ]]; then
  note "断言 helper 缺失: ${HELPERS}（Phase 0 A1 未做：17 个 helper 以 catalog id 为键导出）"
else
  UNBOUND=0
  while IFS= read -r aid; do
    [[ -n "$aid" ]] || continue
    if ! grep -q "$aid" "$HELPERS"; then
      note "catalog id 无 helper 绑定: $aid"
      UNBOUND=1
    fi
  done < <(python3 - "$CATALOG" << 'PY'
import sys, yaml
cat = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
for sec in ("state_assertions", "overlay_assertions"):
    for aid in (cat.get(sec) or {}):
        print(aid)
PY
)
  [[ $UNBOUND -eq 0 ]] && ok "catalog 全部 id 均有 helper 绑定"
fi

# 5. 模型路由真身（§2 铁律：误连高阶模型 = No-Go）
BASE_URL="${ANTHROPIC_BASE_URL:-}"
if [[ "$BASE_URL" != "http://127.0.0.1:9998" ]]; then
  note "ANTHROPIC_BASE_URL=${BASE_URL}（需 http://127.0.0.1:9998 本地代理）"
else
  if curl -s -m 3 "$BASE_URL/" -o /dev/null; then
    ok "模型代理在线（${BASE_URL}）"
  else
    note "模型代理离线（$BASE_URL 不可达）"
  fi
fi
ROUTING_PROOF="$NIGHT_DIR/model-routing-proof.yaml"
if [[ -f "$ROUTING_PROOF" ]]; then
  ok "model-routing-proof 存在（Phase 0 探针证据）"
else
  note "model-routing-proof 缺失（Phase 0 需跑 probe-model-routing）"
fi

# 6. 预算非空（O4：dry-cost 实测填入，禁止拍脑袋）
for f in per_page_calls fix_rounds page_wall_clock_min; do
  v="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --get "budgets.$f" 2>/dev/null || echo MISSING)"
  [[ "$v" != "null" && "$v" != "MISSING" && -n "$v" ]] && ok "budgets.$f=$v" || note "budgets.$f 为空（需 dry-cost 实测 P90×安全系数）"
done

# 7. S1 残余风险签署（§18#9）
SIGNER="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --get trust_boundary.residual_risk_accepted_by 2>/dev/null || echo "")"
[[ -n "$SIGNER" && "$SIGNER" != "null" ]] && ok "trust_boundary 签署人: $SIGNER" || note "trust_boundary.residual_risk_accepted_by 未签署（§18#9，未签署=NO-GO）"
RENEW="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --get trust_boundary.auto_renew 2>/dev/null || echo "")"
[[ "$RENEW" == "false" ]] && ok "auto_renew=false" || note "auto_renew 必须为 false"
SCOPE="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --get trust_boundary.scope 2>/dev/null || echo "")"
[[ "$SCOPE" == "single_page_single_night" ]] && ok "trust_boundary.scope=$SCOPE" || note "trust_boundary.scope 须为 single_page_single_night（Grok §17a P1-8）"

# 8. 环境指纹（S4）
for f in node_version pnpm_version lockfile_sha256; do
  v="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --get "environment_fingerprint.$f" 2>/dev/null || echo "")"
  [[ -n "$v" && "$v" != "null" ]] && ok "fingerprint.$f 已记录" || note "fingerprint.$f 为空"
done

# 9. 五类 smoke 实跑（R4：门禁必须证明自己会失败）
SMOKE_OUT="$NIGHT_DIR/smoke-results.yaml"
if bash "$GATES_DIR/smoke/run-all.sh" --manifest "$MANIFEST" --night-dir "$NIGHT_DIR" --target-repo "$TARGET_REPO" --out "$SMOKE_OUT"; then
  ok "五类 smoke 全绿"
else
  note "smoke 未全绿（见 ${SMOKE_OUT}）"
fi

# 9b. 独立复跑 attest 入袋（Opus §17a P1-10）：self 自陈不得作为首夜放行证据。
# Phase 0 A4 必须已把 SMOKE_RUNNER=independent 的全绿结果落 $NIGHT_DIR/smoke-results-independent.yaml；
# 其 control_plane_digest 必须等于当前 digest（防"控制面改动后拿三天前的独立绿冒充"）。
SMOKE_IND="$NIGHT_DIR/smoke-results-independent.yaml"
if [[ ! -f "$SMOKE_IND" ]]; then
  note "smoke 独立复跑证据缺失: ${SMOKE_IND}（Phase 0 A4：SMOKE_RUNNER=independent 复跑后 --out 落此路径）"
else
  IND_RUNNER="$(python3 "$CARROS_BASE" manifest-json --manifest "$SMOKE_IND" --get runner 2>/dev/null || echo MISSING)"
  IND_GREEN="$(python3 "$CARROS_BASE" manifest-json --manifest "$SMOKE_IND" --get all_green 2>/dev/null || echo MISSING)"
  IND_TAMPER="$(python3 "$CARROS_BASE" manifest-json --manifest "$SMOKE_IND" --get tamper_suite_passed 2>/dev/null || echo MISSING)"
  IND_DIGEST="$(python3 "$CARROS_BASE" manifest-json --manifest "$SMOKE_IND" --get control_plane_digest 2>/dev/null || echo MISSING)"
  CUR_DIGEST="$(gates_verify_control_plane_lock 2>/dev/null || echo "")"
  if [[ "$IND_RUNNER" != "independent" ]]; then
    note "smoke 独立复跑 runner=${IND_RUNNER}（需 independent；self 自陈不算证据）"
  elif [[ "$IND_GREEN" != "true" || "$IND_TAMPER" != "true" ]]; then
    note "smoke 独立复跑未全绿（all_green=${IND_GREEN} tamper=${IND_TAMPER}）"
  elif [[ -z "$CUR_DIGEST" || "$IND_DIGEST" != "$CUR_DIGEST" ]]; then
    note "smoke 独立复跑 digest 过期或不符（独立跑后控制面又改动？需重跑 A4）"
  else
    ok "smoke 独立复跑 attest 在袋（runner=independent，digest 与当前一致）"
  fi
fi

# 10. gh auth（仅警告：不通则 delivery=NOT_ATTEMPTED，不影响 DONE）
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  ok "gh 已认证（DONE 可建 Draft PR）"
else
  echo "  ! gh 未认证——DONE 页 delivery_status=NOT_ATTEMPTED（不影响 DONE 判定）"
fi

echo
if [[ ${#FAILS[@]} -gt 0 ]]; then
  echo "preflight NO-GO（${#FAILS[@]} 项）:" >&2
  printf '  - %s\n' "${FAILS[@]}" >&2
  exit 1
fi

# GO：写 C0 信封 + 夜会话标记
gates_preamble
STARTED_AT="$(gates_now)"
PAGE_ID="$(python3 "$CARROS_BASE" manifest-json --manifest "$MANIFEST" --pages | head -1)"
gates_write_result C0 PASS 0 "$STARTED_AT" >/dev/null
mkdir -p "$CARROS_ROOT/.omc/state"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$CARROS_ROOT/.omc/state/night-session.active"
echo "preflight GO — 夜会话标记已创建，可以 lx-goal on"
