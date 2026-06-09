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
    state_dir = project_root / ".omc" / "state"

    # 读取 retry-budget.json（新格式，error-dna.py 持续写入）
    budget_file = state_dir / "retry-budget.json"
    candidates = []
    if budget_file.exists():
        try:
            with open(str(budget_file), "r", encoding="utf-8") as f:
                budget = json.load(f)
            sigs = budget.get("signatures", {})
            for sig, entry in sigs.items():
                count = entry.get("retry_count", 0)
                label = entry.get("label", "")[:80]
                error_type = entry.get("error_type", "runtime")
                last_seen = entry.get("last_seen", 0)
                if count >= 3:
                    candidates.append((count, 0, sig, label, "", last_seen, error_type))
        except Exception:
            pass

    # 回退或补充读取旧格式 error-dna.json
    dna_file = state_dir / "error-dna.json"
    if dna_file.exists() and not candidates:
        try:
            with open(str(dna_file), "r", encoding="utf-8") as f:
                dna = json.load(f)
            signatures = dna.get("error_signatures", {})
            for sig, entry in signatures.items():
                count = entry.get("count", 0)
                fix_count = entry.get("fix_count", 0)
                status = entry.get("status", "active")
                repair_cmd = entry.get("repair_command", "")
                message = entry.get("message", "")[:80]
                error_type = entry.get("error_type", "runtime")
                last_seen = entry.get("last_seen", 0)
                if count >= 3 and status == "active":
                    candidates.append((count, fix_count, sig, message, repair_cmd, last_seen, error_type))
        except Exception:
            pass

    if not candidates:
        sys.exit(0)

    candidates.sort(key=lambda x: -x[0])
    candidates = candidates[:5]

    lines = [f"[error-dna retrospective] {len(candidates)} 个顽固错误 (≥3次出现，仍 active):"]
    for count, fix_count, sig, message, repair_cmd, last_seen, error_type in candidates:
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
