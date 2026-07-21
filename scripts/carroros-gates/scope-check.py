#!/usr/bin/env python3
"""
scope-check.py — C1 范围门禁 (v6.0, .sh → .py 迁移)
校验：diff + untracked ⊆ files_allowed + spec；治理路径零触碰。
退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib import common

remaining = common.parse_args()
if not common.TARGET_REPO:
    print("ERROR: 需要 --target-repo", file=sys.stderr)
    sys.exit(2)
common.preamble()
started_at = common.now_iso()

base_file = Path(common.NIGHT_DIR) / "page-baselines" / f"{common.PAGE_ID}.sha"
if not base_file.is_file():
    print(f"ERROR: 页基线缺失: {base_file}（夜循环步 0 未记录）", file=sys.stderr)
    sys.exit(2)
base_sha = base_file.read_text().strip()

files_allowed_json = common.mget("files_allowed")
spec_path = common.mget("paths.spec")
allowed = json.loads(files_allowed_json) + [spec_path]


def git(*a, capture=True):
    r = subprocess.run(["git", "-C", common.TARGET_REPO] + list(a),
                       capture_output=capture, text=True)
    if r.returncode != 0:
        print(f"ERROR: git {' '.join(a)} 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout


prefix = git("rev-parse", "--show-prefix").strip()

changed = set()
for line in git("diff", "--name-only", f"{base_sha}..HEAD").splitlines():
    if line.strip():
        changed.add(line.strip())
for line in git("diff", "--name-only").splitlines():
    if line.strip():
        changed.add(line.strip())
for line in git("diff", "--name-only", "--cached").splitlines():
    if line.strip():
        changed.add(line.strip())
r = subprocess.run(["git", "-C", common.TARGET_REPO, "ls-files", "--others", "--exclude-standard", "-z"],
                   capture_output=True)
if r.returncode != 0:
    print("ERROR: git ls-files 失败", file=sys.stderr)
    sys.exit(2)
for raw in r.stdout.decode("utf-8", "replace").split("\0"):
    if raw.strip():
        changed.add(raw.strip())

GOV_PATTERNS = ("scripts/carroros-gates/", ".omc/night/", ".claude/", "/gate-results/")


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
    if any(g in p for g in GOV_PATTERNS):
        gov_hits.append(p)
        continue
    rel = strip_prefix(p)
    if not is_allowed(rel):
        violations.append(p)

if gov_hits:
    print("FAILED_INVARIANT: 治理路径被触碰:", file=sys.stderr)
    for p in gov_hits:
        print(f"  {p}", file=sys.stderr)
    common.write_result("C1", "ERROR", 3, started_at)
    sys.exit(3)

if violations:
    print("C1 FAIL: 越界文件:", file=sys.stderr)
    for p in violations:
        print(f"  {p}", file=sys.stderr)
    common.write_result("C1", "FAIL", 1, started_at)
    sys.exit(1)

print(f"C1 PASS: {len(changed)} 个文件全部在 files_allowed 内")
common.write_result("C1", "PASS", 0, started_at)
