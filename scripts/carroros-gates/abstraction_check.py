#!/usr/bin/env python3
"""abstraction_check.py — O1 页内近似重复检测（FINAL.md v3.1 §16）
首夜仅晨报指标，不阻断。退出：恒 0
"""
from __future__ import annotations
import hashlib, json, re, subprocess, sys, yaml
from pathlib import Path
from lib.common_lib import *

def main() -> int:
    gates_parse_args()
    assert TARGET_REPO is not None, "需要 --target-repo"
    files_allowed_json = gates_mget("files_allowed", PAGE_ID)
    allowed = json.loads(files_allowed_json)
    (NIGHT_DIR / "metrics").mkdir(parents=True, exist_ok=True)
    out = NIGHT_DIR / "metrics" / "o1-duplication.yaml"

    prefix = subprocess.run(["git", "-C", str(TARGET_REPO), "rev-parse", "--show-prefix"],
                            capture_output=True, text=True).stdout.strip()

    files = []
    for pat in allowed:
        pat = pat.rstrip("/")
        if pat.endswith("/**"):
            root = Path(str(TARGET_REPO)) / (prefix + pat[:-3] if prefix else pat[:-3])
            if root.is_dir():
                for ext in ("*.ts", "*.tsx", "*.scss"):
                    files.extend(root.rglob(ext))

    window = 8
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
        for i in range(0, max(0, len(lines) - window + 1)):
            h = hashlib.sha256("\n".join(lines[i:i + window]).encode()).hexdigest()
            windows.setdefault(h, []).append((str(f), i))
            total_windows += 1

    dup_windows = sum(len(v) for v in windows.values() if len(v) > 1)
    dup_blocks = sum(1 for v in windows.values() if len(v) > 1)
    ratio = (dup_windows / total_windows * 100) if total_windows else 0.0

    metric = {
        "duplicate_windows": dup_windows,
        "duplicate_blocks": dup_blocks,
        "total_windows": total_windows,
        "duplication_ratio_pct": round(ratio, 1),
        "window_lines": window,
        "note": "O1 首夜仅报告",
    }
    out.write_text(yaml.safe_dump(metric, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"O1 metric: duplicate_blocks={dup_blocks} ratio={ratio:.1f}% -> {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
