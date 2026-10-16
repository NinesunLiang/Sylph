"""Tests for the one-shot JEV feedback bridge."""
from __future__ import annotations

import json
from pathlib import Path

from jev_feedback import emit_feedback


def _checklist(path: Path, **summary):
    path.write_text(json.dumps({"summary": summary}), encoding="utf-8")


def test_feedback_emits_once_and_requests_one_review(tmp_path):
    checklist = tmp_path / "checklist.json"
    _checklist(checklist, violated=["soul.1.simple"], insufficient=[], undecided=[],
               escalate_for_rule_tuning=[])
    first = emit_feedback(checklist, tmp_path / "out", "task-a", "S1")
    second = emit_feedback(checklist, tmp_path / "out", "task-a", "S1")
    assert first == second
    assert first["one_shot"] is True
    assert first["needs_review"] is True
    assert first["llm_decision"] == "pending"


def test_feedback_marks_unavailable_run_for_review(tmp_path):
    checklist = tmp_path / "checklist.json"
    _checklist(checklist, violated=[], insufficient=[], undecided=[],
               unavailable=["rule-x"], escalate_for_rule_tuning=[])
    result = emit_feedback(checklist, tmp_path / "out", "task-unavailable", "S1")
    assert result["needs_review"] is True


def test_feedback_includes_project_candidates_as_feedback_only(tmp_path):
    checklist = tmp_path / "checklist.json"
    _checklist(checklist, violated=[], insufficient=[], undecided=[],
               unavailable=[], escalate_for_rule_tuning=[])
    candidates = tmp_path / "candidates.json"
    candidates.write_text(json.dumps({"candidates": [{
        "candidate_id": "project.demo", "source": "README.md:1",
        "text": "项目规则", "enforcement": "feedback_only",
    }]}), encoding="utf-8")
    result = emit_feedback(checklist, tmp_path / "out", "task-project", "S1", candidates)
    assert result["project_rule_candidates"]["count"] == 1
    assert result["project_rule_candidates"]["candidates"][0]["enforcement"] == "feedback_only"


def test_feedback_stays_quiet_when_clean(tmp_path):
    checklist = tmp_path / "checklist.json"
    _checklist(checklist, violated=[], insufficient=[], undecided=[],
               escalate_for_rule_tuning=[])
    result = emit_feedback(checklist, tmp_path / "out", "task-b", "S1")
    assert result["needs_review"] is False
    assert "继续当前流程" in result["action"]
