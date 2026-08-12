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
    assert "`goal.e2e.missing`" in report
    assert "`regression.entrypoint.drift`" in report


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
