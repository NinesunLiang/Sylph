#!/usr/bin/env python3
"""Aggregate scorecard and local evaluation readiness into a fail-closed report."""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_SCORES = ("c_weighted", "e_weighted", "total_weighted")
VALID_VERDICTS = {"PASS", "WARN", "BLOCKED", "FAIL"}
CERTIFICATION_THRESHOLD = 8.6
ITEM_THRESHOLD = 8.0  # per-item certification gate: 24 items all >= 8.0
ARITH_TOLERANCE = 0.05
EXPECTED_MANIFEST_ITEMS = (
    [f"C{i}" for i in range(1, 10)]
    + [f"E{i}" for i in range(1, 9)]
    + [f"G{i}" for i in range(1, 8)]
)


def parse_item_manifest(text: str) -> tuple[list[dict], dict]:
    """Parse the canonical `## Item Manifest` section from a scorecard.

    Expected format:

        ## Item Manifest

        > freshness: <date> | commit: <hash> | task: <task-id>

        | id | weight | score |
        | C1 | 15 | 9 |
        | E1 | 20 | 8 |
        | G1 | 0 | 8 |
        ...

    Returns (items, meta) where meta carries freshness/commit/task binding.
    """
    items: list[dict] = []
    meta: dict[str, str] = {}
    match = re.search(r"^## Item Manifest\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return items, meta
    section = match.group(1)
    meta_match = re.search(
        r">\s*freshness:\s*(\S+)[^\n]*commit:\s*(\S+)[^\n]*task:\s*(\S+)",
        section,
    )
    if meta_match:
        meta = {
            "freshness": meta_match.group(1),
            "commit": meta_match.group(2),
            "task": meta_match.group(3),
        }
    for row in re.finditer(
        r"^\|\s*(C\d+|E\d+|G\d+|U\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|",
        section,
        re.MULTILINE,
    ):
        items.append({
            "id": row.group(1),
            "weight": int(row.group(2)),
            "score": float(row.group(3)),
        })
    return items, meta


def validate_item_manifest(items: list[dict], scores: dict) -> list[dict]:
    """Validate the item manifest against the 24-item >=8.0 gate and arithmetic.

    Returns readiness blocker items.
    """
    blockers: list[dict] = []
    ids = [it["id"] for it in items]
    missing = [item_id for item_id in EXPECTED_MANIFEST_ITEMS if item_id not in ids]
    if missing:
        blockers.append(_item(
            "scorecard.item_manifest_incomplete", "evidence", "blocker",
            f"missing: {', '.join(missing)}",
        ))

    below: list[str] = []
    out_of_range: list[str] = []
    for it in items:
        if not 0 <= it["score"] <= 10:
            out_of_range.append(f"{it['id']}={it['score']}")
        elif it["score"] < ITEM_THRESHOLD:
            below.append(f"{it['id']}={it['score']}")
    if out_of_range:
        blockers.append(_item("scorecard.item_manifest_range", "evidence", "blocker", "; ".join(out_of_range)))
    if below:
        blockers.append(_item("scorecard.item_below_threshold", "evidence", "blocker", "; ".join(below)))

    def weighted(prefix: str) -> float | None:
        selected = [it for it in items if it["id"].startswith(prefix) and it["weight"] > 0]
        if not selected:
            return None
        total_w = sum(it["weight"] for it in selected)
        return sum(it["score"] * it["weight"] for it in selected) / total_w

    c_recomputed = weighted("C")
    e_recomputed = weighted("E")
    if c_recomputed is not None and "c_weighted" in scores and abs(c_recomputed - scores["c_weighted"]) > ARITH_TOLERANCE:
        blockers.append(_item(
            "scorecard.arithmetic_mismatch", "evidence", "blocker",
            f"C weighted recomputed={c_recomputed:.2f} declared={scores['c_weighted']}",
        ))
    if e_recomputed is not None and "e_weighted" in scores and abs(e_recomputed - scores["e_weighted"]) > ARITH_TOLERANCE:
        blockers.append(_item(
            "scorecard.arithmetic_mismatch", "evidence", "blocker",
            f"E weighted recomputed={e_recomputed:.2f} declared={scores['e_weighted']}",
        ))
    # 长期治理（G1-G7）算术：无权重算术平均，与声明的 平均 比对（P2-9, index12 S6）
    g_items = [it for it in items if it["id"].startswith("G")]
    if g_items and "g_weighted" in scores:
        g_mean = sum(it["score"] for it in g_items) / len(g_items)
        if abs(g_mean - scores["g_weighted"]) > ARITH_TOLERANCE:
            blockers.append(_item(
                "scorecard.arithmetic_mismatch", "evidence", "blocker",
                f"G mean recomputed={g_mean:.2f} declared={scores['g_weighted']}",
            ))
    # UX（U1-U7）算术：独立 proxy，校验但绝不成为认证 blocker（index13 S6）
    u_items = [it for it in items if it["id"].startswith("U")]
    if u_items and "ux_weighted" in scores:
        u_mean = sum(it["score"] for it in u_items) / len(u_items)
        if abs(u_mean - scores["ux_weighted"]) > ARITH_TOLERANCE:
            blockers.append(_item(
                "scorecard.ux_arithmetic_mismatch", "evidence", "informational",
                f"UX mean recomputed={u_mean:.2f} declared={scores['ux_weighted']}",
            ))
    return blockers


def parse_scorecard(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    result: dict[str, float] = {}
    patterns = {
        "c_weighted": r"C1-C9.*加权.*?([\d.]+)",
        "e_weighted": r"E1-E8.*加权.*?([\d.]+)",
        "total_weighted": r"24 ?项总加权.*?([\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            result[key] = float(match.group(1))
    # g_weighted (E13-003, index13 S6): anchor on the 平均 ROW (table cell or inline
    # value) rather than the heading "长期治理能力（7 项算术平均）". The old
    # `(?s)长期治理.*?平均.*?([\d.]+)` captured the first numeric cell (抗衰减防线)
    # because the heading itself contains "平均".
    g_match = (
        re.search(
            r"\|\s*\*?\*?平均\*?\*?\s*\|\s*(?:[^|\n]*\|\s*)?\*?\*?([\d.]+)\*?\*?\s*\|",
            text,
        )
        or re.search(r"长期治理[^\n]*平均\s*([\d.]+)", text)
    )
    if g_match:
        result["g_weighted"] = float(g_match.group(1))
    # UX (index13 S6): independent proxy mean. Supports table row
    # `| UX 独立 proxy | **7.00 / 10** |` and inline `UX 独立 proxy 平均 7.00`.
    ux_match = (
        re.search(r"\|\s*UX[^\n]*proxy[^\n]*\|\s*\*?\*?([\d.]+)\s*/\s*10\*?\*?\s*\|", text)
        or re.search(r"UX[^\n]*平均\s*([\d.]+)", text)
    )
    if ux_match:
        result["ux_weighted"] = float(ux_match.group(1))
    return result


def _valid_verdict(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    verdict = str(data.get("verdict", data.get("status", ""))).upper()
    score = data.get("score")
    return verdict in VALID_VERDICTS and isinstance(score, (int, float))


def parse_oracle_verdicts(dir_path: Path) -> tuple[list[dict], list[str]]:
    verdicts = []
    invalid = []
    if not dir_path.is_dir():
        return verdicts, invalid
    for sub in sorted(dir_path.iterdir()):
        if not sub.is_dir():
            continue
        v_file = sub / "verdict.json"
        if not v_file.exists():
            continue
        try:
            data = json.loads(v_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            invalid.append(f"{sub.name}:malformed")
            continue
        if not _valid_verdict(data):
            invalid.append(f"{sub.name}:invalid")
            continue
        verdicts.append({"dir": sub.name, **data})
    return verdicts, invalid


def _item(item_id: str, category: str, severity: str, reason: str) -> dict:
    return {"id": item_id, "category": category, "severity": severity, "reason": reason}


def collect_readiness(scorecard_path: Path, oracle_dir: Path, project_root: Path) -> list[dict]:
    scores = parse_scorecard(scorecard_path)
    verdicts, invalid = parse_oracle_verdicts(oracle_dir)
    items = []

    missing_scores = [key for key in REQUIRED_SCORES if key not in scores]
    if missing_scores:
        items.append(_item("scorecard.incomplete", "evidence", "blocker", f"missing: {', '.join(missing_scores)}"))
    for key, value in scores.items():
        if not 0 <= value <= 10:
            items.append(_item("scorecard.range", "evidence", "blocker", f"{key}={value} outside 0..10"))
            break
    below_threshold = [key for key in REQUIRED_SCORES if key in scores and scores[key] < CERTIFICATION_THRESHOLD]
    if below_threshold:
        items.append(_item("scorecard.threshold", "evidence", "blocker", f"below {CERTIFICATION_THRESHOLD}: {', '.join(below_threshold)}"))

    # Item-level 24-dim manifest: the aggregate alone cannot certify the gate
    # "24 items all >= 8.0"; a machine-parseable manifest is required.
    manifest_text = scorecard_path.read_text(encoding="utf-8") if scorecard_path.exists() else ""
    manifest_items, manifest_meta = parse_item_manifest(manifest_text)
    if not manifest_items:
        items.append(_item("scorecard.item_manifest_missing", "evidence", "blocker", "no item-level 24-dim manifest"))
    else:
        items.extend(validate_item_manifest(manifest_items, scores))
        if not manifest_meta.get("commit") or not manifest_meta.get("task"):
            items.append(_item("scorecard.manifest_unbound", "evidence", "blocker", "manifest missing commit/task binding"))

    verdict_names = [str(verdict.get("verdict", verdict.get("status", ""))).upper() for verdict in verdicts]
    if not verdicts:
        items.append(_item("oracle.missing", "evidence", "blocker", "no valid fresh Oracle verdict"))
    elif any(name in {"FAIL", "BLOCKED"} for name in verdict_names):
        item_id = "oracle.conflict" if "PASS" in verdict_names else "oracle.rejected"
        items.append(_item(item_id, "evidence", "blocker", "fresh Oracle verdicts contain FAIL/BLOCKED"))
    elif "PASS" not in verdict_names:
        items.append(_item("oracle.no_approved_pass", "evidence", "blocker", "no fresh PASS Oracle verdict"))
    if invalid:
        items.append(_item("oracle.invalid", "evidence", "blocker", "; ".join(invalid)))

    regression = project_root / "scripts" / "run-regression.sh"
    if not regression.exists():
        items.append(_item("regression.entrypoint.missing", "coverage", "blocker", str(regression)))
    else:
        text = regression.read_text(encoding="utf-8", errors="replace")
        referenced_paths = sorted(set(re.findall(r"((?:scripts|tests)/test[-_][A-Za-z0-9_.-]+\.(?:py|sh))", text)))
        missing = [path for path in referenced_paths if not (project_root / path).exists() and not (project_root / ".claude" / path).exists()]
        if missing:
            items.append(_item("regression.entrypoint.drift", "coverage", "blocker", ", ".join(missing)))

    goal_e2e = project_root / ".claude" / "skills" / "lx-goal" / "scripts" / "test_goal_lifecycle_e2e.py"
    if not goal_e2e.exists():
        items.append(_item("goal.e2e.missing", "lifecycle", "blocker", "complete plan-token-handoff-resume-done/off fixture missing"))

    subagent_matrix = project_root / ".claude" / "scripts" / "test_sub_agent_failure_matrix.py"
    if not subagent_matrix.exists():
        items.append(_item("subagent.matrix.missing", "recovery", "blocker", "offline failure matrix missing"))

    for item_id, reason in (
        ("runtime.network.unexecuted", "network worker intentionally not run"),
        ("credentials.unexecuted", "credential paths intentionally not read"),
        ("ci.install.unexecuted", "CI package installation intentionally not run"),
        ("destructive.unexecuted", "destructive state operations intentionally not run"),
    ):
        items.append(_item(item_id, "boundary", "informational", reason))
    return items


def render_benchmark(scores: dict, readiness: list[dict], certification: str, output_path: Path) -> None:
    lines = [
        "---",
        "type: benchmark-report",
        "schema_version: benchmark-report.v1",
        f"status: {certification.lower().replace(' / ', '-')}",
        "---",
        "",
        "# CarrorOS 治理效能 Benchmark",
        "",
        f"> Certification: **{certification}**（由 readiness 自动派生）",
        "",
        "## 评分",
        "",
        "| 维度 | 分数 |",
        "|---|---:|",
        f"| C1-C9 能力加权 | {scores.get('c_weighted', '?')} |",
        f"| E1-E8 错误防护 | {scores.get('e_weighted', '?')} |",
        f"| 24 项总加权 | {scores.get('total_weighted', '?')} |",
        "",
        "## 未认证项（自动派生）",
        "",
    ]
    lines.extend(
        f"- `{item['id']}` [{item['severity']}] {item['reason']}"
        for item in readiness
    )
    if not readiness:
        lines.append("- 无")
    lines.extend([
        "",
        "## 认证边界",
        "",
        "- 报告事实源为本次 eval-aggregate 输入和 readiness JSON。",
        "- 网络、凭据、CI 安装和破坏性入口不会被自动执行；未执行状态保留为 informational。",
        "- Oracle 缺失、回归入口漂移、Goal E2E 缺失或 SubAgent 矩阵缺失时不得 CERTIFIED。",
        "",
        "## 复现",
        "",
        "```text",
        "python3 .claude/scripts/eval-aggregate.py --scorecard <scorecard> --meta-verdict <oracle-dir> --output <eval-report>",
        "```",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def aggregate(scorecard_path: Path, oracle_dir: Path, output_path: Path, project_root: Path | None = None, benchmark_output: Path | None = None) -> int:
    project_root = project_root or Path(__file__).resolve().parents[2]
    scores = parse_scorecard(scorecard_path)
    verdicts, _ = parse_oracle_verdicts(oracle_dir)
    readiness = collect_readiness(scorecard_path, oracle_dir, project_root)
    blockers = [item for item in readiness if item["severity"] == "blocker"]
    certification = "CERTIFIED" if scores.keys() >= set(REQUIRED_SCORES) and verdicts and not blockers else "PROVISIONAL / NOT_CERTIFIED"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# Eval Report — {now}",
        "",
        f"## Certification: **{certification}**",
        "",
        "认证状态由 scorecard、有效 Oracle verdict 和 readiness checks 派生，禁止手写覆盖。",
        "",
        "## 评分解读",
        "",
        "| 维度 | 分数 |",
        "|------|:----:|",
        f"| C1-C9 加权 | **{scores.get('c_weighted', '?')}** |",
        f"| E1-E8 加权 | **{scores.get('e_weighted', '?')}** |",
        f"| 24项总加权 | **{scores.get('total_weighted', '?')}** |",
        "",
        "## 分歧分析",
        "",
        f"Oracle 评审记录: {len(verdicts)} 条",
        "",
        "## 未认证项（自动派生）",
        "",
    ]
    if readiness:
        lines.extend(f"- `{item['id']}` [{item['severity']}] {item['reason']}" for item in readiness)
    else:
        lines.append("- 无")
    lines.extend(["", "## 下轮建议", "", "详见 .claude/references/archived/design-docs/r8-convergence-plan.md（历史迭代，ADR0017 归档）", "", "---", f"> 由 eval-aggregate.py 于 {now} 生成"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    readiness_path = output_path.with_suffix(".readiness.json")
    readiness_path.write_text(json.dumps({"certification": certification, "items": readiness}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if benchmark_output:
        render_benchmark(scores, readiness, certification, benchmark_output)
    print(f"✅ Eval report: {output_path}")
    return 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    sc_path = root / ".claude" / "references" / "scorecard.md"
    oracle_path = root / ".omc" / "state" / "oracle"
    out_path = root / ".omc" / "state" / "eval-report.md"
    benchmark_path = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--scorecard" and i + 1 < len(sys.argv):
            sc_path = Path(sys.argv[i + 1]); i += 2
        elif sys.argv[i] == "--meta-verdict" and i + 1 < len(sys.argv):
            oracle_path = Path(sys.argv[i + 1]); i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            out_path = Path(sys.argv[i + 1]); i += 2
        elif sys.argv[i] == "--benchmark-output" and i + 1 < len(sys.argv):
            benchmark_path = Path(sys.argv[i + 1]); i += 2
        else:
            i += 1
    sys.exit(aggregate(sc_path, oracle_path, out_path, benchmark_output=benchmark_path))
