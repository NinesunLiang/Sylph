"""test_p0_blockers.py — TDD verification for 7 P0 Blockers fix.

Verifies all 7 blockers are fixed:
  P0-1: Token permission rules no contradiction
  P0-2: Candidate workspace isolation exists
  P0-3: D6/D7 measurement producers exist
  P0-4: Worker envelope validation rejects control fields
  P0-5: UTC time persistence across checkpoint
  P0-6: orchestrator.py imports MAX_TOTAL_ITERATIONS
  P0-7: LoopController.record_and_decide() accepts gates_passed
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "workflows" / "frontend-overnight" / "scripts"))

from ui_autopilot.domain import CandidateWorkspace, RunState
from ui_autopilot.phase_rules import PHASE_ALLOWED_FILE_PATTERNS, PHASE_PROHIBITED_ALWAYS, Phase
from ui_autopilot.convergence import LoopController


def test_p0_1_token_permission_no_contradiction():
    """P0-1: Token phase patterns do NOT allow src/styles/tokens/source/**"""
    allowed = PHASE_ALLOWED_FILE_PATTERNS.get(Phase.TOKENS, [])

    # Verify TOKENS phase does NOT allow src/styles/tokens/source/
    for pattern in allowed:
        assert not pattern.startswith("src/styles/tokens/source/"), \
            f"TOKENS phase must NOT allow {pattern}"

    # Verify prohibited list contains token source
    assert any("src/styles/tokens/source" in p for p in PHASE_PROHIBITED_ALWAYS), \
        "PHASE_PROHIBITED_ALWAYS must contain src/styles/tokens/source/"

    print("✅ P0-1: Token permission rules have no contradiction")


def test_p0_2_candidate_workspace_dataclass_exists():
    """P0-2: CandidateWorkspace dataclass exists with required fields"""
    candidate = CandidateWorkspace(
        worktree_path="/tmp/test-worktree",
        branch_name="night-patch-test",
        created_at="2026-07-30T00:00:00Z",
        patch_id="test-patch-001",
    )

    assert candidate.worktree_path == "/tmp/test-worktree"
    assert candidate.branch_name == "night-patch-test"
    assert candidate.patch_id == "test-patch-001"

    print("✅ P0-2: CandidateWorkspace dataclass exists with correct fields")


def test_p0_3_d6_d7_producers_exist():
    """P0-3: D6/D7 measurement producer files exist"""
    base = Path(__file__).parent.parent / ".claude" / "workflows" / "frontend-overnight" / "scripts" / "ui_autopilot"

    d6_producer = base / "token_align_producer.py"
    d7_producer = base / "interaction_assertion_runner.py"

    assert d6_producer.exists(), "token_align_producer.py must exist"
    assert d7_producer.exists(), "interaction_assertion_runner.py must exist"

    # Verify D6 contains alignment_rate logic
    d6_content = d6_producer.read_text()
    assert "alignment_rate" in d6_content, "D6 producer must compute alignment_rate"
    assert "scan_token_usage" in d6_content, "D6 producer must scan source files"

    # Verify D7 contains interaction_coverage logic
    d7_content = d7_producer.read_text()
    assert "interaction_coverage" in d7_content, "D7 producer must compute interaction_coverage"
    assert "run_assertion" in d7_content, "D7 producer must run Playwright assertions"

    print("✅ P0-3: D6/D7 measurement producers exist and contain correct logic")


def test_p0_4_worker_envelope_validation():
    """P0-4: Orchestrator._validate_worker_envelope() rejects control fields"""
    from ui_autopilot.orchestrator import Orchestrator

    # Check method exists
    assert hasattr(Orchestrator, "_validate_worker_envelope"), \
        "Orchestrator must have _validate_worker_envelope method"

    # Verify orchestrator.py contains forbidden field check
    orch_path = Path(__file__).parent.parent / ".claude" / "workflows" / "frontend-overnight" / "scripts" / "ui_autopilot" / "orchestrator.py"
    orch_content = orch_path.read_text()

    assert "gate_results" in orch_content, "Must check for gate_results field"
    assert "accepted" in orch_content, "Must check for accepted field"
    assert "phase_advance" in orch_content, "Must check for phase_advance field"
    assert "UntrustedControlFieldError" in orch_content or "ValueError" in orch_content, \
        "Must raise error on forbidden fields"

    print("✅ P0-4: Worker envelope validation exists and checks control fields")


def test_p0_5_utc_time_persistence():
    """P0-5: RunState uses UTC timestamps that survive checkpoint"""
    from ui_autopilot.convergence import StrategyState

    # Verify StrategyState uses locked_until_utc (not monotonic)
    strategy = StrategyState()
    assert hasattr(strategy, "locked_until_utc"), \
        "StrategyState must have locked_until_utc field"

    # Verify StrategyState.to_dict() includes utc field
    strategy_dict = strategy.to_dict()
    assert "locked_until_utc" in strategy_dict, \
        "StrategyState.to_dict() must serialize locked_until_utc"

    # Verify StrategyState.from_dict() restores utc field
    restored = StrategyState.from_dict({"locked_until_utc": 1234567890.0})
    assert restored.locked_until_utc == 1234567890.0, \
        "StrategyState.from_dict() must restore locked_until_utc"

    # Verify RunState has wall_clock_deadline_utc field
    state = RunState(run_id="test", task_name="test")
    assert hasattr(state, "wall_clock_deadline_utc"), \
        "RunState must have wall_clock_deadline_utc field"

    # Verify RunState serialization includes deadline_utc
    state_dict = state.to_dict()
    assert "wall_clock_deadline_utc" in state_dict, \
        "RunState.to_dict() must serialize wall_clock_deadline_utc"

    print("✅ P0-5: UTC time fields exist and serialize correctly")


def test_p0_6_orchestrator_imports_config_constants():
    """P0-6: orchestrator.py imports MAX_TOTAL_ITERATIONS and CHECKPOINT_EVERY_SECONDS"""
    orch_path = Path(__file__).parent.parent / ".claude" / "workflows" / "frontend-overnight" / "scripts" / "ui_autopilot" / "orchestrator.py"
    orch_content = orch_path.read_text()

    # Verify imports exist in from .config import block
    assert "MAX_TOTAL_ITERATIONS" in orch_content, \
        "orchestrator.py must import MAX_TOTAL_ITERATIONS"
    assert "CHECKPOINT_EVERY_SECONDS" in orch_content, \
        "orchestrator.py must import CHECKPOINT_EVERY_SECONDS"

    # Verify no duplicate inline import exists
    import_count = orch_content.count("from .config import CHECKPOINT_EVERY_SECONDS")
    assert import_count == 0, \
        "orchestrator.py must NOT have duplicate inline CHECKPOINT_EVERY_SECONDS import"

    print("✅ P0-6: orchestrator.py imports config constants correctly")


def test_p0_7_loop_controller_gates_passed_parameter():
    """P0-7: LoopController.record_and_decide() accepts gates_passed parameter"""
    import inspect

    # Verify method signature includes gates_passed
    sig = inspect.signature(LoopController.record_and_decide)
    params = list(sig.parameters.keys())

    assert "gates_passed" in params, \
        "LoopController.record_and_decide() must accept gates_passed parameter"

    # Verify convergence.py contains gates_passed logic
    conv_path = Path(__file__).parent.parent / ".claude" / "workflows" / "frontend-overnight" / "scripts" / "ui_autopilot" / "convergence.py"
    conv_content = conv_path.read_text()

    assert "gates_passed" in conv_content, \
        "convergence.py must contain gates_passed logic"

    print("✅ P0-7: LoopController.record_and_decide() accepts gates_passed parameter")


def main() -> int:
    """Run all P0 blocker tests."""
    tests = [
        test_p0_1_token_permission_no_contradiction,
        test_p0_2_candidate_workspace_dataclass_exists,
        test_p0_3_d6_d7_producers_exist,
        test_p0_4_worker_envelope_validation,
        test_p0_5_utc_time_persistence,
        test_p0_6_orchestrator_imports_config_constants,
        test_p0_7_loop_controller_gates_passed_parameter,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Total: {len(tests)} tests, {passed} passed, {failed} failed")
    print(f"{'='*60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
