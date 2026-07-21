#!/usr/bin/env python3
"""
abstraction-check.py — O1 页内近似重复检测 (v6.0, .sh → .py 迁移)
方法：规范化行（去空白/注释）→ 8 行滑动窗口哈希 → 跨位置重复窗口计数。
产出：$NIGHT_DIR/metrics/o1-duplication.yaml（morning-report 聚合）。
退出：恒 0（指标型门禁，首夜不阻断）
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

# argparse
import argparse
p = argparse.ArgumentParser()
p.add_argument("--manifest", required=True)
p.add_argument("--page-id", required=True)
p.add_argument("--night-dir", required=True)
p.add_argument("--target-repo", required=True)
args = p.parse_args()

NIGHT_DIR = Path(args.night_dir)
PAGE_ID = args.page_id
TARGET_REPO = args.target_repo

# 读取 manifest files_allowed
r = subprocess.run(
    [sys.executable, str(Path(__file__).resolve().parent.parent.parent.parent /
                         ".claude/scripts/carros_base.py"),
     "manifest-json", "--manifest", args.manifest,
     "--get", "files_allowed", "--page-id", PAGE_ID],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print(f"ERROR: manifest-json 失败: {r.stderr.strip()}", file=sys.stderr)
    sys.exit(2)
allowed = json.loads(r.stdout.strip())

r = subprocess.run(["git", "-C", args.target_repo, "rev-parse", "--show-prefix"],
                   capture_output=True, text=True)
prefix = r.stdout.strip()

files = []
for pat in allowed:
    pat = pat.rstrip("/")
    if pat.endswith("/**"):
        root = Path(args.target_repo) / (prefix + pat[:-3] if prefix else pat[:-3])
        if root.is_dir():
            for ext in ("*.ts", "*.tsx", "*.scss"):
                files.extend(root.rglob(ext))

WINDOW = 8
windows = {}
total_windows = 0
for f in sorted(set(files)):
    try:
        raw = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    lines = []
    for ln in raw.splitlines():
        s = re.sub(r"//.*$", "", ln).strip()
        s = re.sub(r"\s+", " ", s)
        if s and not s.startswith(("/*", "*")):
            lines.append(s)
    for i in range(0, max(0, len(lines) - WINDOW + 1)):
        h = hashlib.sha256("\n".join(lines[i:i + WINDOW]).encode()).hexdigest()
        windows.setdefault(h, []).append((str(f), i))
        total_windows += 1

dup_windows = sum(len(v) for h, v in windows.items() if len(v) > 1)
dup_blocks = sum(1 for h, v in windows.items() if len(v) > 1)
ratio = (dup_windows / total_windows * 100) if total_windows else 0.0

metric = {
    "duplicate_windows": dup_windows,
    "duplicate_blocks": dup_blocks,
    "total_windows": total_windows,
    "duplication_ratio_pct": round(ratio, 1),
    "window_lines": WINDOW,
    "note": "O1 首夜仅报告；ratio > 15% 建议人工看一眼组件抽象",
}

out_dir = NIGHT_DIR / "metrics"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "o1-duplication.yaml"
out.write_text(yaml.safe_dump(metric, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(f"O1 metric: duplicate_blocks={dup_blocks} ratio={ratio:.1f}% -> {out}")
