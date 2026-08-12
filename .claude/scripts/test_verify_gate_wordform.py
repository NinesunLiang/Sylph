"""Regression: VerifyGate assertion core-term matching must normalize word forms (index17 M1).

Rule uses "artifacts exist", evidence assertion uses "artifacts exists"/"artifacts 存在".
Before fix, `_extract_core_terms` returned {'artifacts','exist'} vs {'artifacts','exists'}
so `expected_terms <= assertion_terms` failed and a legitimate evidence was BLOCKED.
Fix: canonicalize word atoms (strip plural/3rd-person trailing 's').
"""
from verify_gate import match_verify_rule


def _ev(assertion: str, el: str = "E3") -> dict:
    return {"type": "test", "assertion": assertion, "evidence_level": el, "exit_code": 0}


def test_exist_exists_core_term_match():
    # Red before fix: exist != exists blocks legitimate evidence.
    ok, reason, _ = match_verify_rule(
        "assertion: artifacts exist",
        [_ev("artifacts exists（10/10 全部 exit 0）")],
    )
    assert ok, reason


def test_spawn_matrix_assertion_zh_match():
    # Chinese 存在 side must also cover English "exist".
    ok, reason, _ = match_verify_rule(
        "assertion: 8/8 spawn-matrix artifacts exist",
        [_ev("8/8 spawn-matrix artifacts 存在，findings=0")],
    )
    assert ok, reason


def test_canonical_atom_plural_and_third_person():
    # Canonicalization: plural/3rd-person -s stripped, guarded.
    from verify_gate import _canonical_atom
    assert _canonical_atom("exists") == "exist"
    assert _canonical_atom("artifacts") == "artifact"
    assert _canonical_atom("files") == "file"
    assert _canonical_atom("verify") == "verify"


def test_wordform_mismatch_still_rejected():
    # Different lexeme must not match even after canonicalization.
    ok, reason, _ = match_verify_rule(
        "assertion: artifacts exist",
        [_ev("artifacts removed from workspace")],
    )
    assert not ok, reason


def test_ss_guard_does_not_over_strip():
    # 'ss' suffix words (e.g. class/process) must not lose their trailing 's'.
    from verify_gate import _canonical_atom
    assert _canonical_atom("class") == "class"
    assert _canonical_atom("process") == "process"
