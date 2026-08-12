"""Focused regressions for VerifyGate assertion matching (index12 S2 / P1-4).

The `assertion:` verify rule previously required the ENTIRE expected rule text to be a
verbatim substring of the evidence assertion. A rule with two clauses whose assertion
rephrases or interleaves extra detail (e.g. "task binding confirmed as expected and report
index advanced to 12") failed the gate even though every clause was covered. This suite
locks in segment-OR matching with a majority requirement, while keeping the whole-rule
substring path backward-compatible.
"""
from verify_gate import match_verify_rule


def test_assertion_segments_match_with_interleaved_detail():
    # Red before fix: whole-rule substring fails (extra words + missing ";"),
    # but both clauses are present as segments.
    ok, reason, _ = match_verify_rule(
        "assertion: task binding confirmed; report index advanced",
        [{"type": "test",
          "assertion": "task binding confirmed as expected and report index advanced to 12",
          "evidence_level": "E2"}],
    )
    assert ok, reason
    assert "task binding confirmed" in reason


def test_assertion_partial_segment_coverage_is_not_a_match():
    # Guard against over-lenient matching: 1 of 3 clauses is below majority.
    ok, reason, _ = match_verify_rule(
        "assertion: task binding confirmed; report index advanced; all checks green",
        [{"type": "test", "assertion": "task binding confirmed only", "evidence_level": "E2"}],
    )
    assert not ok, reason


def test_assertion_whole_rule_substring_still_matches():
    # Backward compatibility: verbatim whole-rule substring remains a match.
    ok, reason, _ = match_verify_rule(
        "assertion: task binding confirmed; report index advanced",
        [{"type": "test",
          "assertion": "task binding confirmed; report index advanced（全部通过）",
          "evidence_level": "E2"}],
    )
    assert ok, reason


def test_assertion_segment_match_also_checks_output_tail():
    # Segment match should also work against command output tail with exit 0.
    ok, reason, _ = match_verify_rule(
        "assertion: report index advanced",
        [{"type": "test",
          "assertion": "irrelevant text",
          "output_tail": "report index advanced to 12",
          "exit_code": 0}],
    )
    assert ok, reason
