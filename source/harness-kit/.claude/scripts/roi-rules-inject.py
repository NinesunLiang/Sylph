#!/usr/bin/env python3
"""
roi-rules-inject.py — pretool-rules-inject ROI
Cross-platform Python resolution (DG-105)

替代 bash 版的 ROI 计算，分析 flywheel.log 中 pretool_rules_inject 相关指标。
"""
import os
from pathlib import Path

FW = Path.home() / ".claude" / "flywheel.log"


def main():
    if not FW.exists():
        print("flywheel.log unavailable")
        return

    rules = pg = cg = ap = 0
    lines = FW.read_text(encoding="utf-8").splitlines()
    for l in lines:
        if "pretool_rules_inject" in l:
            rules += 1
        elif "permission_gate_blocked" in l:
            pg += 1
        elif "completion_gate" in l:
            cg += 1
        elif "anti_pattern" in l:
            ap += 1

    cost = rules * 455
    pg_save = pg * 500
    cg_save = cg * 300
    total_save = pg_save + cg_save

    print("=== pretool-rules-inject ROI ===")
    print(f"注入次数: {rules}")
    print(f"预计Token成本: ~{cost} tokens")
    print()
    print("违规拦截:")
    print(f"  permission-gate: {pg} 次 (节省 ~{pg_save} tokens)")
    print(f"  completion-gate: {cg} 次 (节省 ~{cg_save} tokens)")
    print(f"  anti-pattern: {ap} 次")
    print()
    if total_save > cost:
        print(f"净收益: +{total_save - cost} tokens (ROI {total_save * 100 // cost}%)")
    else:
        print(f"净成本: -{cost - total_save} tokens")


if __name__ == "__main__":
    main()
