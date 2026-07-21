#!/usr/bin/env python3
"""
evidence-check.py — C7 证据门禁 (v6.0, .sh → .py 迁移)
校验：每个 required assert_id 有证据；文件存在+非空；code_sha 无漂移。
产出：$NIGHT_DIR/ac-aggregates/$PAGE_ID.yaml
退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT
"""

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib import common

common.parse_args()
if not common.TARGET_REPO:
    print("ERROR: 需要 --target-repo", file=sys.stderr)
    sys.exit(2)
common.preamble()
started_at = common.now_iso()

artifacts_rel = common.mget("paths.artifacts")
required_json = common.mget("required_states")
overlay_json = common.mget("overlay_contract.items")

required = json.loads(required_json)
overlays = json.loads(overlay_json)

night_date = Path(common.NIGHT_DIR).name
artifacts_dir = Path(common.TARGET_REPO) / artifacts_rel.replace("{date}", night_date)

agg_out = Path(common.NIGHT_DIR) / "ac-aggregates" / f"{common.PAGE_ID}.yaml"
agg_out.parent.mkdir(parents=True, exist_ok=True)

idx_path = artifacts_dir / "evidence-index.yaml"
if not idx_path.is_file():
    print(f"C7 FAIL: evidence-index.yaml 缺失: {idx_path}", file=sys.stderr)
    common.write_result("C7", "FAIL", 1, started_at)
    sys.exit(1)

try:
    index = yaml.safe_load(idx_path.read_text(encoding="utf-8"))
except Exception as e:
    print(f"C7 FAIL: evidence-index.yaml 解析失败: {e}", file=sys.stderr)
    common.write_result("C7", "FAIL", 1, started_at)
    sys.exit(1)

if not isinstance(index, dict) or not isinstance(index.get("items"), dict):
    print("C7 FAIL: evidence-index.yaml 缺 items", file=sys.stderr)
    common.write_result("C7", "FAIL", 1, started_at)
    sys.exit(1)

code_sha = index.get("code_sha")
if not code_sha:
    print("C7 FAIL: evidence-index.yaml 缺 code_sha", file=sys.stderr)
    common.write_result("C7", "FAIL", 1, started_at)
    sys.exit(1)

# 新鲜度
controlled = ["src/", "tests/", "package.json", "pnpm-lock.yaml",
              "vite.config.ts", "vite.config.js", "playwright.config.ts", "playwright.config.js"]
r = subprocess.run(
    ["git", "-C", common.TARGET_REPO, "diff", "--quiet", f"{code_sha}..HEAD", "--"] + controlled)
if r.returncode != 0:
    print(f"C7 FAIL: 证据陈旧——code_sha {code_sha[:8]}..HEAD 受控路径有漂移", file=sys.stderr)
    common.write_result("C7", "FAIL", 1, started_at)
    sys.exit(1)

# 必需 assert_id 集合
need = set()
for state, spec in required.items():
    if isinstance(spec, dict):
        for k in ("assert", "not", "and"):
            if spec.get(k):
                need.add(f"{state}:{spec[k]}")
for ov in overlays or []:
    for a in ov.get("asserts") or []:
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
        p = artifacts_dir / rel
        if not (p.is_file() and p.stat().st_size > 0):
            empty.append(f"{key} -> {rel}")
            ok = False
    if ok:
        covered += 1

total = len(need)
agg = {
    "page_id": agg_out.stem,
    "code_sha": code_sha,
    "ac_total": total,
    "ac_covered": covered,
    "ac_missing": missing,
    "ac_empty_evidence": empty,
    "qualified": (total > 0 and covered == total),
}
agg_out.write_text(yaml.safe_dump(agg, allow_unicode=True, sort_keys=False), encoding="utf-8")

agg_evidence = json.dumps([{"type": "ac_aggregates", "path": str(agg_out)}], ensure_ascii=False)

if missing or empty:
    print(f"C7 FAIL: 覆盖 {covered}/{total}；缺证据 {len(missing)}；空证据 {len(empty)}", file=sys.stderr)
    for m in missing:
        print(f"  缺: {m}", file=sys.stderr)
    for e in empty:
        print(f"  空: {e}", file=sys.stderr)
    common.write_result("C7", "FAIL", 1, started_at, agg_evidence)
    sys.exit(1)

print(f"C7 PASS: 证据覆盖 {covered}/{total}，新鲜度 OK")
common.write_result("C7", "PASS", 0, started_at, agg_evidence)
