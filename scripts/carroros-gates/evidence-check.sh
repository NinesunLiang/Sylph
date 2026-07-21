#!/usr/bin/env bash
# evidence-check.sh — C7 证据门禁（FINAL.md v3.1 §5/§6 + E6 + P0-2）
# 契约：playwright spec 运行在 artifacts 目录写 evidence-index.yaml：
#   code_sha: "..."
#   items: { <assert_id>: ["relative/path.png", ...] }
# 校验：每个 required assert_id 有证据；文件存在+非空；index 的 code_sha 与
#   当前 HEAD 受控路径无漂移（git diff --quiet code_sha..HEAD -- src/ tests/ ...）。
# 产出：$NIGHT_DIR/ac-aggregates/$PAGE_ID.yaml（ac_* 聚合，finalize/晨报消费）。
# 退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
gates_parse_args "$@"
[[ -n "$TARGET_REPO" ]] || { echo "ERROR: 需要 --target-repo" >&2; exit 2; }
gates_preamble
STARTED_AT="$(gates_now)"

ARTIFACTS_REL="$(gates_mget paths.artifacts "$PAGE_ID")" || exit 2
REQUIRED_JSON="$(gates_mget required_states "$PAGE_ID")" || exit 2
OVERLAY_JSON="$(gates_mget overlay_contract.items "$PAGE_ID")" || exit 2
# artifacts 路径里可能含 {date} 占位，用 night-dir 的日期替换
NIGHT_DATE="$(basename "$NIGHT_DIR")"
ARTIFACTS_DIR="$TARGET_REPO/${ARTIFACTS_REL//\{date\}/$NIGHT_DATE}"

mkdir -p "$NIGHT_DIR/ac-aggregates"
AGG_OUT="$NIGHT_DIR/ac-aggregates/$PAGE_ID.yaml"

python3 - "$TARGET_REPO" "$ARTIFACTS_DIR" "$REQUIRED_JSON" "$OVERLAY_JSON" "$AGG_OUT" << 'PY'
import json, subprocess, sys
from pathlib import Path

import yaml

target, artifacts, required_json, overlay_json, agg_out = sys.argv[1:6]
required = json.loads(required_json)
overlays = json.loads(overlay_json)

idx_path = Path(artifacts) / "evidence-index.yaml"
if not idx_path.is_file():
    print(f"C7 FAIL: evidence-index.yaml 缺失: {idx_path}", file=sys.stderr)
    sys.exit(1)
try:
    index = yaml.safe_load(idx_path.read_text(encoding="utf-8"))
except Exception as e:
    print(f"C7 FAIL: evidence-index.yaml 解析失败: {e}", file=sys.stderr)
    sys.exit(1)
if not isinstance(index, dict) or not isinstance(index.get("items"), dict):
    print("C7 FAIL: evidence-index.yaml 缺 items", file=sys.stderr)
    sys.exit(1)

code_sha = index.get("code_sha")
if not code_sha:
    print("C7 FAIL: evidence-index.yaml 缺 code_sha", file=sys.stderr)
    sys.exit(1)

# 新鲜度：code_sha..HEAD 受控路径零漂移（P0-2）
controlled = ["src/", "tests/", "package.json", "pnpm-lock.yaml",
              "vite.config.ts", "vite.config.js", "playwright.config.ts", "playwright.config.js"]
r = subprocess.run(["git", "-C", target, "diff", "--quiet", f"{code_sha}..HEAD", "--"] + controlled)
if r.returncode != 0:
    print(f"C7 FAIL: 证据陈旧——code_sha {code_sha[:8]}..HEAD 受控路径有漂移", file=sys.stderr)
    sys.exit(1)

# 必需 assert_id 集合：required_states 的 assert/not/and + overlay items 的 asserts
need = set()
for state, spec in required.items():
    if isinstance(spec, dict):
        for k in ("assert", "not", "and"):
            if spec.get(k):
                need.add(f"{state}:{spec[k]}")
for ov in overlays or []:
    for a in (ov.get("asserts") or []):
        need.add(f"overlay:{ov.get('selector', '?')}:{a}")

items = index["items"]
missing, empty = [], []
covered = 0
for key in sorted(need):
    files = items.get(key)
    if not files:
        missing.append(key)
        continue
    ok = True
    for rel in files:
        p = Path(artifacts) / rel
        if not (p.is_file() and p.stat().st_size > 0):
            empty.append(f"{key} -> {rel}")
            ok = False
    if ok:
        covered += 1

total = len(need)
agg = {
    "page_id": Path(agg_out).stem,
    "code_sha": code_sha,
    "ac_total": total,
    "ac_covered": covered,
    "ac_missing": missing,
    "ac_empty_evidence": empty,
    "qualified": (total > 0 and covered == total),
}
Path(agg_out).write_text(yaml.safe_dump(agg, allow_unicode=True, sort_keys=False), encoding="utf-8")

if missing or empty:
    print(f"C7 FAIL: 覆盖 {covered}/{total}；缺证据 {len(missing)}；空证据 {len(empty)}", file=sys.stderr)
    for m in missing: print(f"  缺: {m}", file=sys.stderr)
    for e in empty: print(f"  空: {e}", file=sys.stderr)
    sys.exit(1)
print(f"C7 PASS: 证据覆盖 {covered}/{total}，新鲜度 OK")
PY
RC=$?

case $RC in
  0) gates_write_result C7 PASS 0 "$STARTED_AT" "[{\"type\":\"ac_aggregates\",\"path\":\"$AGG_OUT\"}]" >/dev/null; exit 0;;
  3) gates_write_result C7 ERROR 3 "$STARTED_AT" >/dev/null || true; exit 3;;
  1) gates_write_result C7 FAIL 1 "$STARTED_AT" "[{\"type\":\"ac_aggregates\",\"path\":\"$AGG_OUT\"}]" >/dev/null; exit 1;;
  *) gates_write_result C7 ERROR "$RC" "$STARTED_AT" >/dev/null || true; exit 2;;
esac
