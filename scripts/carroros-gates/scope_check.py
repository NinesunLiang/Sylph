#!/usr/bin/env python3
"""scope_check.py — C1 范围门禁（FINAL.md v3.1 §6）
校验：diff + untracked ⊆ files_allowed + spec；治理路径零触碰。
退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT
"""
from __future__ import annotations
import json, subprocess, sys
from lib.common_lib import *

def main() -> int:
    gates_parse_args()
    assert TARGET_REPO is not None, "需要 --target-repo"
    base_file = NIGHT_DIR / "page-baselines" / f"{PAGE_ID}.sha"
    if not base_file.is_file():
        print(f"ERROR: 页基线缺失: {base_file}", file=sys.stderr)
        return 2
    base_sha = base_file.read_text(encoding="utf-8").strip()
    files_allowed_json = gates_mget("files_allowed", PAGE_ID)
    spec_path = gates_mget("paths.spec", PAGE_ID)
    allowed = json.loads(files_allowed_json) + [spec_path]

    gates_preamble()
    started_at = gates_now()

    def git(*args):
        r = subprocess.run(["git", "-C", str(TARGET_REPO)] + list(args),
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"ERROR: git {' '.join(args)} 失败: {r.stderr.strip()}", file=sys.stderr)
            sys.exit(2)
        return r.stdout

    prefix = git("rev-parse", "--show-prefix").strip()
    changed = set()
    for line in git("diff", "--name-only", f"{base_sha}..HEAD").splitlines():
        if line.strip(): changed.add(line.strip())
    for line in git("diff", "--name-only").splitlines():
        if line.strip(): changed.add(line.strip())
    for line in git("diff", "--name-only", "--cached").splitlines():
        if line.strip(): changed.add(line.strip())
    r = subprocess.run(["git", "-C", str(TARGET_REPO), "ls-files", "--others", "--exclude-standard", "-z"],
                       capture_output=True)
    if r.returncode != 0:
        print("ERROR: git ls-files 失败", file=sys.stderr); return 2
    for raw in r.stdout.decode("utf-8", "replace").split("\0"):
        if raw.strip(): changed.add(raw.strip())

    gov_patterns = ("scripts/carroros-gates/", ".omc/night/", ".claude/", "/gate-results/")

    def strip_prefix(p):
        return p[len(prefix):] if prefix and p.startswith(prefix) else p

    def is_allowed(rel):
        for pat in allowed:
            pat = pat.rstrip("/")
            if pat.endswith("/**"):
                if rel == pat[:-3] or rel.startswith(pat[:-2]):
                    return True
            elif rel == pat:
                return True
        return False

    violations, gov_hits = [], []
    for p in sorted(changed):
        if any(g in p for g in gov_patterns):
            gov_hits.append(p)
            continue
        rel = strip_prefix(p)
        if not is_allowed(rel):
            violations.append(p)

    if gov_hits:
        print("FAILED_INVARIANT: 治理路径被触碰:", file=sys.stderr)
        for p in gov_hits: print(f"  {p}", file=sys.stderr)
        result_code = 3
    elif violations:
        print("C1 FAIL: 越界文件:", file=sys.stderr)
        for p in violations: print(f"  {p}", file=sys.stderr)
        result_code = 1
    else:
        print(f"C1 PASS: {len(changed)} 个文件全部在 files_allowed 内")
        result_code = 0

    status = {0: "PASS", 1: "FAIL", 3: "ERROR"}.get(result_code, "ERROR")
    exit_code = {0: 0, 1: 1, 3: 3}.get(result_code, result_code)
    gates_write_result("C1", status, exit_code, started_at)
    return result_code

if __name__ == "__main__":
    sys.exit(main())
