"""TDD for GA observability metric semantics."""

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS / "lib"))

from ga_observability_metrics import (  # noqa: E402
    token_controllable_tokens,
    token_critical_count,
    token_compact_count,
    token_l5_count,
)


def test_empty_token_has_no_event_counts():
    token = {}
    assert token_l5_count(token) == 0
    assert token_compact_count(token) == 0
    assert token_critical_count(token) == 0


def test_explicit_zero_controllable_tokens_is_not_replaced():
    token = {"context": {"controllable_tokens": 0}}
    assert token_controllable_tokens(token, fallback=123) == 0


def test_explicit_event_counts_are_preserved():
    token = {
        "session": {"l5_count": 2, "compact_count": 3, "critical_trip_count": 4},
    }
    assert token_l5_count(token) == 2
    assert token_compact_count(token) == 3
    assert token_critical_count(token) == 4
