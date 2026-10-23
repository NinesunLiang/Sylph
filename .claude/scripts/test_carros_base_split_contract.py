"""Contract probes for a future carros_base split."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".claude" / "scripts" / "carros_base.py"


def test_carros_base_keeps_public_command_registry():
    text = SOURCE.read_text(encoding="utf-8")
    # 2026-10-24 人类裁决：12 个退役观察区命令（含 oracle / fallback）已物理删除，
    # 契约只剩真实在用的核心动词。详见 .omc/decisions/DECISIONS.md D-015。
    for command in ("init", "verify", "archive", "status", "tick", "lint"):
        assert f'"{command}"' in text


def test_carros_base_keeps_verdict_compatibility_facade():
    from carros_base import _aggregate_verdicts

    assert _aggregate_verdicts("ACCEPT", "REJECT") == "REJECT"


def test_carros_base_facade_honors_legacy_severity_monkeypatch():
    import carros_base

    original = carros_base._ORACLE_SEVERITY
    try:
        carros_base._ORACLE_SEVERITY = {"ACCEPT": 10, "REJECT": 1}
        assert carros_base._aggregate_verdicts("ACCEPT", "REJECT") == "ACCEPT"
    finally:
        carros_base._ORACLE_SEVERITY = original


def test_equal_severity_keeps_first_verdict_for_core_and_facade():
    from carros_core import aggregate_verdicts
    import carros_base

    assert aggregate_verdicts("LEFT", "RIGHT", {"LEFT": 1, "RIGHT": 1}) == "LEFT"

    original = carros_base._ORACLE_SEVERITY
    try:
        carros_base._ORACLE_SEVERITY = {"ACCEPT": 7, "REJECT": 7}
        assert carros_base._aggregate_verdicts("ACCEPT", "REJECT") == "ACCEPT"
    finally:
        carros_base._ORACLE_SEVERITY = original


def test_carros_base_keeps_task_and_archive_contracts():
    text = SOURCE.read_text(encoding="utf-8")
    assert "def cmd_archive" in text
    assert "def cmd_init" in text
    assert "token" in text and "audit" in text


def test_core_aggregate_verdicts_prefers_stricter_result():
    from carros_core import aggregate_verdicts

    assert aggregate_verdicts("ACCEPT", "REJECT") == "REJECT"
    assert aggregate_verdicts("ADVISORY", "ESCALATE") == "ESCALATE"
    assert aggregate_verdicts("ACCEPT", "ACCEPT") == "ACCEPT"


def test_core_aggregate_verdicts_preserves_unknown_fallback_order():
    from carros_core import aggregate_verdicts

    assert aggregate_verdicts("UNKNOWN", "ACCEPT") == "ACCEPT"
    assert aggregate_verdicts("UNKNOWN", "ALSO_UNKNOWN") == "UNKNOWN"
