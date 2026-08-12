"""Regression: plan step dependencies may be comma-separated (index17 S6).

`find_first_activatable_step` only handled a single dep ("none" or one id),
so a step with `depends_on: S2,S3,S4` was never activatable even after all
deps completed. Fix: split on ',' and require all deps completed.
"""
from step_contracts import _deps_all_completed, find_first_activatable_step


def _steps():
    return [
        {"id": "S1", "status": "completed", "depends_on": "none"},
        {"id": "S2", "status": "completed", "depends_on": "S1"},
        {"id": "S3", "status": "completed", "depends_on": "S2"},
        {"id": "S4", "status": "completed", "depends_on": "S3"},
        {"id": "S5", "status": "completed", "depends_on": "S4"},
        {"id": "S6", "status": "pending", "depends_on": "S2,S3,S4"},
        {"id": "S7", "status": "pending", "depends_on": "S6"},
    ]


def test_multi_dep_all_completed_is_activatable():
    # Red before fix: "S2,S3,S4" not in completed set → returns S7 or None.
    assert find_first_activatable_step(_steps()) == "S6"


def test_multi_dep_with_pending_dep_is_skipped():
    # Guard: multi-dep step with an incomplete dep must not be selected
    # when a later step is activatable.
    steps = [
        {"id": "A", "status": "completed", "depends_on": "none"},
        {"id": "C", "status": "pending", "depends_on": "A,B"},
        {"id": "B", "status": "pending", "depends_on": "A"},
    ]
    assert find_first_activatable_step(steps) == "B"


def test_single_dep_still_works():
    steps = [
        {"id": "A", "status": "completed", "depends_on": "none"},
        {"id": "B", "status": "pending", "depends_on": "A"},
    ]
    assert find_first_activatable_step(steps) == "B"


def test_none_dep_first_pending():
    steps = [
        {"id": "A", "status": "pending", "depends_on": "none"},
        {"id": "B", "status": "pending", "depends_on": "A"},
    ]
    assert find_first_activatable_step(steps) == "A"


def test_deps_all_completed_helper():
    # Direct coverage of the shared helper used by start_step_atomic (index17 S6).
    completed = {"S1", "S2", "S3", "S4", "S5"}
    assert _deps_all_completed("none", completed) is True
    assert _deps_all_completed("S2", completed) is True
    assert _deps_all_completed("S2,S3,S4", completed) is True
    assert _deps_all_completed("S2,S3,S9", completed) is False
    assert _deps_all_completed("S2, S4", completed) is True  # spaces tolerated
