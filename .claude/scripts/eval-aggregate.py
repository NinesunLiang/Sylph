#!/usr/bin/env python3
"""Aggregate scorecard and local evaluation readiness into a fail-closed report."""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_SCORES = ("c_weighted", "e_weighted", "total_weighted")
VALID_VERDICTS = {"PASS", "WARN", "BLOCKED", "FAIL"}


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

    if not verdicts:
        items.append(_item("oracle.missing", "evidence", "blocker", "no valid fresh Oracle verdict"))
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
    lines.extend(["", "## 下轮建议", "", "详见 .claude/references/design-docs/r8-convergence-plan.md", "", "---", f"> 由 eval-aggregate.py 于 {now} 生成"])
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
