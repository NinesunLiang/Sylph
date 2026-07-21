#!/usr/bin/env python3
"""
c7-check.py — C3 架构门禁 (v6.0, .sh → .py 迁移)
只扫 diff 新增行：裸色值/魔法px/:global/!important/antd 家族 import
产出 O2 token 引用覆盖率指标（首夜仅报告，不阻断）。
退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT
"""

import json
import pathlib
import re
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

base_file = Path(common.NIGHT_DIR) / "page-baselines" / f"{common.PAGE_ID}.sha"
if not base_file.is_file():
    print(f"ERROR: 页基线缺失: {base_file}", file=sys.stderr)
    sys.exit(2)
base_sha = base_file.read_text().strip()

token_source = common.mget("ui_policy.token_source")
files_allowed_json = common.mget("files_allowed")
allowed = json.loads(files_allowed_json)


def git(*a):
    r = subprocess.run(["git", "-C", common.TARGET_REPO] + list(a),
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: git {' '.join(a)} 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout


prefix = git("rev-parse", "--show-prefix").strip()

diff = git("diff", "--unified=0", f"{base_sha}..HEAD", "--", "*.ts", "*.tsx", "*.scss", "*.css", "*.module.scss")
diff += git("diff", "--unified=0", "--", "*.ts", "*.tsx", "*.scss", "*.css", "*.module.scss")

current_file = None
new_lines = []
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
        continue
    if HEX.search(code):
        violations.append(f"{f}:{n} 裸色值: {stripped[:80]}")
    for m in PX.finditer(code):
        v = float(m.group(1))
        if v in (0, 1):
            continue
        if "var(" in code or "$" in code:
            continue
        violations.append(f"{f}:{n} 魔法px({m.group(1)}): {stripped[:80]}")
    if ":global" in code:
        violations.append(f"{f}:{n} :global 禁用: {stripped[:80]}")
    if "!important" in code:
        violations.append(f"{f}:{n} !important 禁用: {stripped[:80]}")
    if ANTD.search(code):
        violations.append(f"{f}:{n} antd 家族 import（Patch A 禁用）: {stripped[:80]}")

# O2 token 引用覆盖率
style_files = []
for pat in allowed:
    pat = pat.rstrip("/")
    if pat.endswith("/**"):
        root = Path(common.TARGET_REPO) / (prefix + pat[:-3] if prefix else pat[:-3])
        if root.is_dir():
            for ext in ("*.scss", "*.css", "*.module.scss", "*.tsx", "*.ts"):
                style_files.extend(root.rglob(ext))

total, with_token = 0, 0
for sf in set(style_files):
    if in_token_source(str(sf.relative_to(common.TARGET_REPO)) if prefix else str(sf)):
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

# O2 指标落夜目录
metric_out = Path(common.NIGHT_DIR) / "metrics" / f"{common.PAGE_ID}.o2.json"
metric_out.parent.mkdir(parents=True, exist_ok=True)
metric_out.write_text(json.dumps({
    "token_reference_coverage": round(coverage, 1),
    "files_total": total,
    "files_with_token": with_token,
}))

if violations:
    print("C3 FAIL:", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    common.write_result("C3", "FAIL", 1, started_at)
    sys.exit(1)

print("C3 PASS: 架构红线零违规")
common.write_result("C3", "PASS", 0, started_at)
