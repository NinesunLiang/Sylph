import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "eval-aggregate.py"
spec = importlib.util.spec_from_file_location("eval_aggregate_under_test", SCRIPT)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_aggregate_marks_missing_oracle_provisional(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text("C1-C9 加权 7.71\nE1-E8 加权 7.68\n24 项总加权 7.67\n")
    output = tmp_path / "report.md"
    benchmark = tmp_path / "Benchmarking" / "index.md"

    assert module.aggregate(scorecard, tmp_path / "oracle", output, benchmark_output=benchmark) == 0
    report = output.read_text()

    assert "PROVISIONAL / NOT_CERTIFIED" in report
    assert "Oracle 评审记录: 0 条" in report
    assert "`oracle.missing`" in report
    assert output.with_suffix(".readiness.json").exists()
    assert "未认证项（自动派生）" in benchmark.read_text()


def test_aggregate_marks_verdict_backed_scores_certified(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text("C1-C9 加权 8.9\nE1-E8 加权 8.8\n24 项总加权 8.85\n")
    oracle = tmp_path / "oracle" / "run-1"
    oracle.mkdir(parents=True)
    (oracle / "verdict.json").write_text(json.dumps({"verdict": "PASS", "score": 8.9}))
    output = tmp_path / "report.md"

    assert module.aggregate(scorecard, tmp_path / "oracle", output) == 0
    report = output.read_text()

    assert "Certification: **PROVISIONAL / NOT_CERTIFIED**" in report
    assert "Oracle 评审记录: 1 条" in report
    assert "`scorecard.item_manifest_missing`" in report
    # P0-6 canonical regression entrypoint no longer drifts
    assert "`regression.entrypoint.drift`" not in report
    # P0-1 Goal lifecycle E2E fixture exists, so goal.e2e.missing is gone
    assert "`goal.e2e.missing`" not in report


def make_certification_ready_project(tmp_path):
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / ".claude/skills/lx-goal/scripts").mkdir(parents=True)
    (project / ".claude/scripts").mkdir(parents=True)
    (project / "scripts/run-regression.sh").write_text("#!/bin/sh\n")
    (project / ".claude/skills/lx-goal/scripts/test_goal_lifecycle_e2e.py").write_text("# fixture\n")
    (project / ".claude/scripts/test_sub_agent_failure_matrix.py").write_text("# fixture\n")
    return project


def test_warn_oracle_never_certifies(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text("C1-C9 加权 9.0\nE1-E8 加权 9.0\n24 项总加权 9.0\n")
    oracle = tmp_path / "oracle" / "run-1"
    oracle.mkdir(parents=True)
    (oracle / "verdict.json").write_text(json.dumps({"verdict": "WARN", "score": 9.0}))
    output = tmp_path / "report.md"
    project = make_certification_ready_project(tmp_path)

    assert module.aggregate(scorecard, oracle.parent, output, project_root=project) == 0
    report = output.read_text()
    assert "PROVISIONAL / NOT_CERTIFIED" in report
    assert "`oracle.no_approved_pass`" in report


def test_scores_below_certification_threshold_stay_provisional(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text("C1-C9 加权 8.5\nE1-E8 加权 8.5\n24 项总加权 8.5\n")
    oracle = tmp_path / "oracle" / "run-1"
    oracle.mkdir(parents=True)
    (oracle / "verdict.json").write_text(json.dumps({"verdict": "PASS", "score": 9.0}))
    output = tmp_path / "report.md"
    project = make_certification_ready_project(tmp_path)

    assert module.aggregate(scorecard, oracle.parent, output, project_root=project) == 0
    report = output.read_text()
    assert "PROVISIONAL / NOT_CERTIFIED" in report
    assert "`scorecard.threshold`" in report


def test_conflicting_oracle_verdicts_block_certification(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text("C1-C9 加权 9.0\nE1-E8 加权 9.0\n24 项总加权 9.0\n")
    oracle = tmp_path / "oracle"
    for name, verdict in (("run-pass", "PASS"), ("run-fail", "FAIL")):
        run = oracle / name
        run.mkdir(parents=True)
        (run / "verdict.json").write_text(json.dumps({"verdict": verdict, "score": 9.0}))
    output = tmp_path / "report.md"
    project = make_certification_ready_project(tmp_path)

    assert module.aggregate(scorecard, oracle, output, project_root=project) == 0
    report = output.read_text()

    assert "PROVISIONAL / NOT_CERTIFIED" in report
    assert "`oracle.conflict`" in report


def test_invalid_oracle_is_not_silently_certified(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text("C1-C9 加权 8.9\nE1-E8 加权 8.8\n24 项总加权 8.85\n")
    oracle = tmp_path / "oracle" / "run-1"
    oracle.mkdir(parents=True)
    (oracle / "verdict.json").write_text(json.dumps({"verdict": "UNKNOWN"}))
    output = tmp_path / "report.md"

    assert module.aggregate(scorecard, oracle.parent, output) == 0
    report = output.read_text()

    assert "PROVISIONAL / NOT_CERTIFIED" in report
    assert "`oracle.invalid`" in report


# ── item-level 24-dim score manifest (P0-2) ─────────────────────────

C_WEIGHTS = {"C1": 15, "C2": 15, "C3": 15, "C4": 10, "C5": 10, "C6": 10, "C7": 10, "C8": 10, "C9": 10}
E_WEIGHTS = {"E1": 20, "E2": 20, "E3": 15, "E4": 12, "E5": 10, "E6": 13, "E7": 10, "E8": 10}


def item_rows(score=8.0, overrides=None):
    overrides = overrides or {}
    rows = []
    for cid, w in C_WEIGHTS.items():
        rows.append(f"| {cid} | {w} | {overrides.get(cid, score)} |")
    for eid, w in E_WEIGHTS.items():
        rows.append(f"| {eid} | {w} | {overrides.get(eid, score)} |")
    for gid in range(1, 8):
        rows.append(f"| G{gid} | 0 | {overrides.get(f'G{gid}', score)} |")
    return "\n".join(rows)


def manifest_text(score=8.0, overrides=None, bound=True):
    binding = "> freshness: 2026-08-12 | commit: abc123 | task: t-1\n\n" if bound else ""
    return (
        "## Item Manifest\n\n"
        f"{binding}"
        "| id | weight | score |\n"
        "|----|--------|-------|\n"
        f"{item_rows(score, overrides)}\n"
    )


def manifest_scorecard(text):
    return text + "C1-C9 加权 8.0\nE1-E8 加权 8.0\n24 项总加权 8.0\n"


def test_manifest_missing_is_blocker(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text("C1-C9 加权 8.9\nE1-E8 加权 8.8\n24 项总加权 8.85\n")

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    assert any(i["id"] == "scorecard.item_manifest_missing" and i["severity"] == "blocker"
               for i in items)


def test_parse_item_manifest_reads_all_24_items():
    items, meta = module.parse_item_manifest(manifest_text())

    assert len(items) == 24
    assert meta == {"freshness": "2026-08-12", "commit": "abc123", "task": "t-1"}


def test_manifest_item_below_threshold_is_blocker(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(manifest_scorecard(manifest_text(overrides={"C5": 7.0})))

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    assert any(i["id"] == "scorecard.item_below_threshold" and "C5" in i["reason"]
               for i in items)


def test_manifest_arithmetic_mismatch_is_blocker(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(manifest_text() + "C1-C9 加权 9.0\nE1-E8 加权 8.0\n24 项总加权 8.5\n")

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    assert any(i["id"] == "scorecard.arithmetic_mismatch" for i in items)


def test_manifest_g_arithmetic_mismatch_is_blocker(tmp_path):
    # index12 S6 / P2-9: long-term governance (G1-G7) arithmetic mean must match
    # the declared 平均 when the scorecard declares one.
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(
        manifest_text()
        + "C1-C9 加权 8.0\nE1-E8 加权 8.0\n24 项总加权 8.0\n长期治理 平均 9.0\n"
    )

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    assert any(i["id"] == "scorecard.arithmetic_mismatch" and "G mean" in i["reason"]
               for i in items)


def test_manifest_g_arithmetic_match_adds_no_blocker(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(
        manifest_text()
        + "C1-C9 加权 8.0\nE1-E8 加权 8.0\n24 项总加权 8.0\n长期治理 平均 8.0\n"
    )

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    assert not any("G mean" in i["reason"] for i in items)


def test_parse_scorecard_g_weighted_from_table_format():
    # E13-003 (index13 S6): the g_weighted regex `(?s)长期治理.*?平均.*?([\d.]+)`
    # anchored on the heading "长期治理能力（7 项算术平均）" and captured the FIRST
    # numeric cell in the table (抗衰减防线 score) instead of the 平均 row value.
    # Real scorecards are Markdown tables, so this must parse the `| 平均 | 7.57 |` row.
    text = (
        "# Scorecard\n"
        "## 长期治理能力（7 项算术平均）\n"
        "| 维度 | 得分 |\n"
        "|---|---:|\n"
        "| 抗衰减防线 | 8 |\n"
        "| AI 赋能的全流程自动化 | 7 |\n"
        "| 学习笔记积累 | 8 |\n"
        "| 长期目标一致性 | 7 |\n"
        "| 功能标志分明 | 7 |\n"
        "| 内置安全与洞察 | 8 |\n"
        "| Evaluation 评测框架 | 8 |\n"
        "| **平均** | **7.57** |\n"
        "# real-world 3-col (index13): 平均 row with an empty 评估依据 column\n"
        "| **平均** | | **7.57** | 独立 proxy |\n"
    )
    scores = module.parse_scorecard(Path("/dev/null"))
    # inject via a real path
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(text)
        path = Path(fh.name)
    try:
        scores = module.parse_scorecard(path)
        assert abs(scores["g_weighted"] - 7.57) < 0.01, f"g_weighted={scores.get('g_weighted')}"
    finally:
        path.unlink(missing_ok=True)


def test_manifest_unbound_is_blocker(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(manifest_scorecard(manifest_text(bound=False)))

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    assert any(i["id"] == "scorecard.manifest_unbound" and i["severity"] == "blocker"
               for i in items)


def test_valid_manifest_adds_no_item_blocker(tmp_path):
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(manifest_scorecard(manifest_text()))

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    assert not any(i["id"].startswith("scorecard.item_") for i in items)


UX_SCORECARD = (
    "## UX 独立 proxy（7 项算术平均，非人类研究）\n"
    "| 维度 | 得分 |\n"
    "|---|---:|\n"
    "| 长期目标一致性 | 7 |\n"
    "| 用户心智负担减轻 | 6 |\n"
    "| 交互现代化 | 6 |\n"
    "| 用户掌控感 | 8 |\n"
    "| ai 智能感 | 7 |\n"
    "| 行为可预测 | 7 |\n"
    "| 人机权限分明 | 8 |\n"
    "| **平均** | **7.00** |\n"
    "## Item Manifest\n\n"
    "> freshness: 2026-08-12 | commit: abc123 | task: t-1\n\n"
    "| id | weight | score |\n"
    "|----|--------|-------|\n"
    + "\n".join([f"| U{i} | 0 | {v} |" for i, v in enumerate([7, 6, 6, 8, 7, 7, 8], start=1)])
    + "\n"
)


def test_parse_item_manifest_reads_ux_items():
    # index13 S6: UX items (U1-U7) should be parseable when a scorecard includes them.
    items, meta = module.parse_item_manifest(UX_SCORECARD)

    u_items = [it for it in items if it["id"].startswith("U")]
    assert len(u_items) == 7, f"expected 7 UX items, got {len(u_items)}"
    assert [it["score"] for it in u_items] == [7, 6, 6, 8, 7, 7, 8]


def test_ux_mean_validation_informational_not_blocker(tmp_path):
    # UX is an independent proxy; its arithmetic mean must be checked but must NOT
    # become a certification blocker (UX does not gate the 24-item C/E/G threshold).
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(UX_SCORECARD + "C1-C9 加权 8.0\nE1-E8 加权 8.0\n24 项总加权 8.0\nUX 独立 proxy 平均 7.00\n")

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    # UX mean is validated as informational, never a blocker
    assert not any(i["severity"] == "blocker" and "UX" in i.get("reason", "") for i in items)
    assert not any(i["id"] == "scorecard.ux_arithmetic_mismatch" and i["severity"] == "blocker" for i in items)


def test_ux_mean_mismatch_is_informational_not_blocker(tmp_path):
    # A UX arithmetic mismatch (mean 7.00 declared, items average 7.14) must surface
    # as informational only — it must not flip certification status.
    scorecard = tmp_path / "scorecard.md"
    scorecard.write_text(
        "## UX 独立 proxy（7 项算术平均，非人类研究）\n"
        "| 维度 | 得分 |\n"
        "|---|---:|\n"
        "| 长期目标一致性 | 7 |\n"
        "| 用户心智负担减轻 | 6 |\n"
        "| 交互现代化 | 6 |\n"
        "| 用户掌控感 | 8 |\n"
        "| ai 智能感 | 7 |\n"
        "| 行为可预测 | 8 |\n"
        "| 人机权限分明 | 8 |\n"
        "| **平均** | **7.00** |\n"
        "## Item Manifest\n\n"
        "> freshness: 2026-08-12 | commit: abc123 | task: t-1\n\n"
        "| id | weight | score |\n"
        "|----|--------|-------|\n"
        "| U1 | 0 | 7 |\n"
        "| U2 | 0 | 6 |\n"
        "| U3 | 0 | 6 |\n"
        "| U4 | 0 | 8 |\n"
        "| U5 | 0 | 7 |\n"
        "| U6 | 0 | 8 |\n"
        "| U7 | 0 | 8 |\n"
        "C1-C9 加权 8.0\nE1-E8 加权 8.0\n24 项总加权 8.0\nUX 独立 proxy 平均 7.00\n"
    )

    items = module.collect_readiness(scorecard, tmp_path / "oracle", tmp_path)

    mismatch = [i for i in items if i["id"] == "scorecard.ux_arithmetic_mismatch"]
    assert mismatch, "UX arithmetic mismatch should be reported"
    assert mismatch[0]["severity"] == "informational"
    assert all(i["severity"] != "blocker" for i in items if "UX" in i.get("reason", ""))
