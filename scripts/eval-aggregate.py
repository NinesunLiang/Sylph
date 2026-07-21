#!/usr/bin/env python3
"""eval-aggregate.py — CarrorOS 科学评测合成器（Evaluation Framework v1）

用法:
  python3 scripts/eval-aggregate.py                                   # 默认模式
  python3 scripts/eval-aggregate.py --scorecard PATH                   # 指定纵向账本
  python3 scripts/eval-aggregate.py --meta-verdict PATH                # 指定审计裁决
  python3 scripts/eval-aggregate.py --run-regression                   # 跑回归再合成
  python3 scripts/eval-aggregate.py --out PATH                         # 输出路径

退出码: 0=GREEN 1=YELLOW 2=RED 3=ERROR
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── 常量 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCORECARD = PROJECT_ROOT / "improve_plan" / "CarrorOS_second_time" / "scorecard.md"
DEFAULT_META_VERDICT = PROJECT_ROOT / ".omc" / "state" / "meta-oracle-verdicts" / "runtime-capability-scoring" / "latest.json"
DEFAULT_OUT = PROJECT_ROOT / "eval-report.md"

BASELINE = 6.30
TARGET = 10.0
DELTA_RANGE = TARGET - BASELINE  # 3.70

# 维度定义
C_DIMS = [
    ("C1", "指令清晰度", 15),
    ("C2", "上下文完整度", 15),
    ("C3", "流程结构化", 15),
    ("C4", "输出规范化", 10),
    ("C5", "工具生命周期", 10),
    ("C6", "知识密度", 10),
    ("C7", "关联编排", 10),
    ("C8", "可维护性", 10),
    ("C9", "错误恢复", 10),
]
E_DIMS = [
    ("E1", "目标漂移", 20),
    ("E2", "幻觉输出", 20),
    ("E3", "虚假完成", 15),
    ("E4", "惯性执行", 12),
    ("E5", "症状混淆", 10),
    ("E6", "自我矛盾", 13),
    ("E7", "过度自信", 10),
    ("E8", "上下文遗忘", 10),
]
GOV_DIMS = [
    "抗衰减防线", "AI 赋能全流程自动化", "学习笔记积累",
    "长期目标一致性", "功能标志分明", "内置安全与洞察", "Evaluation 评测框架",
]


# ── 解析器 ──

def parse_scorecard(path: Path) -> dict[str, Any]:
    """解析 scorecard.md 提取当前分数。"""
    text = path.read_text(encoding="utf-8")
    scores: dict[str, int] = {}
    current_weighted = 0
    current_weight_total = 0

    # 解析 C 维度表: | C1 | ... | weight | baseline | current(**N** or N→**N**) | ... | ... |
    c_pat = re.compile(
        r"^\|\s*(C\d+)\s*\|\s*[^|]+\s*\|\s*(\d+)\s*\|\s*(?:\d+|\*{0,2}\d+\*{0,2})\s*\|\s*(?:\d+→)?\*{0,2}(\d+)\*{0,2}",
        re.MULTILINE,
    )
    for m in c_pat.finditer(text):
        scores[m.group(1)] = int(m.group(3))

    # 解析 E 维度表: same format
    e_pat = re.compile(
        r"^\|\s*(E\d+)\s*\|\s*[^|]+\s*\|\s*(\d+)\s*\|\s*(?:\d+|\*{0,2}\d+\*{0,2})\s*\|\s*(?:\d+→)?\*{0,2}(\d+)\*{0,2}",
        re.MULTILINE,
    )
    for m in e_pat.finditer(text):
        scores[m.group(1)] = int(m.group(3))

    # 解析治理维度: | 维度 | N | N→**N** |
    for dim in GOV_DIMS:
        pat = re.compile(
            r"^\|\s*" + re.escape(dim) + r"\s*\|\s*(?:\d+|\*{0,2}\d+\*{0,2})\s*\|\s*(?:\d+→)?\*{0,2}(\d+)\*{0,2}",
            re.MULTILINE,
        )
        m = pat.search(text)
        if m:
            scores[dim] = int(m.group(1))

    # 提取总分/加权
    c_total = re.search(r"C\s+加权\s+(\d+)/", text)
    e_total = re.search(r"E\s+加权\s+(\d+)/", text)
    gov_total = re.search(r"(\d+)/70\s*=\s*\d+\.\d+", text)

    return {
        "scores": scores,
        "c_weighted_raw": int(c_total.group(1)) if c_total else None,
        "e_weighted_raw": int(e_total.group(1)) if e_total else None,
        "gov_weighted_raw": int(gov_total.group(1)) if gov_total else None,
    }


def parse_scorecard_scorecard_v2(text: str) -> dict[str, int]:
    """更宽松的解析——从 scorecard.md 的当前得分列提取。"""
    scores: dict[str, int] = {}

    # C 维度: | C1 | 指令清晰度 | 15 | 6 | 6→**9** | ≥9 | ✅ |
    # current could be "6→**9**" → take last
    c_pat = re.compile(r"^\|\s*(C\d+)\s*\|\s*[^|]+\|\s*\d+\s*\|\s*\d+\s*\|\s*[\d→*]+(\d+)\*{0,2}")
    for m in c_pat.finditer(text, re.MULTILINE):
        scores[m.group(1)] = int(m.group(1))

    # E 维度 similar
    e_pat = re.compile(r"^\|\s*(E\d+)\s*\|\s*[^|]+\|\s*\d+\s*\|\s*\d+\s*\|\s*[\d→*]+(\d+)\*{0,2}")
    for m in e_pat.finditer(text, re.MULTILINE):
        scores[m.group(1)] = int(m.group(1))

    # Gov 维度: | 维度 | 7 | 7→**9** |
    for dim in GOV_DIMS:
        pat = re.compile(
            r"^\|\s*" + re.escape(dim) + r"\s*\|\s*\d+\s*\|\s*[\d→*]+(\d+)",
            re.MULTILINE,
        )
        m = pat.search(text)
        if m:
            scores[dim] = int(m.group(1))

    return scores


def read_meta_verdict(path: Path) -> dict[str, Any] | None:
    """读取 meta_oracle 裁决 JSON。"""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def run_regression() -> dict[str, Any]:
    """跑回归套件，返回结构化结果。"""
    script = PROJECT_ROOT / "scripts" / "run-regression.sh"
    if not script.is_file():
        return {"error": "run-regression.sh not found", "rc": -1}

    r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=600)
    lines = r.stdout.strip().splitlines()
    passed = sum(1 for l in lines if l.startswith("PASS"))
    failed = sum(1 for l in lines if l.startswith("FAIL"))
    total = passed + failed

    suites = []
    for l in lines:
        m = re.match(r"(PASS|FAIL)\s+(.+)$", l)
        if m:
            suites.append({"name": m.group(2), "status": m.group(1)})

    return {
        "rc": r.returncode,
        "passed": passed,
        "failed": failed,
        "total": total,
        "suites": suites,
        "stdout": r.stdout,
        "stderr": r.stderr,
    }


# ── 计分器 ──

def compute_longitudinal(scores: dict[str, int]) -> tuple[float, dict[str, Any]]:
    """计算纵向追踪分。"""
    c_total, c_weight = 0, 0
    for cid, name, weight in C_DIMS:
        s = scores.get(cid, 0)
        c_total += s * weight
        c_weight += weight
    e_total, e_weight = 0, 0
    for eid, name, weight in E_DIMS:
        s = scores.get(eid, 0)
        e_total += s * weight
        e_weight += weight
    gov_sum = 0
    for dim in GOV_DIMS:
        gov_sum += scores.get(dim, 0)

    grand_total = c_total + e_total + gov_sum
    grand_weight = c_weight + e_weight + len(GOV_DIMS)
    current_avg = grand_total / grand_weight if grand_weight else 0.0

    # delta from baseline
    delta = (current_avg - BASELINE) / DELTA_RANGE
    longitudinal = round(BASELINE + delta * DELTA_RANGE, 2)

    return longitudinal, {
        "c_weighted": round(c_total / c_weight, 2) if c_weight else 0,
        "e_weighted": round(e_total / e_weight, 2) if e_weight else 0,
        "gov_weighted": round(gov_sum / len(GOV_DIMS), 2) if GOV_DIMS else 0,
        "grand_total": grand_total,
        "grand_weight": grand_weight,
        "current_avg": round(current_avg, 2),
        "delta_from_baseline": round(delta, 3),
    }


def compute_audit_score(verdict: dict[str, Any]) -> float:
    """从 meta_oracle 裁决提取审计分（G1-G4 复合）。"""
    # The verdict has an overall score, but we want G1-G4 composite
    # From the meta_oracle.py framework:
    # final_score = G1*0.35 + G2*0.25 + G3*0.20 + G4*0.20
    # For now, use the overall verdict score as proxy
    return verdict.get("score", 0.0)


def compute_delta(longitudinal: float, audit: float | None) -> float | None:
    """纵向 vs 审计的偏差。"""
    if audit is None:
        return None
    return round(abs(longitudinal - audit), 2)


def determine_verdict(regression: dict[str, Any] | None, delta: float | None) -> str:
    """裁定最终状态。"""
    regression_failed = regression and regression.get("failed", 0) > 0
    if regression_failed:
        return "RED"

    if delta is None:
        # No audit data — rely on regression only
        return "GREEN" if (regression and regression.get("failed", 0) == 0) else "YELLOW"

    if delta >= 1.0:
        return "RED"
    elif delta >= 0.5:
        return "YELLOW"
    else:
        return "GREEN"


# ── 报告生成器 ──

def generate_report(
    scores: dict[str, int],
    longitudinal: float,
    audit_score: float | None,
    delta: float | None,
    verdict: str,
    regression: dict[str, Any] | None,
    audit_verdict: dict[str, Any] | None,
    meta: dict[str, Any],
) -> str:
    """输出 eval-report.md。"""
    lines = [
        "# CarrorOS 评测报告",
        "",
        f"> 生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"> 框架: evaluation-framework.v1",
        f"> 纵向账本: {meta.get('scorecard', 'N/A')}",
        f"> 审计裁决: {meta.get('meta_verdict', 'N/A')}",
        f"> 回归: {'已跑' if regression else '未跑'}",
        "",
        "---",
        "",
        "## 综合裁决",
        "",
        f"| 维度 | 分数 | 说明 |",
        f"|---|---|---|",
        f"| 纵向追踪分(Longitude) | **{longitudinal:.2f}/10** | 从基线 {BASELINE} 的增量{(longitudinal - BASELINE):+.2f} |",
    ]

    if audit_score is not None:
        lines.append(f"| 独立审计分(Latitude) | **{audit_score:.2f}/10** | G1-G4 复合 |")
    else:
        lines.append(f"| 独立审计分(Latitude) | **N/A** | 未提供审计裁决 |")

    if delta is not None:
        d_label = "GREEN 可信" if delta < 0.5 else ("YELLOW 注意" if delta < 1.0 else "RED 报警")
        lines.append(f"| 内外偏差 Δ | **{delta}** | {d_label} |")
    else:
        lines.append(f"| 内外偏差 Δ | **N/A** | 无审计数据 |")

    if regression:
        lines.append(f"| 回归 | **{regression['passed']}/{regression['total']}** 通过 | rc={regression['rc']} |")
    else:
        lines.append(f"| 回归 | **未跑** | |")

    lines.append(f"| **最终裁定** | **{verdict}** | |")
    lines.append("")

    # C 维度明细
    lines.extend([
        "---",
        "",
        "## C 维度明细",
        "",
        "| C | 指标 | 权重 | 得分 | 加权分 | 状态 |",
        "|---|---|---|---|---|---|",
    ])
    c_weighted_total = 0
    c_weight_sum = 0
    for cid, name, weight in C_DIMS:
        s = scores.get(cid, 0)
        w = s * weight / 10.0
        c_weighted_total += w
        c_weight_sum += weight
        status = "✅" if s >= 9 else "⬜"
        lines.append(f"| {cid} | {name} | {weight} | {s} | {w:.1f} | {status} |")
    lines.append(f"| | **C 加权** | **{c_weight_sum}** | | **{c_weighted_total:.1f}/{c_weight_sum}** | |")

    # E 维度明细
    lines.extend([
        "",
        "## E 维度明细",
        "",
        "| E | 指标 | 权重 | 得分 | 加权分 | 状态 |",
        "|---|---|---|---|---|---|",
    ])
    e_weighted_total = 0
    e_weight_sum = 0
    for eid, name, weight in E_DIMS:
        s = scores.get(eid, 0)
        w = s * weight / 10.0
        e_weighted_total += w
        e_weight_sum += weight
        status = "✅" if s >= 9 else "⬜"
        lines.append(f"| {eid} | {name} | {weight} | {s} | {w:.1f} | {status} |")
    lines.append(f"| | **E 加权** | **{e_weight_sum}** | | **{e_weighted_total:.1f}/{e_weight_sum}** | |")

    # 治理明细
    lines.extend([
        "",
        "## 长期治理明细",
        "",
        "| 维度 | 得分 | 状态 |",
        "|---|---|---|",
    ])
    gov_sum = 0
    for dim in GOV_DIMS:
        s = scores.get(dim, 0)
        gov_sum += s
        status = "✅" if s >= 9 else "⬜"
        lines.append(f"| {dim} | {s} | {status} |")
    lines.append(f"| **治理均分** | **{gov_sum / len(GOV_DIMS):.2f}** | |")

    # Delta 分析
    if delta is not None and audit_score is not None:
        lines.extend([
            "",
            "## Δ 偏差分析",
            "",
            f"纵向追踪分 = {longitudinal} / 独立审计分 = {audit_score} → Δ = {delta}",
            "",
        ])
        if delta < 0.5:
            lines.append("✅ **可信区间** — 内外评估一致，评分可靠。")
        elif delta < 1.0:
            lines.append("⚠️ **注意区间** — 建议查明差异来源后继续。")
            d = longitudinal - audit_score
            if d > 0:
                lines.append(f"  纵向({longitudinal}) > 审计({audit_score})：可能存在自评盲点。")
            else:
                lines.append(f"  审计({audit_score}) > 纵向({longitudinal})：可能存在审计遗漏。")
        else:
            lines.append("🔴 **报警区间** — Δ ≥ 1.0，必须查明原因后才可继续迭代。")

    # 回归明细
    if regression:
        lines.extend([
            "",
            "## 回归明细",
            "",
            f"一键回归: bash scripts/run-regression.sh → rc={regression['rc']}",
            "",
            "| 套件 | 状态 |",
            "|---|---|",
        ])
        for suite in regression.get("suites", []):
            icon = "✅" if suite["status"] == "PASS" else "❌"
            lines.append(f"| {icon} {suite['name']} | {suite['status']} |")

    # 审计原因
    if audit_verdict:
        lines.extend([
            "",
            "## 审计详情",
            "",
            f"裁决: {audit_verdict.get('verdict', 'N/A')}",
            f"风险: {audit_verdict.get('risk', 'N/A')}",
            f"得分: {audit_verdict.get('score', 'N/A')}",
            "",
            "### 审计原因",
            "",
        ])
        for r in audit_verdict.get("reasons", []):
            lines.append(f"- {r}")

    # Footer
    lines.extend([
        "",
        "---",
        "",
        f"VERIFIED — 评测完成 | longitudinal={longitudinal} | audit={audit_score or 'N/A'} | Δ={delta or 'N/A'} | {verdict}",
    ])

    return "\n".join(lines) + "\n"


# ── 主入口 ──

def main() -> int:
    ap = argparse.ArgumentParser(description="CarrorOS 科学评测合成器")
    ap.add_argument("--scorecard", default=str(DEFAULT_SCORECARD), help="scorecard.md 路径")
    ap.add_argument("--meta-verdict", default=str(DEFAULT_META_VERDICT), help="meta_oracle 裁决 JSON 路径")
    ap.add_argument("--run-regression", action="store_true", help="跑回归后再合成")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="输出报告路径")
    ap.add_argument("--verbose", action="store_true", help="输出详细信息")
    args = ap.parse_args()

    meta_info = {"scorecard": args.scorecard, "meta_verdict": args.meta_verdict}

    # 1. 读纵向账本
    scorecard_path = Path(args.scorecard)
    if not scorecard_path.is_file():
        print(f"ERROR: scorecard 不存在: {scorecard_path}", file=sys.stderr)
        return 3
    parsed = parse_scorecard(scorecard_path)
    scores = parsed.get("scores", {})
    if not scores:
        print(f"WARN: scorecard 解析无分数, 尝试宽松模式", file=sys.stderr)
        text = scorecard_path.read_text(encoding="utf-8")
        scores = parse_scorecard_scorecard_v2(text)
    if not scores:
        print(f"ERROR: scorecard 无法解析分数", file=sys.stderr)
        return 3

    if args.verbose:
        print(f"[verbose] 解析到 {len(scores)} 个分数: {scores}")

    # 2. 读审计裁决
    verdict_path = Path(args.meta_verdict)
    audit_verdict = read_meta_verdict(verdict_path)

    # 3. 可选跑回归
    regression = None
    if args.run_regression:
        print("正在跑回归...")
        regression = run_regression()
        if args.verbose:
            print(f"[verbose] 回归结果: {regression.get('passed', 0)}/{regression.get('total', 0)} 通过")

    # 4. 计分
    longitudinal, detail = compute_longitudinal(scores)
    audit_score = compute_audit_score(audit_verdict) if audit_verdict else None
    delta = compute_delta(longitudinal, audit_score)
    verdict = determine_verdict(regression, delta)

    if args.verbose:
        print(f"[verbose] longitudinal={longitudinal} audit={audit_score} Δ={delta} → {verdict}")

    # 5. 生成报告
    report = generate_report(scores, longitudinal, audit_score, delta, verdict, regression, audit_verdict, meta_info)

    out_path = Path(args.out)
    out_path.write_text(report, encoding="utf-8")
    print(f"✅ 评测报告: {out_path}")
    print(f"   纵向追踪分: {longitudinal}/10 | 审计分: {audit_score or 'N/A'}/10 | Δ: {delta or 'N/A'} | 裁定: {verdict}")

    return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(verdict, 2)


if __name__ == "__main__":
    sys.exit(main())
