"""Four public entrypoints, with shared runtime capabilities retained."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {"lx-goal", "lx-rpe", "lx-pre-commit", "lx-pre-push"}


def test_only_four_public_skills():
    actual = {p.parent.name for p in (ROOT / ".claude/skills").glob("*/SKILL.md")}
    assert actual == EXPECTED


def test_internal_runtime_is_retained():
    for name in ("carros_base.py", "goal_state_machine.py", "goal_contracts.py",
                 "phase_contracts.py", "executor_ledger.py", "token_lifecycle.py",
                 "worktree_utils.py", "oracle_agent.py", "verify_gate.py"):
        assert (ROOT / ".claude/scripts" / name).is_file(), name


def test_goal_no_longer_routes_to_removed_entrypoint():
    text = (ROOT / ".claude/skills/lx-goal/SKILL.md").read_text()
    assert "direct + lx-stepwise" not in text


def test_delivery_manifest_includes_four_entrypoints():
    import yaml
    manifest = yaml.safe_load((ROOT / "packaging/manifest-delivery.yaml").read_text())
    for name in EXPECTED:
        assert any(f"skills/{name}/" in pattern for pattern in manifest["include"]), name
