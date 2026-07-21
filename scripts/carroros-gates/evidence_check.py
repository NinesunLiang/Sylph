#!/usr/bin/env python3
"""evidence_check.py — C7 证据门禁（FINAL.md v3.1 §5/§6 + E6 + P0-2）
退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT
"""
from __future__ import annotations
import json, subprocess, sys, yaml
from pathlib import Path
from lib.common_lib import *

def main() -> int:
    gates_parse_args()
    assert TARGET_REPO is not None, "需要 --target-repo"
    artifacts_rel = gates_mget("paths.artifacts", PAGE_ID)
    required_json = gates_mget("required_states", PAGE_ID)
    overlay_json = gates_mget("overlay_contract.items", PAGE_ID)
    required = json.loads(required_json)
    overlays = json.loads(overlay_json)

    night_date = NIGHT_DIR.name
    artifacts_dir = TARGET_REPO / artifacts_rel.replace("{date}", night_date)
    (NIGHT_DIR / "ac-aggregates").mkdir(parents=True, exist_ok=True)
    agg_out = NIGHT_DIR / "ac-aggregates" / f"{PAGE_ID}.yaml"

    gates_preamble()
    started_at = gates_now()

    idx_path = artifacts_dir / "evidence-index.yaml"
    if not idx_path.is_file():
        print(f"C7 FAIL: evidence-index.yaml 缺失: {idx_path}", file=sys.stderr)
        return 1
    try:
        index = yaml.safe_load(idx_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"C7 FAIL: evidence-index.yaml 解析失败: {e}", file=sys.stderr)
        return 1
    if not isinstance(index, dict) or not isinstance(index.get("items"), dict):
        print("C7 FAIL: evidence-index.yaml 缺 items", file=sys.stderr)
        return 1

    code_sha = index.get("code_sha")
    if not code_sha:
        print("C7 FAIL: evidence-index.yaml 缺 code_sha", file=sys.stderr)
        return 1

    controlled = ["src/", "tests/", "package.json", "pnpm-lock.yaml",
                  "vite.config.ts", "vite.config.js", "playwright.config.ts", "playwright.config.js"]
    r = subprocess.run(["git", "-C", str(TARGET_REPO), "diff", "--quiet",
                        f"{code_sha}..HEAD", "--"] + controlled)
    if r.returncode != 0:
        print(f"C7 FAIL: 证据陈旧——code_sha {code_sha[:8]}..HEAD 受控路径有漂移", file=sys.stderr)
        return 1

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
        for rel_path in files:
            p = artifacts_dir / rel_path
            if not (p.is_file() and p.stat().st_size > 0):
                empty.append(f"{key} -> {rel_path}")
                ok = False
        if ok:
            covered += 1

    total = len(need)
    agg = {
        "page_id": PAGE_ID,
        "code_sha": code_sha,
        "ac_total": total,
        "ac_covered": covered,
        "ac_missing": missing,
        "ac_empty_evidence": empty,
        "qualified": (total > 0 and covered == total),
    }
    agg_out.write_text(yaml.safe_dump(agg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    if missing or empty:
        print(f"C7 FAIL: 覆盖 {covered}/{total}；缺证据 {len(missing)}；空证据 {len(empty)}", file=sys.stderr)
        for m in missing: print(f"  缺: {m}", file=sys.stderr)
        for e in empty: print(f"  空: {e}", file=sys.stderr)
        code = 1
    else:
        print(f"C7 PASS: 证据覆盖 {covered}/{total}，新鲜度 OK")
        code = 0

    status = {0: "PASS", 1: "FAIL"}.get(code, "ERROR")
    evidence = [{"type": "ac_aggregates", "path": str(agg_out)}]
    gates_write_result("C7", status, code, started_at, evidence=evidence)
    return code

if __name__ == "__main__":
    sys.exit(main())
