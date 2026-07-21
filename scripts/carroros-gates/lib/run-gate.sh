#!/usr/bin/env bash
# run-gate.sh — 通用门禁执行器：跑任意命令，按退出码写 gate-result 信封。
# 用于 C2（typecheck/lint/build）、C4/C5（playwright）、C6（视觉确定性子集）
# 这类"外部工具即门禁"的场景，保证全部门禁走同一信封协议（FINAL §4.4）。
#
# 用法:
#   run-gate.sh --gate-id C2 --manifest M --night-dir D --page-id P \
#               [--target-repo R] [--evidence JSON] -- cmd [args...]
# 退出码: 0=PASS；被包装命令非 0 → 1=FAIL；命令无法启动 → 2=ERROR。
# 信封 status 与退出码一致（gate_result.py 强制校验）。

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 以第一个裸 `--` 为界：前段为 run-gate 参数，后段为被包装命令
OUR_ARGS=()
CMD=()
seen_sep=0
for a in "$@"; do
  if [[ $seen_sep -eq 0 && "$a" == "--" ]]; then
    seen_sep=1
    continue
  fi
  if [[ $seen_sep -eq 0 ]]; then
    OUR_ARGS+=("$a")
  else
    CMD+=("$a")
  fi
done
[[ $seen_sep -eq 1 && ${#CMD[@]} -gt 0 ]] || {
  echo "ERROR: 用法: run-gate.sh --gate-id X --manifest M --night-dir D --page-id P [--target-repo R] [--evidence J] -- cmd" >&2
  exit 2
}

GATE_ID=""
EVIDENCE="[]"
PASS_ARGS=()
i=0
while [[ $i -lt ${#OUR_ARGS[@]} ]]; do
  case "${OUR_ARGS[$i]}" in
    --gate-id) GATE_ID="${OUR_ARGS[$((i+1))]}"; i=$((i+2));;
    --evidence) EVIDENCE="${OUR_ARGS[$((i+1))]}"; i=$((i+2));;
    *) PASS_ARGS+=("${OUR_ARGS[$i]}"); i=$((i+1));;
  esac
done
[[ -n "$GATE_ID" ]] || { echo "ERROR: 需要 --gate-id" >&2; exit 2; }

source "$SCRIPT_DIR/common.sh"
gates_parse_args "${PASS_ARGS[@]}"
gates_preamble

STARTED_AT="$(gates_now)"
set +e
"${CMD[@]}"
CMD_EXIT=$?
set -e

case $CMD_EXIT in
  0) STATUS="PASS"; FINAL_EXIT=0;;
  126|127) STATUS="ERROR"; FINAL_EXIT=2;;   # 无法执行/命令不存在
  *) STATUS="FAIL"; FINAL_EXIT=1;;
esac

# Grok §17a P0-3：被包装命令留痕（argv + digest），晨报据此识别"包空命令骗 PASS"
WRAPPED_STR="${CMD[*]}"
ARGV_DIGEST="$(gates_sha256_string "$WRAPPED_STR")"
EVIDENCE_FINAL="$(python3 -c "import json,sys; e=json.loads(sys.argv[1]); e.append({'type':'wrapped_argv','argv':sys.argv[2],'argv_digest':sys.argv[3]}); print(json.dumps(e, ensure_ascii=False))" "$EVIDENCE" "$WRAPPED_STR" "$ARGV_DIGEST")"

gates_write_result "$GATE_ID" "$STATUS" "$CMD_EXIT" "$STARTED_AT" "$EVIDENCE_FINAL" "$ARGV_DIGEST" >/dev/null
echo "run-gate $GATE_ID: $STATUS (exit $CMD_EXIT)"
exit $FINAL_EXIT
