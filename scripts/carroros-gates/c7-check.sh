#!/usr/bin/env bash
# c7-check.sh — C3 架构门禁（FINAL.md v3.1 §6 + E5/E3 勘误 + O2 指标）
# 只扫 diff 新增行（E5：裸色值正则不误伤注释/既有代码）：
#   - 裸色值（token_source 之外）/ 魔法 px（0|1px 放行，E3）/ :global / !important / antd 家族 import
# 另产出 O2 token 引用覆盖率指标（首夜仅报告，不阻断）。
# 退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
gates_parse_args "$@"
[[ -n "$TARGET_REPO" ]] || { echo "ERROR: 需要 --target-repo" >&2; exit 2; }
gates_preamble
STARTED_AT="$(gates_now)"

BASE_FILE="$NIGHT_DIR/page-baselines/$PAGE_ID.sha"
[[ -f "$BASE_FILE" ]] || { echo "ERROR: 页基线缺失: $BASE_FILE" >&2; exit 2; }
BASE_SHA="$(tr -d '[:space:]' < "$BASE_FILE")"
TOKEN_SOURCE="$(gates_mget ui_policy.token_source "$PAGE_ID")" || exit 2
FILES_ALLOWED_JSON="$(gates_mget files_allowed "$PAGE_ID")" || exit 2

python3 - "$TARGET_REPO" "$BASE_SHA" "$TOKEN_SOURCE" "$FILES_ALLOWED_JSON" << 'PY'
import json, re, subprocess, sys

target, base, token_source, allowed_json = sys.argv[1:5]
allowed = json.loads(allowed_json)

def git(*args):
    r = subprocess.run(["git", "-C", target] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: git {' '.join(args)} 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout

prefix = git("rev-parse", "--show-prefix").strip()

# 收集页目录内新增行（unified=0 保证只有纯新增）
diff = git("diff", "--unified=0", f"{base}..HEAD", "--", "*.ts", "*.tsx", "*.scss", "*.css", "*.module.scss")
diff += git("diff", "--unified=0", "--", "*.ts", "*.tsx", "*.scss", "*.css", "*.module.scss")

current_file = None
new_lines = []  # (file, lineno, text)
for line in diff.splitlines():
    if line.startswith("+++ b/"):
        current_file = line[6:]
    elif line.startswith("@@") and current_file:
        m = re.search(r"\+(\d+)", line)
        new_lineno = int(m.group(1)) if m else 0
    elif line.startswith("+") and not line.startswith("+++") and current_file:
        new_lines.append((current_file, new_lineno, line[1:]))
        new_lineno += 1

def in_scope(f):
    rel = f[len(prefix):] if prefix and f.startswith(prefix) else f
    for pat in allowed:
        pat = pat.rstrip("/")
        if pat.endswith("/**") and (rel == pat[:-3] or rel.startswith(pat[:-2])):
            return True
    return False

def in_token_source(f):
    rel = f[len(prefix):] if prefix and f.startswith(prefix) else f
    return rel.startswith(token_source.rstrip("/"))

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
PX = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)px\b")
ANTD = re.compile(r"""(?:from\s+['"]|require\(\s*['"]|import\(\s*['"])antd|@ant-design""")

violations = []
for f, n, text in new_lines:
    if not in_scope(f) or in_token_source(f):
        continue
    code = text.split("//")[0] if not f.endswith((".scss", ".css")) else text
    stripped = code.strip()
    if not stripped or stripped.startswith(("/*", "*", "//")):
        continue  # E5：跳过注释行
    if HEX.search(code):
        violations.append(f"{f}:{n} 裸色值: {stripped[:80]}")
    for m in PX.finditer(code):
        v = float(m.group(1))
        if v in (0, 1):
            continue  # E3：0/1px 放行（边框hairline）
        if "var(" in code or "$" in code:
            continue  # 走 token 的行不判魔法数
        violations.append(f"{f}:{n} 魔法px({m.group(1)}): {stripped[:80]}")
    if ":global" in code:
        violations.append(f"{f}:{n} :global 禁用: {stripped[:80]}")
    if "!important" in code:
        violations.append(f"{f}:{n} !important 禁用: {stripped[:80]}")
    if ANTD.search(code):
        violations.append(f"{f}:{n} antd 家族 import（Patch A 禁用）: {stripped[:80]}")

# O2 token 引用覆盖率（报告指标，不阻断）
import pathlib
style_files = []
for pat in allowed:
    pat = pat.rstrip("/")
    if pat.endswith("/**"):
        root = pathlib.Path(target) / (prefix + pat[:-3] if prefix else pat[:-3])
        if root.is_dir():
            for ext in ("*.scss", "*.css", "*.module.scss", "*.tsx", "*.ts"):
                style_files.extend(root.rglob(ext))
total, with_token = 0, 0
for sf in set(style_files):
    if in_token_source(str(sf.relative_to(target)) if prefix else str(sf)):
        continue
    try:
        content = sf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    total += 1
    if token_source.rstrip("/") in content or "tokens/" in content:
        with_token += 1
coverage = (with_token / total * 100) if total else 100.0
print(f"O2 metric: token_reference_coverage={coverage:.0f}% ({with_token}/{total})")
metric = {"token_reference_coverage": round(coverage, 1), "files_total": total, "files_with_token": with_token}
pathlib.Path(sys.argv[1], ".omc-o2-metric.json").write_text(json.dumps(metric))

if violations:
    print("C3 FAIL:", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    sys.exit(1)
print("C3 PASS: 架构红线零违规")
PY
RC=$?

# O2 指标落夜目录（供 morning-report 聚合）
if [[ -f "$TARGET_REPO/.omc-o2-metric.json" ]]; then
  mkdir -p "$NIGHT_DIR/metrics"
  mv "$TARGET_REPO/.omc-o2-metric.json" "$NIGHT_DIR/metrics/$PAGE_ID.o2.json"
fi

case $RC in
  0) gates_write_result C3 PASS 0 "$STARTED_AT" >/dev/null; exit 0;;
  3) gates_write_result C3 ERROR 3 "$STARTED_AT" >/dev/null || true; exit 3;;
  1) gates_write_result C3 FAIL 1 "$STARTED_AT" >/dev/null; exit 1;;
  *) gates_write_result C3 ERROR "$RC" "$STARTED_AT" >/dev/null || true; exit 2;;
esac
