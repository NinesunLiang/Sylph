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
