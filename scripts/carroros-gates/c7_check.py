#!/usr/bin/env python3
"""c7_check.py — C3 架构门禁（FINAL.md v3.1 §6 + E5/E3 + O2 指标）
退出：0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT
"""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path
from lib.common_lib import *

def main() -> int:
    gates_parse_args()
    assert TARGET_REPO is not None, "需要 --target-repo"
    base_file = NIGHT_DIR / "page-baselines" / f"{PAGE_ID}.sha"
    if not base_file.is_file():
        print(f"ERROR: 页基线缺失: {base_file}", file=sys.stderr)
        return 2
    base_sha = base_file.read_text(encoding="utf-8").strip()
    token_source = gates_mget("ui_policy.token_source", PAGE_ID)
    files_allowed_json = gates_mget("files_allowed", PAGE_ID)
    allowed = json.loads(files_allowed_json)

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

    hex_re = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    px_re = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)px\b")
    antd_re = re.compile(r"""(?:from\s+['"]|require\(\s*['"]|import\(\s*['"])antd|@ant-design""")

    violations = []
    for f, n, text in new_lines:
        if not in_scope(f) or in_token_source(f):
            continue
        code = text.split("//")[0] if not f.endswith((".scss", ".css")) else text
        stripped = code.strip()
        if not stripped or stripped.startswith(("/*", "*", "//")):
            continue
        if hex_re.search(code):
            violations.append(f"{f}:{n} 裸色值: {stripped[:80]}")
        for m in px_re.finditer(code):
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
        if antd_re.search(code):
            violations.append(f"{f}:{n} antd 家族 import: {stripped[:80]}")

    # O2 token reference coverage
    style_files = []
    for pat in allowed:
        pat = pat.rstrip("/")
        if pat.endswith("/**"):
            root = Path(str(TARGET_REPO)) / (prefix + pat[:-3] if prefix else pat[:-3])
            if root.is_dir():
                for ext in ("*.scss", "*.css", "*.module.scss", "*.tsx", "*.ts"):
                    style_files.extend(root.rglob(ext))
    total, with_token = 0, 0
    for sf in set(style_files):
        rel = str(sf.relative_to(TARGET_REPO)) if prefix else str(sf)
        if in_token_source(rel):
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
    (NIGHT_DIR / "metrics").mkdir(parents=True, exist_ok=True)
    (NIGHT_DIR / "metrics" / f"{PAGE_ID}.o2.json").write_text(json.dumps(metric), encoding="utf-8")

    if violations:
        print("C3 FAIL:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        code = 1
    else:
        print("C3 PASS: 架构红线零违规")
        code = 0
    status = {0: "PASS", 1: "FAIL"}.get(code, "ERROR")
    gates_write_result("C3", status, code, started_at)
    return code

if __name__ == "__main__":
    sys.exit(main())
