"""task_generator.py — Bounded task generation with per-phase file scoping (Opus pattern).

Each task targets exactly one region/state/phase with a strictly bounded
files_allowed set. This prevents workers from touching anything outside
their current phase scope — Shell workers can't modify color tokens,
Element workers can't change layout scaffolding.

Key design:
  - Phase-scoped file patterns (Opus PHASE_ALLOWED_FILE_PATTERNS)
  - Priority sorting: visual_impact × confidence × risk_inverse
  - ProposeToken job routing when no matching token exists
  - Stagnation-aware: tasks that fail too many times get frozen
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .domain import Phase, Task, TaskStatus, RegionGold, Score
from .scorer import ScoreDiff
from .phase_rules import PHASE_ALLOWED_FILE_PATTERNS, PHASE_PROHIBITED_ALWAYS


# ── Task Generator ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class TaskGenerator:
    """Generates bounded tasks from phase + region tree + score diff.

    Usage:
        gen = TaskGenerator(target_repo="apps/my-app")
        tasks = gen.generate_for_phase(phase, regions, score_diff)
    """

    target_repo: str = "src"
    task_counter: int = field(default=0)

    def generate_for_phase(
        self,
        phase: Phase,
        regions: list[RegionGold],
        score_diff: ScoreDiff | None = None,
        current_scores: dict[str, float] | None = None,
    ) -> list[Task]:
        """Generate tasks for a given phase.

        Args:
            phase: Current phase
            regions: Region definitions (gold standard)
            score_diff: Current score diff for prioritization
            current_scores: Per-region current scores {region_id: composite}

        Returns:
            Ordered list of Tasks (highest priority first)
        """
        tasks: list[Task] = []

        allowed_patterns = PHASE_ALLOWED_FILE_PATTERNS.get(
            phase.name, ["src/**"]
        )

        for region in regions:
            for state in region.states:
                self.task_counter += 1
                task_id = f"{phase.value}-{region.id}-{state}-{self.task_counter:04d}"

                # Determine target type based on phase
                target_type = self._target_type_for_phase(phase)

                # Compute priority
                priority = self._compute_priority(
                    region, state, phase, score_diff, current_scores
                )

                task = Task(
                    id=task_id,
                    phase=phase,
                    target_id=f"{region.id}:{state}",
                    target_type=target_type,
                    status=TaskStatus.PENDING,
                    priority=priority,
                    allowed_files=list(allowed_patterns),
                    prohibited_patterns=list(PHASE_PROHIBITED_ALWAYS),
                    measurements={
                        "region_id": region.id,
                        "state": state,
                        "gold_image": region.gold_image_path,
                        "capture_trigger": region.capture,
                        "is_critical": region.is_critical,
                        "bbox": region.bbox,
                    },
                )

                tasks.append(task)

        # Sort by priority descending
        tasks.sort(key=lambda t: t.priority, reverse=True)

        # Assign dependency chain (each task depends on the previous one
        # for the same region — enforces atomic sequential repair)
        prev_by_region: dict[str, str] = {}
        for task in tasks:
            region_key = task.target_id.split(":")[0]
            prev = prev_by_region.get(region_key)
            if prev:
                task.dependencies.append(prev)
            prev_by_region[region_key] = task.id

        return tasks

    def generate_propose_token_task(
        self,
        property_name: str,
        candidate_value: str,
        nearest_token: str | None,
        distance: float,
        affected_regions: list[str],
    ) -> Task:
        """Generate a ProposeToken job when no matching token exists.

        This is a special task type that doesn't modify code directly —
        it proposes a new token value to the human for signoff.
        """
        self.task_counter += 1
        task_id = f"propose-token-{property_name}-{self.task_counter:04d}"

        return Task(
            id=task_id,
            phase=Phase.TOKENS,
            target_id=f"token:{property_name}",
            target_type="token_proposal",
            status=TaskStatus.PENDING,
            priority=0.8,  # High priority — token gaps block progress
            allowed_files=[".omc/ui-autopilot/{task_id}/proposals/"],
            prohibited_patterns=list(PHASE_PROHIBITED_ALWAYS),
            measurements={
                "property": property_name,
                "candidate_value": candidate_value,
                "nearest_token": nearest_token,
                "distance": distance,
                "affected_regions": affected_regions,
            },
            metadata={"type": "propose_token"},
        )

    # ── Internal helpers ────────────────────────────────────────────────────

    @staticmethod
    def _target_type_for_phase(phase: Phase) -> str:
        """Map phase to task target type."""
        mapping = {
            Phase.SHELL: "shell_component",
            Phase.REGIONS: "region",
            Phase.ELEMENTS: "element",
            Phase.INTERACTIONS: "overlay",
            Phase.POLISH: "element",
            Phase.FINAL_AUDIT: "audit",
        }
        return mapping.get(phase, "region")

    @staticmethod
    def _compute_priority(
        region: RegionGold,
        state: str,
        phase: Phase,
        score_diff: ScoreDiff | None,
        current_scores: dict[str, float] | None,
    ) -> float:
        """Compute task priority score.

        Priority = visual_impact × confidence × risk_inverse

        - visual_impact: region weight + criticality bonus
        - confidence: higher for regions with clear diff signals
        - risk_inverse: 1.0 for safe phases, lower for risky ones
        """
        # Visual impact: region weight + criticality
        visual_impact = region.weight if region.weight > 0 else 0.1
        if region.is_critical:
            visual_impact *= 1.5

        # Confidence: regions with worse scores get higher priority
        confidence = 0.8  # default
        if current_scores:
            region_key = f"{region.id}:{state}"
            score = current_scores.get(region_key, 0.5)
            # Lower score → higher priority
            confidence = 1.0 - score * 0.5

        # Risk inverse: interaction/polish phases are safer for changes
        risk_inverse = 1.0
        if phase in (Phase.SHELL, Phase.REGIONS):
            risk_inverse = 0.7  # Layout changes have higher blast radius
        elif phase == Phase.ELEMENTS:
            risk_inverse = 0.9
        elif phase == Phase.INTERACTIONS:
            risk_inverse = 0.85

        priority = visual_impact * confidence * risk_inverse

        # Boost default state (most visible)
        if state == "default":
            priority *= 1.2

        return min(1.0, priority)
