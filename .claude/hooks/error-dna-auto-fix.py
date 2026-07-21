#!/usr/bin/env python3
"""error-dna-auto-fix.py — Stop — 跨会话错误回顾：扫描 error-dna.json 输出未修复的顽固错误
Role: 跨会话错误回顾，只输出 fix_count > 1 的条目
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("error_dna_auto_fix"):
        sys.exit(0)

    flywheel_event("error_dna_auto_fix", "active", "P2")

    # ── Path setup ──
    hooks_dir = Path(__file__).resolve().parent
    project_root = (hooks_dir / "../..").resolve()
    dna_file = project_root / ".omc" / "state" / "error-dna.json"

    if not dna_file.exists():
        sys.exit(0)

    # ── Read and analyze error-dna.json ──
    try:
        with open(str(dna_file), "r", encoding="utf-8") as f:
            dna = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        sys.exit(0)

    signatures = dna.get("error_signatures", {})
    candidates = []

    for sig, entry in signatures.items():
        count = entry.get("count", 0)
        fix_count = entry.get("fix_count", 0)
        status = entry.get("status", "active")
        repair_cmd = entry.get("repair_command", "")
        message = entry.get("message", "")[:80]
        last_seen = entry.get("last_seen", 0)

        if count >= 3 and status == "active":
            candidates.append((count, fix_count, sig, message, repair_cmd, last_seen))

    if not candidates:
        sys.exit(0)

    candidates.sort(key=lambda x: -x[0])
    candidates = candidates[:5]

    lines = [f"[error-dna retrospective] {len(candidates)} 个顽固错误 (≥3次出现，仍 active):"]
    for count, fix_count, sig, message, repair_cmd, last_seen in candidates:
        last_str = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M') if last_seen else '未知'
        lines.append(f" · {sig[:16]} ×{count} (已尝试修复 {fix_count} 次) — {message}")
        if repair_cmd:
            lines.append(f"   ▶ 自动执行修复: `{repair_cmd}`")
        lines.append(f"   └ 上次失败: {last_str}")

    output = "|".join(lines)

    # ── Write to retrospective file ──
    retrospective_file = project_root / ".omc" / "state" / "error-dna-retrospective.txt"
    try:
        retrospective_file.parent.mkdir(parents=True, exist_ok=True)
        retrospective_file.write_text(output, encoding="utf-8")
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
