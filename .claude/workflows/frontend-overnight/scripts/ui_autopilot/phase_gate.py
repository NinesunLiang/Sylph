"""phase_gate.py — Hierarchical phase gate system (Grok L0-L6 + Opus dual-direction).

Key differences from simple "next_phase()":
  - Dual-direction gates: entry conditions AND exit conditions per phase
  - Partial pass support: regions/elements can advance with partial completion
  - Interaction phase is HARD GATE: no partial pass, 100% required
  - Token pre-requisite: no Token gate → no Element phase
  - Regression detection: can trigger phase demotion

Design: Grok hierarchy + Opus entry/exit conditions, adapted for CarrorOS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .domain import Phase, PhaseThresholds, PHASE_THRESHOLDS, PHASE_TRANSITIONS
from .phase_rules import PHASE_ALLOWED_FILE_PATTERNS, PHASE_PROHIBITED_ALWAYS


# ── Phase Report ───────────────────────────────────────────────────────────────


@dataclass(slots=True)
class PhaseReport:
    """Aggregated report for a phase's completion status.

    This is what the orchestrator checks to determine can_advance().
    """
    phase: Phase
    blocking_errors: int = 0
    required_evidence_complete: bool = False
    runtime_errors: int = 0
    console_errors: int = 0

    # Phase-specific metrics
    route_coverage: float = 0.0
    state_inventory_complete: bool = False
    scroll_coverage: float = 0.0
    token_inventory_complete: bool = False
    token_baseline_frozen: bool = False
    token_compliance: float = 0.0

    geometry_score: float = 0.0
    global_similarity: float = 0.0
    minimum_region_similarity: float = 0.0
    minimum_critical_region_similarity: float = 0.0

    typography_score: float = 0.0
    color_score: float = 0.0
    decoration_score: float = 0.0

    interaction_coverage: float = 0.0
    state_coverage: float = 0.0
    viewport_coverage: float = 0.0

    shell_geometry_score: float = 0.0
    no_missing_shell_components: bool = False
    scroll_container_structure_correct: bool = False
    z_index_layer_correct: bool = False
    fixed_sticky_elements_positioned: bool = False

    region_geometry_score: float = 0.0
    all_required_regions_present: bool = False
    no_overflow_clipping: bool = False
    critical_regions_complete: bool = False

    element_visual_score: float = 0.0
    no_runtime_errors: bool = False
    no_console_errors: bool = False
    open_geometry_regressions: bool = False
    missing_critical_elements: bool = False

    final_gate_passed: bool = False

    # Additional metadata
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ── Gate Conditions ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PhaseGateRule:
    """A single gate condition for a phase."""
    requires: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)


# Entry conditions — must satisfy ALL "requires" and NONE of "blocked_by"
PHASE_ENTRY_CONDITIONS: dict[Phase, PhaseGateRule] = {
    Phase.DISCOVERY: PhaseGateRule(
        requires=[],  # Entry phase — no prerequisites
        blocked_by=[],
    ),
    Phase.TOKENS: PhaseGateRule(
        requires=[
            "discovery_complete",
            "prototype_scanned",
        ],
        blocked_by=["runtime_errors > 0"],
    ),
    Phase.SHELL: PhaseGateRule(
        requires=["token_baseline_frozen"],
        blocked_by=[],
    ),
    Phase.REGIONS: PhaseGateRule(
        requires=[
            "shell_geometry_score >= 0.95",
            "no_missing_shell_components",
        ],
        blocked_by=["runtime_errors > 0"],
    ),
    Phase.ELEMENTS: PhaseGateRule(
        requires=[
            "region_geometry_score >= 0.97",
            "all_required_regions_present",
        ],
        blocked_by=[],
    ),
    Phase.INTERACTIONS: PhaseGateRule(
        requires=[
            "element_visual_score >= 0.98",
            "token_compliance >= 0.99",
            "no_runtime_errors",
            "no_console_errors",
        ],
        blocked_by=[
            "open_geometry_regressions",
            "missing_critical_elements",
        ],
    ),
    Phase.POLISH: PhaseGateRule(
        requires=[
            "interaction_coverage >= 1.0",
            "state_coverage >= 1.0",
        ],
        blocked_by=[],
    ),
    Phase.FINAL_AUDIT: PhaseGateRule(
        requires=["final_gate_passed"],
        blocked_by=[],
    ),
}


# ── Gate Engine ────────────────────────────────────────────────────────────────


class PhaseGate:
    """Hierarchical phase gate engine.

    Evaluates entry/exit conditions per phase based on the PhaseReport.
    Supports partial advancement (regions/elements) and hard-gate phases
    (interactions, final_audit).

    Usage:
        gate = PhaseGate()
        report = PhaseReport(phase=Phase.SHELL, ...)
        if gate.can_advance(report):
            next_phase = gate.next_phase(report.phase)
    """

    def can_advance(self, report: PhaseReport) -> bool:
        """Check if the current phase can advance to the next."""
        if report.phase not in PHASE_TRANSITIONS:
            return False  # terminal phase

        # Common preconditions for ALL phases
        if report.blocking_errors > 0:
            return False
        if not report.required_evidence_complete:
            return False
        if report.runtime_errors > 0:
            return False

        # Phase-specific checks
        checker = getattr(self, f"_check_{report.phase.value}", None)
        if checker:
            return checker(report)

        return report.global_similarity >= 0.95

    def should_regress(self, report: PhaseReport) -> Phase | None:
        """Check if the current phase should regress to an earlier phase.

        Regression triggers:
          - Element phase finds systemic layout issues → regress to REGIONS
          - Interactions find open geometry regressions → regress to ELEMENTS
          - Token compliance drops below threshold → regress to TOKENS

        Returns the Phase to regress to, or None if no regression needed.
        """
        if report.open_geometry_regressions and report.phase in (
            Phase.INTERACTIONS, Phase.POLISH
        ):
            return Phase.REGIONS

        if report.missing_critical_elements and report.phase == Phase.INTERACTIONS:
            return Phase.ELEMENTS

        if report.token_compliance < 0.95 and report.phase in (
            Phase.ELEMENTS, Phase.INTERACTIONS, Phase.POLISH
        ):
            return Phase.TOKENS

        return None

    def next_phase(self, current: Phase) -> Phase | None:
        """Get the next phase in the hierarchy."""
        return PHASE_TRANSITIONS.get(current)

    def allowed_files_for_phase(self, phase: Phase, feature: str = "*") -> list[str]:
        """Get the allowed file patterns for a given phase.

        Args:
            phase: Current phase
            feature: Feature name for substitution in patterns

        Returns:
            List of file glob patterns workers may write to
        """
        key = phase.name  # e.g., "SHELL", "REGIONS"
        patterns = PHASE_ALLOWED_FILE_PATTERNS.get(key, ["src/**"])
        return [p.replace("{feature}", feature) for p in patterns]

    def prohibited_files_for_phase(self) -> list[str]:
        """Get always-prohibited file patterns."""
        return list(PHASE_PROHIBITED_ALWAYS)

    def get_thresholds(self, phase: Phase) -> PhaseThresholds:
        """Get the score thresholds for a phase."""
        return PHASE_THRESHOLDS.get(phase, PhaseThresholds(phase=phase))

    # ── Phase-specific checkers ────────────────────────────────────────────

    def _check_discovery(self, report: PhaseReport) -> bool:
        return (
            report.route_coverage >= 1.0
            and report.state_inventory_complete
            and report.scroll_coverage >= 1.0
        )

    def _check_tokens(self, report: PhaseReport) -> bool:
        return (
            report.token_inventory_complete
            and report.token_compliance >= 0.80
        )

    def _check_shell(self, report: PhaseReport) -> bool:
        return (
            report.geometry_score >= 0.95
            and report.global_similarity >= 0.95
            and report.no_missing_shell_components
            and report.scroll_container_structure_correct
            and report.z_index_layer_correct
            and report.fixed_sticky_elements_positioned
        )

    def _check_regions(self, report: PhaseReport) -> bool:
        return (
            report.global_similarity >= 0.97
            and report.minimum_region_similarity >= 0.97
            and report.all_required_regions_present
            and report.no_overflow_clipping
        )

    def _check_elements(self, report: PhaseReport) -> bool:
        return (
            report.global_similarity >= 0.98
            and report.typography_score >= 0.98
            and report.color_score >= 0.98
            and report.token_compliance >= 0.99
        )

    def _check_interactions(self, report: PhaseReport) -> bool:
        return (
            report.interaction_coverage >= 1.0
            and report.state_coverage >= 1.0
            and not report.open_geometry_regressions
            and not report.missing_critical_elements
        )

    def _check_polish(self, report: PhaseReport) -> bool:
        return (
            report.global_similarity >= 0.99
            and report.minimum_critical_region_similarity >= 0.99
            and report.token_compliance >= 0.99
        )

    def _check_final_audit(self, report: PhaseReport) -> bool:
        return report.final_gate_passed

    def can_enter(self, phase: Phase, report: PhaseReport) -> tuple[bool, list[str]]:
        """Check if a phase can be entered, returning (ok, missing_requirements).

        This is the dual of can_advance() — it checks entry conditions
        rather than exit conditions.

        Returns:
            (can_enter, list_of_missing_requirements)
        """
        rule = PHASE_ENTRY_CONDITIONS.get(phase)
        if rule is None:
            return True, []

        missing: list[str] = []

        for req in rule.requires:
            if not self._eval_condition(req, report):
                missing.append(req)

        for blocker in rule.blocked_by:
            if self._eval_condition(blocker, report):
                missing.append(f"blocked: {blocker}")

        can_enter = len(missing) == 0
        return can_enter, missing

    def _eval_condition(self, condition: str, report: PhaseReport) -> bool:
        """Evaluate a named condition string against a PhaseReport.

        Supported conditions:
          - "token_baseline_frozen" → report.token_baseline_frozen
          - "shell_geometry_score >= 0.95" → report.shell_geometry_score >= 0.95
          - "runtime_errors > 0" → report.runtime_errors > 0
          - etc.
        """
        # Simple boolean checks
        boolean_fields = {
            "token_baseline_frozen", "no_missing_shell_components",
            "critical_regions_complete", "all_required_regions_present",
            "no_runtime_errors", "no_console_errors",
            "open_geometry_regressions", "missing_critical_elements",
            "final_gate_passed",
        }

        if condition in boolean_fields:
            return bool(getattr(report, condition, False))

        # Comparison checks: "field >= value"
        import re

        match = re.match(
            r"(\w+)\s*(>=|<=|>|<|==)\s*([\d.]+)", condition
        )
        if match:
            field, op, val_str = match.groups()
            val = float(val_str)
            actual = float(getattr(report, field, 0.0))

            if op == ">=":
                return actual >= val
            elif op == "<=":
                return actual <= val
            elif op == ">":
                return actual > val
            elif op == "<":
                return actual < val
            elif op == "==":
                return actual == val

        # Unknown condition → fail-closed
        return False
