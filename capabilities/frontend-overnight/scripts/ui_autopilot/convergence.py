"""convergence.py — EMA-based improvement-rate convergence tracker (Opus pattern).

Key innovation over simple counters:
  - Tracks improvement-rate EMA, not raw score delta
  - Distinguishes 6 distinct convergence states
  - "Micro-tremors" (0.82→0.82→0.821) don't reset counters
  - Oscillation detection prevents ping-pong repair loops
  - Decision engine returns actionable next-steps, never just "exit"

Design: Opus 4.8 convergence model, adapted for CarrorOS orchestration.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .domain import ConvergenceStatus, Phase, TaskStatus


# ── Convergence Tracker ────────────────────────────────────────────────────────


@dataclass(slots=True)
class ConvergenceTracker:
    """EMA-based convergence state detector.

    Instead of simple "no-progress-N→exit", this tracks the exponential
    moving average of score deltas to determine the improvement regime:

      PROGRESSING  — EMA stable positive, keep current strategy
      DECELERATING — EMA shrinking but positive, switch to precision
      STAGNANT     — EMA near zero, trigger root-cause diagnosis
      OSCILLATING  — score bouncing in a band, lock direction
      CONVERGED    — above threshold + EMA stable
      DIVERGING    — score decreasing, emergency rollback
    """

    target_threshold: float
    ema_alpha: float = 0.3
    stagnant_ema_threshold: float = 0.0005
    oscillation_window: int = 6
    history_max: int = 40

    _scores: deque[float] = field(default_factory=deque, repr=False)
    _ema: float = field(default=0.0, repr=False)
    _ema_initialized: bool = field(default=False, repr=False)

    def record(self, score: float) -> ConvergenceStatus:
        """Record a new score and return the current convergence status.

        Args:
            score: Current UIF-99 composite score [0.0, 1.0]

        Returns:
            ConvergenceStatus classification
        """
        self._scores.append(score)

        if len(self._scores) > self.history_max:
            self._scores.popleft()

        # Need at least 2 points for delta
        if len(self._scores) < 2:
            return ConvergenceStatus.PROGRESSING

        delta = self._scores[-1] - self._scores[-2]

        if not self._ema_initialized:
            self._ema = delta
            self._ema_initialized = True
        else:
            self._ema = (
                self.ema_alpha * delta
                + (1 - self.ema_alpha) * self._ema
            )

        # Check if converged (at target + EMA stable)
        if score >= self.target_threshold:
            if abs(self._ema) < self.stagnant_ema_threshold:
                return ConvergenceStatus.CONVERGED

        # Check for divergence
        if self._ema < -0.005:
            return ConvergenceStatus.DIVERGING

        # Check for oscillation
        if len(self._scores) >= self.oscillation_window:
            window = list(self._scores)[-self.oscillation_window:]
            if self._is_oscillating(window):
                return ConvergenceStatus.OSCILLATING

        # Check for stagnation
        if abs(self._ema) < self.stagnant_ema_threshold:
            return ConvergenceStatus.STAGNANT

        # Check for deceleration
        if 0 < self._ema < self.stagnant_ema_threshold * 4:
            return ConvergenceStatus.DECELERATING

        return ConvergenceStatus.PROGRESSING

    @staticmethod
    def _is_oscillating(window: list[float]) -> bool:
        """Detect score oscillation with zero net progress."""
        if len(window) < 4:
            return False

        direction_changes = sum(
            1
            for i in range(1, len(window) - 1)
            if (window[i] - window[i - 1]) * (window[i + 1] - window[i]) < 0
        )

        net_progress = window[-1] - window[0]

        return direction_changes >= 3 and abs(net_progress) < 0.003

    @property
    def current_ema(self) -> float:
        return self._ema

    @property
    def latest_score(self) -> float | None:
        return self._scores[-1] if self._scores else None

    @property
    def best_score(self) -> float:
        return max(self._scores) if self._scores else 0.0

    @property
    def score_count(self) -> int:
        return len(self._scores)

    def to_dict(self) -> dict[str, Any]:
        """Serialize convergence tracker state for checkpoint."""
        return {
            "target_threshold": self.target_threshold,
            "ema_alpha": self.ema_alpha,
            "stagnant_ema_threshold": self.stagnant_ema_threshold,
            "oscillation_window": self.oscillation_window,
            "history_max": self.history_max,
            "_scores": list(self._scores),
            "_ema": self._ema,
            "_ema_initialized": self._ema_initialized,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConvergenceTracker:
        """Restore convergence tracker from checkpoint."""
        tracker = cls(
            target_threshold=data["target_threshold"],
            ema_alpha=data.get("ema_alpha", 0.3),
            stagnant_ema_threshold=data.get("stagnant_ema_threshold", 0.0005),
            oscillation_window=data.get("oscillation_window", 6),
            history_max=data.get("history_max", 40),
        )
        tracker._scores = deque(data.get("_scores", []), maxlen=tracker.history_max)
        tracker._ema = data.get("_ema", 0.0)
        tracker._ema_initialized = data.get("_ema_initialized", False)
        return tracker


# ── Strategy State ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class StrategyState:
    """Tracks the current repair strategy to support direction locking."""
    current: str = "normal"
    locked_direction: str | None = None
    locked_until_utc: float = 0.0  # UTC timestamp, survives checkpoint restore

    def lock(self, direction: str, duration_seconds: float) -> None:
        self.locked_direction = direction
        self.locked_until_utc = datetime.now(timezone.utc).timestamp() + duration_seconds
        self.current = "locked"

    def unlock(self) -> None:
        if datetime.now(timezone.utc).timestamp() >= self.locked_until_utc:
            self.locked_direction = None
            self.current = "normal"

    @property
    def is_locked(self) -> bool:
        return (
            self.locked_direction is not None
            and datetime.now(timezone.utc).timestamp() < self.locked_until_utc
        )

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "locked_direction": self.locked_direction,
            "locked_until_utc": self.locked_until_utc,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StrategyState:
        s = cls()
        s.current = data.get("current", "normal")
        s.locked_direction = data.get("locked_direction")
        s.locked_until_utc = data.get("locked_until_utc", 0.0)
        return s


# ── Action Types ───────────────────────────────────────────────────────────────


class LoopAction:
    """Actions the LoopController can emit. Never 'exit' directly — that's
    the orchestrator's decision after reading the action."""
    CONTINUE_NORMAL = "CONTINUE_NORMAL"
    CONTINUE_NEXT_TARGET = "CONTINUE_NEXT_TARGET"
    PHASE_COMPLETE_ADVANCE = "PHASE_COMPLETE_ADVANCE"
    SWITCH_TO_PRECISION = "SWITCH_TO_PRECISION_PATCH_MODE"
    RETRY_WITH_MORE_MEASUREMENTS = "RETRY_WITH_MORE_MEASUREMENTS"
    ESCALATE_TO_ROOT_CAUSE = "ESCALATE_TO_ROOT_CAUSE_ANALYSIS"
    INVOKE_VISUAL_DIAGNOSIS = "INVOKE_KIMI_VISUAL_DIAGNOSIS"
    DEMOTE_PHASE_AND_RETRY_PARENT = "DEMOTE_PHASE_AND_RETRY_PARENT"
    FREEZE_TARGET_CONTINUE_OTHERS = "FREEZE_TARGET_CONTINUE_OTHERS"
    LOCK_AND_TRY_DIFFERENT = "LOCK_AND_TRY_DIFFERENT_APPROACH"
    ROLLBACK_LAST_PATCH = "ROLLBACK_LAST_PATCH"
    EMERGENCY_ROLLBACK_TO_BEST = "EMERGENCY_ROLLBACK_TO_BEST"
    TERMINATE_BLOCKER_REPORT = "TERMINATE_BLOCKER_REPORT"
    ENTER_FINAL_AUDIT = "ENTER_FINAL_AUDIT"
    CONVERGED_PROCEED_TO_GATE = "CONVERGED_PROCEED_TO_GATE"


