import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

from gatekeeper import GateContext, GateDecision, GateKeeper, Philosophy


def test_philosophy_priority_order():
    expected_keys = [
        "less_is_more",
        "verify_first",
        "zero_trust",
        "guard_first",
        "doc_first",
        "human_first",
        "gain_first",
    ]
    assert [item.key for item in Philosophy] == expected_keys
    assert [item.priority for item in Philosophy] == list(range(1, 8))
    assert GateKeeper._PHILOSOPHY_ORDER == expected_keys


def test_philosophy_scores_follow_priority_order():
    context = GateContext(
        action="evaluate all philosophy signals",
        target="test",
        risk_level="low",
        metadata={
            "has_verification": True,
            "minimal_privilege": True,
            "has_safeguards": True,
            "generates_documentation": True,
            "user_requested": True,
            "positive_roi": True,
            "simplifies_system": True,
        },
    )

    score, hits = GateKeeper._evaluate_philosophy(context)

    assert score == 49.0
    assert hits == [
        ("less_is_more", 10.0),
        ("verify_first", 9.0),
        ("zero_trust", 8.0),
        ("guard_first", 7.0),
        ("doc_first", 6.0),
        ("human_first", 5.0),
        ("gain_first", 4.0),
    ]


def test_iron_rule_blocks_simplification_bypass(monkeypatch):
    monkeypatch.delenv("GATEKEEPER_DISABLED", raising=False)
    context = GateContext(
        action="simplify governance gate",
        target=".claude/kernel.md",
        metadata={"bypass_attempt": True, "simplifies_system": True},
    )

    result = GateKeeper.evaluate(context, gate_type="execute")

    assert result.decision is GateDecision.BLOCK
    assert result.iron_law_violations
    assert result.philosophy_hits == []


def test_irreversible_operation_still_requires_confirmation(monkeypatch):
    monkeypatch.delenv("GATEKEEPER_DISABLED", raising=False)
    context = GateContext(
        action="perform irreversible operation",
        target="production",
        hazard_flags=["irreversible"],
        risk_level="high",
        metadata={"simplifies_system": True},
    )

    result = GateKeeper.evaluate(context, gate_type="execute")

    assert result.decision is GateDecision.ASK_USER


def test_unattended_irreversible_operation_still_skips(monkeypatch):
    monkeypatch.delenv("GATEKEEPER_DISABLED", raising=False)
    context = GateContext(
        action="perform irreversible operation",
        target="production",
        hazard_flags=["irreversible"],
        risk_level="high",
        unattended=True,
        metadata={"simplifies_system": True},
    )

    result = GateKeeper.evaluate(context, gate_type="execute")

    assert result.decision is GateDecision.SKIP


def test_philosophy_number_mapping_is_bijective():
    old_to_new = {1: 1, 2: 7, 3: 4, 4: 2, 5: 6, 6: 3, 7: 5}
    assert set(old_to_new.values()) == set(range(1, 8))
    assert {value: key for key, value in old_to_new.items()} == {
        1: 1,
        2: 4,
        3: 6,
        4: 3,
        5: 7,
        6: 5,
        7: 2,
    }


def test_feature_registry_uses_migrated_philosophy_numbers():
    registry = (ROOT / ".claude" / "references" / "feature-registry.yaml").read_text(
        encoding="utf-8"
    )
    assert 'name: permission-gate\n  philosophy: ["#3", "#4"]' in registry
    assert "name: edit-guard\n  philosophy: ['#2', '#3']" in registry
