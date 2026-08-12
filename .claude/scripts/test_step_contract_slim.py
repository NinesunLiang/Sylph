"""executor 契约精简（6→3）回归测试：只要求 Key Changes + TDD Evidence + EV 块。

还债项：砍掉 Conditions / Decisions / Acceptance Checklist 三段的格式摩擦，
保留验证必需的三段；EV 块防线（缺块即无法校验）不变。
"""
from step_contracts import EVIDENCE_REQUIRED_SECTIONS, validate_step_evidence


def test_evidence_required_sections_slimmed_to_two():
    assert EVIDENCE_REQUIRED_SECTIONS == ["Key Changes", "TDD Evidence"]


def test_three_section_executor_passes_validation():
    executor = (
        "## Key Changes\n- modified verify_gate.py\n\n"
        "## TDD Evidence\n- Dependency TDD: pytest test_x.py -> exit 0\n"
        "- Regression TDD: pytest -> exit 0\n\n"
        "### EV-S1\n- step: S1\n- exit_code: 0\n- assertion: done\n"
    )
    assert validate_step_evidence(executor, "S1") == []


def test_six_section_legacy_executor_still_passes():
    # 历史 6 段格式不报错（向后兼容：多余段不影响校验）
    executor = (
        "## Conditions\n- scope: verify_gate\n\n"
        "## Key Changes\n- modified verify_gate.py\n\n"
        "## Decisions\n- Rationale: 轻改放宽格式\n\n"
        "## Acceptance Checklist\n- [x] done\n\n"
        "## TDD Evidence\n- Dependency TDD: pytest test_x.py -> exit 0\n"
        "- Regression TDD: pytest -> exit 0\n\n"
        "### EV-S1\n- step: S1\n- exit_code: 0\n- assertion: done\n"
    )
    assert validate_step_evidence(executor, "S1") == []


def test_missing_key_changes_still_rejected():
    executor = (
        "## TDD Evidence\n- pytest -> exit 0\n\n"
        "### EV-S1\n- step: S1\n- exit_code: 0\n- assertion: done\n"
    )
    errors = validate_step_evidence(executor, "S1")
    assert any("key_changes" in e for e in errors)


def test_missing_tdd_evidence_still_rejected():
    executor = (
        "## Key Changes\n- changed file\n\n"
        "### EV-S1\n- step: S1\n- exit_code: 0\n- assertion: done\n"
    )
    errors = validate_step_evidence(executor, "S1")
    assert any("tdd" in e for e in errors)


def test_missing_ev_block_blocks_validation():
    executor = "## Key Changes\n- changed file\n\n## TDD Evidence\n- pytest -> exit 0\n"
    errors = validate_step_evidence(executor, "S1")
    assert any("missing_step_evidence_block" in e for e in errors)
