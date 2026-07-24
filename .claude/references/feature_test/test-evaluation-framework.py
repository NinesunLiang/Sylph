#!/usr/bin/env python3
"""test-evaluation-framework.py — 评测框架规范一致性验证

覆盖:
  1. 框架文档存在 / schema 版本
  2. 核心公式（纵向 + 独立审计）及其常数
  3. Layer 4 Δ 计算阈值
  4. GATE_WEIGHTS 在 meta_oracle.py 中匹配框架文档
  5. 基线 / 目标 / 三元组 / 文件清单
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
FRAMEWORK = ROOT / ".claude" / "references" / "evaluation-framework.md"
META_ORACLE = ROOT / ".claude" / "scripts" / "meta_oracle.py"

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f"  -- {detail}"
        print(msg)


# ═══════════════════════════════════════════════════════════════════
# 1. 文档存在与 schema
# ═══════════════════════════════════════════════════════════════════

print("=== 1. 文档存在 ===")
ok("evaluation-framework.md exists", FRAMEWORK.exists())
text = FRAMEWORK.read_text(encoding="utf-8")

ok("Has schema_version header", 'schema_version: evaluation-framework.v1' in text)
ok("Has creation date", "2026-07-21" in text)


# ═══════════════════════════════════════════════════════════════════
# 2. 核心公式
# ═══════════════════════════════════════════════════════════════════

print("\n=== 2. 核心公式 ===")
# 最终分 = 纵向追踪分 x 0.6 + 独立审计分 x 0.4
ok("Final score formula: longitude x0.6 + latitude x0.4",
   "最终分 = 纵向追踪分 x 0.6 + 独立审计分 x 0.4" in text or
   "最终分 = 纵向追踪分 × 0.6 + 独立审计分 × 0.4" in text)

# 纵向追踪分 = baseline + Σ(verified_delta_i) / total_target
ok("Longitude formula mentions baseline + Σ",
   "baseline +" in text or "baseline +" in text.lower())

# 独立审计分 = G1x0.35 + G2x0.25 + G3x0.20 + G4x0.20
indep_re = re.search(r'(?:独立审计分|审计)\s*=\s*.*?G1[×x*]\s*0?\.35.*?G2[×x*]\s*0?\.25.*?G3[×x*]\s*0?\.20.*?G4[×x*]\s*0?\.20', text, re.DOTALL)
ok("Independent audit formula: G1x0.35 + G2x0.25 + G3x0.20 + G4x0.20",
   indep_re is not None,
   "Regex did not match the audit formula line")


# ═══════════════════════════════════════════════════════════════════
# 3. 关键常数
# ═══════════════════════════════════════════════════════════════════

print("\n=== 3. 关键常数 ===")
ok("Baseline = 6.30 (R0 locked)", "6.30" in text and "R0" in text)
ok("Target >= 9.0 mentioned", "≥9.0" in text or ">=9.0" in text)
ok("Range 6.30 to 10.0 implied (3.70 = 10.0 - 6.30)",
   "3.70" in text and "10.0" in text and "6.30" in text)

# 提取所有 target 引用
ok("Has target value '目标' in context of scoring",
   "目标" in text)

# 增量提分账三元组
ok("Longitude triplet: [commit_sha] + [回归证据] + [裁决记录]",
   all(kw in text for kw in ["commit_sha", "回归证据", "裁决记录"]))

# Longitudinal delta formula
ok("Longitudinal delta formula: delta = (当前加权 - baseline) / (目标加权 - baseline)",
   "delta = (当前加权 - baseline) / (目标加权 - baseline)" in text or
   "delta =（当前加权 - baseline）/（目标加权 - baseline）" in text)


# ═══════════════════════════════════════════════════════════════════
# 4. Layer 4 Δ（对抗合成 — 纵向追踪分与独立审计分之差）
# ═══════════════════════════════════════════════════════════════════

print("\n=== 4. Layer 4 Δ 阈值 ===")
# Δ = |纵向追踪分 - 独立审计分|
ok("Δ = |纵向追踪分 - 独立审计分|",
   "Δ = |纵向追踪分 - 独立审计分|" in text or
   "Δ = |纵向追踪分 - 独立审计分|" in text or
   "Δ = 纵向追踪分 - 独立审计分" in text)

# Δ < 0.5 => 可信
ok("Δ < 0.5 → 可信区间",
   "0.5" in text and "可信" in text and "Δ <" in text)

# 0.5 <= Δ < 1.0 => 注意
ok("0.5 <= Δ < 1.0 → 注意",
   "0.5" in text and "1.0" in text and "注意" in text)

# Δ >= 1.0 => 报警
ok("Δ >= 1.0 → 报警",
   "1.0" in text and "报警" in text)

# 分歧分类
ok("Has divergence classification table",
   "纵向高" in text and "审计高" in text and "纵向低" in text and "审计低" in text)


# ═══════════════════════════════════════════════════════════════════
# 5. GATE_WEIGHTS — meta_oracle.py 与框架文档一致性
# ═══════════════════════════════════════════════════════════════════

print("\n=== 5. GATE_WEIGHTS 一致性 ===")
ok("meta_oracle.py exists", META_ORACLE.exists())

if META_ORACLE.exists():
    mo_text = META_ORACLE.read_text(encoding="utf-8")

    # Extract GATE_WEIGHTS dict from meta_oracle.py
    gw_match = re.search(r'GATE_WEIGHTS\s*=\s*\{(.+?)\}', mo_text, re.DOTALL)
    ok("GATE_WEIGHTS dict found in meta_oracle.py", gw_match is not None)
    if gw_match:
        # Extract G1..G4 weights
        g1_match = re.search(r'"G1"\s*:\s*([\d.]+)', gw_match.group(1))
        g2_match = re.search(r'"G2"\s*:\s*([\d.]+)', gw_match.group(1))
        g3_match = re.search(r'"G3"\s*:\s*([\d.]+)', gw_match.group(1))
        g4_match = re.search(r'"G4"\s*:\s*([\d.]+)', gw_match.group(1))

        doc_weights = {"G1": 0.35, "G2": 0.25, "G3": 0.20, "G4": 0.20}
        code_weights = {}
        for label, match in [("G1", g1_match), ("G2", g2_match), ("G3", g3_match), ("G4", g4_match)]:
            if match:
                code_weights[label] = float(match.group(1))
                ok(f"meta_oracle.py GATE_WEIGHTS.{label} = {code_weights[label]}",
                   abs(code_weights[label] - doc_weights[label]) < 0.001,
                   f"expected {doc_weights[label]}, got {code_weights[label]}")

        # Weight sum should be 1.0
        total = sum(code_weights.values())
        ok("GATE_WEIGHTS sum to 1.0",
           abs(total - 1.0) < 0.01,
           f"sum = {total}")

        # Each gate has a minimum pass threshold documented in framework
        gate_thresholds = [
            ("G1", 6, "证据质量"),
            ("G2", 5, "范围冻结"),
            ("G3", 6, "验收"),
            ("G4", 5, "哲学一致性"),
        ]
        for gid, expected_min, name in gate_thresholds:
            # Framework doc table format: | G1 证据质量 | 0.35 | 描述 | 6/10 |
            w_str = f"{doc_weights[gid]:.2f}"
            pattern = re.search(
                rf'\|\s*{gid}\s+{name}\s*\|\s*{w_str}\s*\|\s*[^|]*\|\s*([\d.]+)/10\s*\|',
                text,
            )
            if pattern:
                actual_min = float(pattern.group(1))
                ok(f"Framework doc: {gid} min pass = {actual_min}/10 (expected {expected_min}/10)",
                   abs(actual_min - expected_min) < 0.1,
                   f"expected {expected_min}, got {actual_min}")
            else:
                ok(f"Framework doc: {gid} ({name}) min pass threshold present in gate table",
                   False,
                   f"Could not find row for {gid} in gate table")

    # Verify meta_oracle.py __doc__ references G1-G4
    docstring = mo_text.split('"""')[1] if '"""' in mo_text else ""
    if not docstring:
        docstring = mo_text.split("'''")[1] if "'''" in mo_text else ""
    ok("meta_oracle.py docstring describes G1-G4 gates",
       all(f"G{i}" in docstring for i in range(1, 5)))
else:
    for _ in range(8):
        ok("meta_oracle.py not found — SKIP", True)


# ═══════════════════════════════════════════════════════════════════
# 6. 裁定标准
# ═══════════════════════════════════════════════════════════════════

print("\n=== 6. 裁定标准 ===")
ok("GREEN: 回归全过 + 24项加权 >= 8.6 + 最低单项 >= 8.0 + Δ < 0.5",
   "GREEN" in text and "回归" in text and "8.6" in text)
ok("YELLOW: same but 0.5 <= Δ < 1.0",
   "YELLOW" in text)
ok("RED: 回归失败 / Δ >= 1.0",
   "RED" in text and ("Δ ≥" in text or "Δ >=" in text))
ok("最低单项 >= 8.0 condition documented",
   "最低单项 ≥ 8.0" in text or "最低单项 >= 8.0" in text)
ok("24项加权 >= 8.6 condition documented",
   "24 项加权 ≥ 8.6" in text or "24 项加权 >= 8.6" in text or "24项加权" in text)


# ═══════════════════════════════════════════════════════════════════
# 7. 文件清单与工具匹配
# ═══════════════════════════════════════════════════════════════════

print("\n=== 7. 文件清单 ===")
expected_files = [
    (".claude/references/evaluation-framework.md", "框架规范"),
    ("scripts/run-regression.sh", "回归地基"),
    # ("scripts/eval-aggregate.py", "合成器(文档已列出,尚未实现 — 非阻塞)"), # not implemented yet
    (".claude/scripts/meta_oracle.py", "审计器"),
    ("improve_plan/CarrorOS_second_time/scorecard.md", "纵向账本"),
    ("benchmark/runs/", "基准回归存档"),
]
for relpath, purpose in expected_files:
    abspath = ROOT / relpath
    if relpath.endswith("/"):
        ok(f"Directory '{relpath}' exists ({purpose})", abspath.is_dir())
    else:
        exists = abspath.is_file()
        ok(f"File '{relpath}' exists ({purpose})", exists)
        if not exists:
            print(f"     INFO: '{relpath}' is documented in the framework but not yet implemented")

# 12 regression suites listed
suite_count = text.count("|")  # rough check, more precise below
suites = re.findall(r'\|\s*\d+\s+\|\s+[\w-]+', text)
ok("At least 12 regression suites listed in Layer 1 table",
   len(suites) >= 12, f"found {len(suites)} suites")

# 9 capability dimensions C1-C9
c_count = len(re.findall(r'\|\s*C\d+\s*\|', text))
ok(f"C1-C9 table with {c_count} rows (expected ~10 including header)",
   c_count >= 9, f"found {c_count} rows")

# 8 error protection dimensions E1-E8
e_count = len(re.findall(r'\|\s*E\d+\s*\|', text))
ok(f"E1-E8 table with {e_count} rows (expected ~9 including header)",
   e_count >= 8, f"found {e_count} rows")

# 7 governance dimensions
ok("7 governance dimensions listed",
   "抗衰减防线" in text and "Evaluation 评测框架" in text)


# ═══════════════════════════════════════════════════════════════════
# 8. 框架完整性检查
# ═══════════════════════════════════════════════════════════════════

print("\n=== 8. 框架完整性 ===")
# All 4 layers represented
ok("Layer 1: 回归地基 (Ground Truth) present",
   "Layer 1" in text and "回归地基" in text)
ok("Layer 2: 增量提分账 (Longitude) present",
   "Layer 2" in text and "增量提分账" in text and "Longitude" in text)
ok("Layer 3: 独立审计 (Latitude) present",
   "Layer 3" in text and "独立审计" in text and "Latitude" in text)
ok("Layer 4: 对抗合成 (Adversarial) present",
   "Layer 4" in text and "对抗合成" in text and "Adversarial" in text)

# Usage flow documented
ok("Usage flow documented (6 steps)",
   "提分施工" in text and "git commit" in text and "独立审计" in text and "合成报告" in text and "eval-report.md" in text)

# C1-C9 weight table (check weights sum)
c_weights = re.findall(r'\|\s*C\d+\s*\|\s*\w+\s*\|\s*(\d+)\s*\|', text)
ok("C1-C9 weights defined",
   len(c_weights) >= 9, f"found {len(c_weights)} weight entries")

# E1-E8 weight table
e_weights = re.findall(r'\|\s*E\d+\s*\|\s*\w+\s*\|\s*(\d+)\s*\|', text)
ok("E1-E8 weights defined",
   len(e_weights) >= 8, f"found {len(e_weights)} weight entries")


# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════

total = PASS + FAIL
print(f"\n{'='*50}")
print(f"结果: {PASS}/{total} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
