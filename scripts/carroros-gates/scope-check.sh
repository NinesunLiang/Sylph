#!/usr/bin/env bash
# scope-check.sh — C1 范围门禁（FINAL.md v3.1 §6）
# 校验：diff + untracked ⊆ files_allowed + spec；治理路径零触碰。
# 输入：页基线 $NIGHT_DIR/page-baselines/$PAGE_ID.sha（夜循环步 0 记录）。
# 退出：0=PASS 1=FAIL（越界） 2=ERROR 3=FAILED_INVARIANT

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
gates_parse_args "$@"
[[ -n "$TARGET_REPO" ]] || { echo "ERROR: 需要 --target-repo（或 TARGET_REPO 环境变量）" >&2; exit 2; }
gates_preamble
STARTED_AT="$(gates_now)"

BASE_FILE="$NIGHT_DIR/page-baselines/$PAGE_ID.sha"
[[ -f "$BASE_FILE" ]] || { echo "ERROR: 页基线缺失: ${BASE_FILE}（夜循环步 0 未记录）" >&2; exit 2; }
BASE_SHA="$(tr -d '[:space:]' < "$BASE_FILE")"

FILES_ALLOWED_JSON="$(gates_mget files_allowed "$PAGE_ID")" || exit 2
SPEC_PATH="$(gates_mget paths.spec "$PAGE_ID")" || exit 2

python3 - "$TARGET_REPO" "$BASE_SHA" "$FILES_ALLOWED_JSON" "$SPEC_PATH" << 'PY'
import json, subprocess, sys

target, base, allowed_json, spec = sys.argv[1:5]
allowed = json.loads(allowed_json) + [spec]

def git(*args, capture=True):
    r = subprocess.run(["git", "-C", target] + list(args),
                       capture_output=capture, text=True)
    if r.returncode != 0:
        print(f"ERROR: git {' '.join(args)} 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout

prefix = git("rev-parse", "--show-prefix").strip()  # target 相对 git 根的前缀（外部 repo 为空）

changed = set()
for line in git("diff", "--name-only", f"{base}..HEAD").splitlines():
    if line.strip(): changed.add(line.strip())
for line in git("diff", "--name-only").splitlines():  # 未提交改动
    if line.strip(): changed.add(line.strip())
for line in git("diff", "--name-only", "--cached").splitlines():  # 已暂存
    if line.strip(): changed.add(line.strip())
r = subprocess.run(["git", "-C", target, "ls-files", "--others", "--exclude-standard", "-z"],
                   capture_output=True)
if r.returncode != 0:
    print("ERROR: git ls-files 失败", file=sys.stderr); sys.exit(2)
for raw in r.stdout.decode("utf-8", "replace").split("\0"):
    if raw.strip(): changed.add(raw.strip())

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
    for p in gov_hits: print(f"  {p}", file=sys.stderr)
    sys.exit(3)
if violations:
    print("C1 FAIL: 越界文件:", file=sys.stderr)
    for p in violations: print(f"  {p}", file=sys.stderr)
    sys.exit(1)
print(f"C1 PASS: {len(changed)} 个文件全部在 files_allowed 内")
PY
RC=$?

case $RC in
  0) gates_write_result C1 PASS 0 "$STARTED_AT" >/dev/null; exit 0;;
  3) gates_write_result C1 ERROR 3 "$STARTED_AT" >/dev/null || true; exit 3;;
  1) gates_write_result C1 FAIL 1 "$STARTED_AT" >/dev/null; exit 1;;
  *) gates_write_result C1 ERROR "$RC" "$STARTED_AT" >/dev/null || true; exit 2;;
esac
