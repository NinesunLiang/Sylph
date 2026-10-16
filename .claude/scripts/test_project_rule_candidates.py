"""Tests for source-bound project rule candidates."""
from __future__ import annotations

from project_rule_candidates import extract_candidates, heuristic_extractor, write_candidates


def _extractor(blocks):
    assert any(block["source"] == "README.md:1" for block in blocks)
    return [
        {"source": "README.md:1", "text": "项目组件不得超过 300 行"},
        {"source": "README.md:1", "text": "项目组件不得超过 300 行"},
        {"source": "outside.md:1", "text": "不可接受"},
        {"source": "README.md:1", "text": "固定规则原文"},
    ]


def test_candidates_are_source_bound_deduplicated_and_feedback_only(tmp_path):
    (tmp_path / "README.md").write_text("项目组件不得超过 300 行\n", encoding="utf-8")
    result = extract_candidates(tmp_path, _extractor, {"固定规则原文"})
    assert result["sources"] == ["README.md"]
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["source"] == "README.md:1"
    assert candidate["enforcement"] == "feedback_only"


def test_heuristic_extractor_selects_only_explicit_rule_lines():
    selected = heuristic_extractor([
        {"source": "README.md:1", "text": "这是产品介绍"},
        {"source": "README.md:2", "text": "禁止硬编码颜色"},
    ])
    assert selected == [{"source": "README.md:2", "text": "禁止硬编码颜色"}]


def test_missing_extractor_is_honest_and_does_not_invent_rules(tmp_path):
    (tmp_path / "AGENTS.md").write_text("规则\n", encoding="utf-8")
    result = extract_candidates(tmp_path, None, set())
    assert result["candidates"] == []
    assert result["unavailable_reason"] == "extractor_unavailable"


def test_candidates_can_be_persisted_under_runtime_state(tmp_path):
    target = tmp_path / ".omc/state/project-rules/candidates.json"
    result = {"schema_version": "carros.project_rule_candidates.v1", "candidates": []}
    write_candidates(result, target)
    assert target.exists()
