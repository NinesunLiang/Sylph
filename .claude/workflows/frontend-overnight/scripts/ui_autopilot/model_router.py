"""model_router.py — Model routing decisions with budget guardrails.

Routes tasks between:
  - haiku (default): 95%+ of calls, fast+cheap
  - sonnet (visual): key-frame visual diagnosis only, ≤40 calls/6h

Routing logic:
  1. Default: haiku for all routine patches and SCSS changes
  2. Escalate to sonnet when: consecutive stagnation ≥ 2, ambiguous visual
     root cause, or critical region score < 0.97
  3. Budget guard: sonnet calls capped, with escalation reason logging

Design: Grok dual-model strategy + Opus budget discipline.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import _model_from_env


class ModelTarget(StrEnum):
    """Environment-resolved Claude model roles."""
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


class EscalationReason(StrEnum):
    """Reasons for escalating from haiku to sonnet."""
    STAGNATION_COUNT = "stagnation_count_ge_2"
    AMBIGUOUS_VISUAL = "ambiguous_visual_root_cause"
    CRITICAL_REGION_LOW = "critical_region_score_lt_0.97"
    OSCILLATION_DETECTED = "oscillation_detected"
    OVERLAY_CONFLICT = "overlay_state_conflict"
    TYPOGRAPHY_DISPUTE = "typography_rendering_dispute"
    COLOR_AMBIGUITY = "color_perception_difference"
    CROSS_STATE_INCONSISTENCY = "cross_state_visual_inconsistency"


# ── Routing Engine ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ModelRouter:
    """Model routing with budget guardrails.

    Usage:
        router = ModelRouter(escalation_budget=40)
        target, reason = router.route(call_context)
        router.record_call(target, reason)
    """

    escalation_budget: int = 40
    haiku_calls: int = field(default=0)
    sonnet_calls: int = field(default=0)
    opus_calls: int = field(default=0)
    escalation_log: list[dict[str, Any]] = field(default_factory=list)

    def route(
        self,
        context: dict[str, Any],
    ) -> tuple[ModelTarget, EscalationReason | str]:
        """Determine which model should handle a call.

        Decision tree:
          1. If sonnet budget exhausted → FLASH (with reason)
          2. If critical escalation condition → KIMI
          3. Default → FLASH

        Args:
            context: Call context with keys:
                - stagnation_count: int (consecutive stagnant rounds)
                - critical_region_score: float (lowest critical region score)
                - root_cause_category: str (from ScoreDiff)
                - convergence_status: str (from ConvergenceTracker)
                - phase: str (current phase)
                - target_type: str (region|element|overlay)

        Returns:
            (model_target, reason_string)
        """
        stagnation = int(context.get("stagnation_count", 0))
        critical_score = float(context.get("critical_region_score", 1.0))
        root_cause = str(context.get("root_cause_category", ""))
        convergence = str(context.get("convergence_status", ""))
        target_type = str(context.get("target_type", ""))

        # ── Escalation checks ──

        # Check 1: consecutive stagnation ≥ 2
        if stagnation >= 2:
            return self._maybe_escalate(
                EscalationReason.STAGNATION_COUNT,
                f"consecutive_stagnant={stagnation}",
            )

        # Check 2: ambiguous visual root cause
        if root_cause in ("unknown", "style_mismatch") and convergence == "stagnant":
            return self._maybe_escalate(
                EscalationReason.AMBIGUOUS_VISUAL,
                f"root_cause={root_cause} convergence={convergence}",
            )

        # Check 3: critical region score < 0.97
        if critical_score < 0.97 and critical_score > 0.0:
            return self._maybe_escalate(
                EscalationReason.CRITICAL_REGION_LOW,
                f"critical_score={critical_score:.3f}",
            )

        # Check 4: oscillation detected
        if convergence == "oscillating":
            return self._maybe_escalate(
                EscalationReason.OSCILLATION_DETECTED,
                f"convergence={convergence}",
            )

        # Check 5: overlay conflict (interaction phase issues)
        if target_type == "overlay" and root_cause == "interaction_missing":
            return self._maybe_escalate(
                EscalationReason.OVERLAY_CONFLICT,
                f"target_type={target_type}",
            )

        # Default: use haiku
        return ModelTarget.HAIKU, "default"

    def record_call(
        self,
        target: ModelTarget,
        reason: EscalationReason | str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record a model call for budget tracking.

        Args:
            target: Which model was used
            reason: Why this model was chosen
            context: Optional call context for audit
        """
        self.haiku_calls += 1 if target == ModelTarget.HAIKU else 0
        self.sonnet_calls += 1 if target == ModelTarget.SONNET else 0
        self.opus_calls += 1 if target == ModelTarget.OPUS else 0

        if target == ModelTarget.SONNET:
            self.escalation_log.append({
                "timestamp": time.time(),
                "reason": str(reason),
                "context": context or {},
                "sonnet_count": self.sonnet_calls,
            })

    @property
    def total_calls(self) -> int:
        return self.haiku_calls + self.sonnet_calls + self.opus_calls

    @property
    def escalation_budget_remaining(self) -> int:
        return max(0, self.escalation_budget - self.sonnet_calls)

    @property
    def escalation_budget_exhausted(self) -> bool:
        return self.sonnet_calls >= self.escalation_budget

    def budget_report(self) -> dict[str, Any]:
        """Generate a budget usage report."""
        return {
            "haiku_calls": self.haiku_calls,
            "sonnet_calls": self.sonnet_calls,
            "escalation_budget": self.escalation_budget,
            "sonnet_remaining": self.escalation_budget_remaining,
            "opus_calls": self.opus_calls,
            "total_calls": self.total_calls,
            "escalation_count": len(self.escalation_log),
            "escalations": self.escalation_log[-5:],
        }

    # ── Internal ───────────────────────────────────────────────────────────

    def _maybe_escalate(
        self,
        reason: EscalationReason,
        detail: str,
    ) -> tuple[ModelTarget, EscalationReason | str]:
        """Try to escalate to sonnet, falling back to haiku if budget exhausted."""
        if self.escalation_budget_exhausted:
            return ModelTarget.HAIKU, f"escalation_budget_exhausted: {reason.value}"
        return ModelTarget.SONNET, f"{reason.value}: {detail}"


# ── Routing helpers for orchestrator integration ───────────────────────────────


def build_call_context(
    stagnation_count: int = 0,
    critical_region_score: float = 1.0,
    root_cause_category: str = "unknown",
    convergence_status: str = "opusgressing",
    phase: str = "",
    target_type: str = "region",
) -> dict[str, Any]:
    """Build a standardized call context dict for ModelRouter.route()."""
    return {
        "stagnation_count": stagnation_count,
        "critical_region_score": critical_region_score,
        "root_cause_category": root_cause_category,
        "convergence_status": convergence_status,
        "phase": phase,
        "target_type": target_type,
    }


def should_dom_assert_first(target_type: str) -> bool:
    """Determine if DOM assertion should be tried before visual model.

    For interaction-state verification (is-overlay-open, is-sidebar-expanded),
    DOM assertions are cheaper and more reliable than visual models.
    Only escalate to Kimi K3 when DOM assertion is ambiguous.
    """
    return target_type in ("overlay", "shell_component")