# ── Loop Controller ────────────────────────────────────────────────────────────


@dataclass(slots=True)
class LoopController:
    """Main decision engine for the repair loop.

    Key difference from simple "iteration count" control:
      - Exit strategy based on convergence state machine
      - Different convergence states trigger different actions
      - Stagnation escalates through a pre-defined ladder
      - Deadlines and budget are factors, not the primary driver
    """

    target_threshold: float
    deadline_epoch: float                     # Unix timestamp of wall-clock deadline
    reserve_seconds: float = 1800             # 30 min reserve for final audit
    budget: dict[str, int] = field(default_factory=dict)

    _tracker: ConvergenceTracker = field(init=False)
    _strategy: StrategyState = field(default_factory=StrategyState)
    _consecutive_stagnant: int = field(default=0)
    _consecutive_diverging: int = field(default=0)
    _phase_attempts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._tracker = ConvergenceTracker(
            target_threshold=self.target_threshold,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize loop controller state for checkpoint."""
        return {
            "target_threshold": self.target_threshold,
            "deadline_epoch": self.deadline_epoch,
            "reserve_seconds": self.reserve_seconds,
            "budget": self.budget,
            "_tracker": self._tracker.to_dict(),
            "_strategy": self._strategy.to_dict(),
            "_consecutive_stagnant": self._consecutive_stagnant,
            "_consecutive_diverging": self._consecutive_diverging,
            "_phase_attempts": self._phase_attempts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoopController:
        """Restore loop controller from checkpoint."""
        controller = cls(
            target_threshold=data["target_threshold"],
            deadline_epoch=data["deadline_epoch"],
            reserve_seconds=data.get("reserve_seconds", 1800),
            budget=data.get("budget", {}),
        )
        controller._tracker = ConvergenceTracker.from_dict(data["_tracker"])

        strategy_data = data.get("_strategy", {})
        controller._strategy = StrategyState.from_dict(strategy_data)

        controller._consecutive_stagnant = data.get("_consecutive_stagnant", 0)
        controller._consecutive_diverging = data.get("_consecutive_diverging", 0)
        controller._phase_attempts = data.get("_phase_attempts", {})

        return controller

    def record_and_decide(
        self,
        score: float,
        phase: str,
        gates_passed: bool = True,
        on_strategy_change: Callable[[str, str], None] | None = None,
    ) -> str:
        """Record a score and return the next action.

        Returns one of the LoopAction constants. Never returns "exit" —
        that decision belongs to the orchestrator after interpreting the action.

        Args:
            score: Current UIF-99 composite score
            phase: Current phase identifier string
            gates_passed: Whether gate validation passed (only feed EMA with valid samples)
            on_strategy_change: Optional callback for strategy transitions

        Returns:
            LoopAction constant string
        """
        self._strategy.unlock()

        # Only feed EMA with scores that passed gate validation
        if gates_passed:
            status = self._tracker.record(score)
        else:
            # Gate failure: don't pollute EMA, use last known status
            status = (
                self._tracker.record(self._tracker.latest_score or 0.0)
                if self._tracker.latest_score is not None
                else ConvergenceStatus.PROGRESSING
            )

        self._phase_attempts[phase] = self._phase_attempts.get(phase, 0) + 1

        remaining = self.deadline_epoch - datetime.now(timezone.utc).timestamp()

        # Deadline check: if within reserve window, enter final audit
        if remaining < self.reserve_seconds:
            return LoopAction.ENTER_FINAL_AUDIT

        # Goal met: advance to next gate
        if score >= self.target_threshold:
            return LoopAction.CONVERGED_PROCEED_TO_GATE

        # Diverging: score is actively getting worse
        if status == ConvergenceStatus.DIVERGING:
            self._consecutive_diverging += 1
            self._consecutive_stagnant = 0

            if self._consecutive_diverging >= 2:
                return LoopAction.EMERGENCY_ROLLBACK_TO_BEST

            return LoopAction.ROLLBACK_LAST_PATCH

        self._consecutive_diverging = 0

        # Oscillating: score bouncing, no real progress
        if status == ConvergenceStatus.OSCILLATING:
            direction = f"{phase}_{score:.4f}"
            self._strategy.lock(direction, 21600)  # Lock 6h, skip this direction

            if on_strategy_change:
                on_strategy_change("oscillating", direction)

            return LoopAction.LOCK_AND_TRY_DIFFERENT

        # Stagnant: EMA near zero — escalate through diagnostic ladder
        if status == ConvergenceStatus.STAGNANT:
            self._consecutive_stagnant += 1

            # Escalation ladder: each stagnation → more aggressive action
            thresholds = [1, 2, 3, 5, 8]
            actions = [
                LoopAction.RETRY_WITH_MORE_MEASUREMENTS,
                LoopAction.ESCALATE_TO_ROOT_CAUSE,
                LoopAction.INVOKE_VISUAL_DIAGNOSIS,
                LoopAction.DEMOTE_PHASE_AND_RETRY_PARENT,
                LoopAction.FREEZE_TARGET_CONTINUE_OTHERS,
            ]

            for i, threshold in enumerate(thresholds):
                if self._consecutive_stagnant == threshold:
                    return actions[i]

            return LoopAction.TERMINATE_BLOCKER_REPORT

        self._consecutive_stagnant = 0

        # Decelerating: improvement slowing down
        if status == ConvergenceStatus.DECELERATING:
            return LoopAction.SWITCH_TO_PRECISION

        # Progressing: normal operation
        return LoopAction.CONTINUE_NORMAL

    @property
    def best_score(self) -> float:
        return self._tracker.best_score

    @property
    def latest_score(self) -> float | None:
        return self._tracker.latest_score

    @property
    def status(self) -> ConvergenceStatus:
        """Get current convergence status without recording a new score."""
        return self._tracker.record(self._tracker.latest_score or 0.0)


# ── Scheduler helpers ──────────────────────────────────────────────────────────


def compute_phase_budget(
    total_wall_clock: int,
    phases: list[str],
    default_ratios: dict[str, float] | None = None,
) -> dict[str, int]:
    """Distribute wall-clock budget across phases.

    Default ratios (from plan §IV):
      DISCOVERY: 5%, TOKENS: 10%, SHELL: 10%, REGIONS: 25%,
      ELEMENTS: 25%, INTERACTIONS: 15%, POLISH: 7%, FINAL_AUDIT: 3%

    Args:
        total_wall_clock: Total budget in seconds
        phases: Ordered phase identifiers
        default_ratios: Override ratio map

    Returns:
        Phase → seconds budget dict
    """
    ratios = default_ratios or {
        "discovery": 0.05, "tokens": 0.10, "shell": 0.10,
        "regions": 0.25, "elements": 0.25,
        "interactions": 0.15, "polish": 0.07, "final_audit": 0.03,
    }

    budget: dict[str, int] = {}
    remaining = total_wall_clock

    for i, phase in enumerate(phases):
        key = phase.lower()
        ratio = ratios.get(key, 0.10)

        if i == len(phases) - 1:
            # Last phase gets remaining (to account for rounding)
            phase_budget = max(60, remaining)
        else:
            phase_budget = max(60, int(total_wall_clock * ratio))
            remaining -= phase_budget

        budget[phase] = phase_budget

    return budget
