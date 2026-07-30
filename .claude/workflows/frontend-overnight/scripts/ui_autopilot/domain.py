"""domain.py — Core data models for UI Autopilot v2.

Defines the type system shared by all orchestration modules:
  - RunStatus / Phase / TaskStatus enums
  - Score (UIF-99 7-dimension composite)
  - Task / RunState / GoalManifest dataclasses
  - Legal phase transition mappings
  - Phase entry/exit threshold structs

Design constraints:
  - All dataclasses use slots=True for memory efficiency (long 6h runs)
  - Immutable where possible (frozen=True) to prevent accidental mutation
  - JSON-serializable for checkpoint persistence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


# ── Utilities ────────────────────────────────────────────────────────────────


def utc_now() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ── Core Enums ────────────────────────────────────────────────────────────────


class RunStatus(StrEnum):
    """Top-level run lifecycle states."""
    CREATED = "created"
    PREFLIGHT = "preflight"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    EXHAUSTED = "exhausted"      # budget wall-clock / API calls consumed
    FAILED = "failed"


class Phase(StrEnum):
    """Hierarchical restoration phases. Must execute in order; gate required between each."""
    DISCOVERY = "discovery"         # L0a: prototype scanning, route enumeration
    TOKENS = "tokens"               # L0b: extract/bootstrap design tokens
    SHELL = "shell"                 # L1: app frame (sidebar/header/layout shell)
    REGIONS = "regions"             # L2–L3: region-by-region layout & positioning
    ELEMENTS = "elements"           # L4: per-element typography/color/decoration
    INTERACTIONS = "interactions"   # L5: hover/click/scroll/overlay matrix
    POLISH = "polish"               # L6: cross-page consistency, proto.*→semantic migration
    FINAL_AUDIT = "final_audit"     # terminal: full gate chain verification


# Legal forward transitions (linear, with regression arcs handled by should_regress())
PHASE_TRANSITIONS: dict[Phase, Phase] = {
    Phase.DISCOVERY: Phase.TOKENS,
    Phase.TOKENS: Phase.SHELL,
    Phase.SHELL: Phase.REGIONS,
    Phase.REGIONS: Phase.ELEMENTS,
    Phase.ELEMENTS: Phase.INTERACTIONS,
    Phase.INTERACTIONS: Phase.POLISH,
    Phase.POLISH: Phase.FINAL_AUDIT,
}


class TaskStatus(StrEnum):
    """Single bounded-task lifecycle states."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    VERIFYING = "verifying"
    PASSED = "passed"
    RETRYABLE = "retryable"
    ESCALATED = "escalated"        # escalated to Kimi K3 or human
    BLOCKED = "blocked"
    FAILED = "failed"


class ConvergenceStatus(StrEnum):
    """EMA-based improvement-rate states (Opus convergence tracker)."""
    PROGRESSING = "progressing"         # EMA stable positive, continue
    DECELERATING = "decelerating"       # EMA shrinking but positive, switch to precision
    STAGNANT = "stagnant"              # EMA near zero, trigger root-cause diagnosis
    OSCILLATING = "oscillating"        # score oscillates, lock direction
    CONVERGED = "converged"            # score above threshold + EMA stable
    DIVERGING = "diverging"            # score decreasing, emergency rollback


# ── Score Model ────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Score:
    """UIF-99 seven-dimension composite score.

    Dimensions D1-D7 follow the Grok UIF-99 specification:
      D1 Geometry (0.16)  — region IoU + critical edge delta
      D2 Color (0.12)     — LAB ΔE against token ladder
      D3 Typography (0.10)— font-size/weight/line-height
      D4 Decoration (0.08)— radius/border/shadow
      D5 Layout (0.12)    — flex/grid/gap/overflow
      D6 TokenAlign (0.18)— token-index hit rate, raw-value detection
      D7 Interaction (0.24)— assertion catalog pass rate

    Hard gates:
      H1 Engineering — C1+C2+C3 all pass
      H2 Evidence    — evidence_check passes
    """
    global_similarity: float = 0.0
    geometry: float = 0.0           # D1
    color: float = 0.0              # D2
    typography: float = 0.0         # D3
    decoration: float = 0.0         # D4
    layout: float = 0.0             # D5
    token_align: float = 0.0        # D6
    interaction: float = 0.0        # D7

    minimum_region_similarity: float = 0.0
    interaction_coverage: float = 0.0     # 0.0–1.0, must be 1.0 for UIF-99
    state_coverage: float = 0.0
    route_coverage: float = 0.0
    scroll_coverage: float = 0.0

    runtime_errors: int = 0
    console_errors: int = 0

    # Hard gate flags
    h1_engineering_pass: bool = False
    h2_evidence_pass: bool = False

    def uif_composite(self) -> float:
        """Compute UIF-99 weighted composite score.

        Returns:
            float in [0.0, 1.0]. Capped at 0.94 if interaction coverage < 1.0.
            Returns 0.0 if hard gates fail.
        """
        if not self.h1_engineering_pass or not self.h2_evidence_pass:
            return 0.0

        visual = (
            self.geometry * 0.16
            + self.color * 0.12
            + self.typography * 0.10
            + self.decoration * 0.08
            + self.layout * 0.12
            + self.token_align * 0.18
            + self.interaction * 0.24
        )

        completeness = min(
            self.interaction_coverage,
            self.state_coverage,
            self.route_coverage,
            self.scroll_coverage,
        )

        composite = visual * 0.85 + completeness * 0.15

        # Hard cap: interaction coverage < 100% → max 0.94
        if self.interaction_coverage < 1.0:
            composite = min(composite, 0.94)

        return max(0.0, min(1.0, composite))

    def is_goal_met(self, threshold: float = 0.99) -> bool:
        """Check if UIF-99 goal is met."""
        return (
            self.uif_composite() >= threshold
            and self.interaction_coverage >= 1.0
            and self.state_coverage >= 1.0
            and self.h1_engineering_pass
            and self.h2_evidence_pass
        )


# ── Region Model ───────────────────────────────────────────────────────────────


@dataclass(slots=True)
class RegionGold:
    """Gold-standard region definition from prototype module screenshots.

    Each region corresponds to a module in the user's static screenshot document.
    """
    id: str
    gold_image_path: str
    states: list[str] = field(default_factory=lambda: ["default"])
    weight: float = 0.0
    capture: dict[str, str] = field(default_factory=dict)  # trigger/target for interaction
    is_critical: bool = False
    bbox: dict[str, int] | None = None  # {x, y, width, height} if annotated


@dataclass(slots=True)
class RegionScore:
    """Per-region score breakdown."""
    region_id: str
    state: str
    geometry: float = 0.0
    color: float = 0.0
    typography: float = 0.0
    decoration: float = 0.0
    layout: float = 0.0
    token_align: float = 0.0
    interaction: float = 0.0
    composite: float = 0.0  # weighted sum

    def compute(self, weights: dict[str, float] | None = None) -> float:
        w = weights or {
            "geometry": 0.20, "color": 0.15, "typography": 0.12,
            "decoration": 0.10, "layout": 0.15, "token_align": 0.18,
            "interaction": 0.10,
        }
        self.composite = (
            self.geometry * w["geometry"]
            + self.color * w["color"]
            + self.typography * w["typography"]
            + self.decoration * w["decoration"]
            + self.layout * w["layout"]
            + self.token_align * w["token_align"]
            + self.interaction * w["interaction"]
        )
        return self.composite


# ── Task Model ─────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Task:
    """A single bounded repair task for a model worker.

    Each task targets exactly one region/state/phase combination
    and has a strictly bounded allowed_files set.
    """
    id: str
    phase: Phase
    target_id: str
    target_type: str = "region"         # "region" | "element" | "overlay" | "token_proposal"
    status: TaskStatus = TaskStatus.PENDING
    priority: float = 0.0
    attempts: int = 0
    stagnation_count: int = 0
    max_attempts: int = 8
    allowed_files: list[str] = field(default_factory=list)
    prohibited_patterns: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    last_error: str | None = None
    root_cause_hint: str | None = None
    measurements: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_retry(self) -> bool:
        return self.attempts < self.max_attempts and self.status in (
            TaskStatus.RETRYABLE, TaskStatus.FAILED
        )


# ── Run State ──────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class RunState:
    """Persistent run state. Serialized to JSON for checkpoint/restore.

    This is the single source of truth for the orchestrator's current position.
    """
    run_id: str
    task_name: str
    status: RunStatus = RunStatus.CREATED
    phase: Phase = Phase.DISCOVERY

    started_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    iteration: int = 0
    current_task_id: str | None = None
    task_queue: list[str] = field(default_factory=list)          # ordered task IDs
    completed_tasks: list[str] = field(default_factory=list)

    best_score: Score = field(default_factory=Score)
    latest_score: Score = field(default_factory=Score)

    consecutive_no_progress: int = 0
    consecutive_stagnant: int = 0
    consecutive_diverging: int = 0

    last_checkpoint: str | None = None
    blocker: dict[str, Any] | None = None

    # Budget tracking
    wall_clock_start: float = 0.0              # UTC timestamp for started_at
    wall_clock_deadline_utc: float = 0.0       # UTC timestamp for deadline
    wall_clock_budget_seconds: int = 21600     # 6h default
    kimi_calls_used: int = 0
    kimi_calls_budget: int = 40
    total_model_calls: int = 0

    # Pages tracked
    pages: list[str] = field(default_factory=list)
    current_page: str = ""
    regions: list[RegionGold] = field(default_factory=list)

    # Convergence state (GAP 7 fix)
    convergence_state: dict[str, Any] | None = None

    # Candidate workspace (P0-2 fix)
    candidate_workspace: dict[str, Any] | None = None

    def touch(self) -> None:
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "run_id": self.run_id,
            "task_name": self.task_name,
            "status": str(self.status),
            "phase": str(self.phase),
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "iteration": self.iteration,
            "current_task_id": self.current_task_id,
            "task_queue": self.task_queue,
            "completed_tasks": self.completed_tasks,
            "best_score": self._score_to_dict(self.best_score),
            "latest_score": self._score_to_dict(self.latest_score),
            "consecutive_no_progress": self.consecutive_no_progress,
            "consecutive_stagnant": self.consecutive_stagnant,
            "consecutive_diverging": self.consecutive_diverging,
            "last_checkpoint": self.last_checkpoint,
            "blocker": self.blocker,
            "wall_clock_start": self.wall_clock_start,
            "wall_clock_deadline_utc": self.wall_clock_deadline_utc,
            "wall_clock_budget_seconds": self.wall_clock_budget_seconds,
            "kimi_calls_used": self.kimi_calls_used,
            "kimi_calls_budget": self.kimi_calls_budget,
            "total_model_calls": self.total_model_calls,
            "pages": self.pages,
            "current_page": self.current_page,
            "regions": [
                {
                    "id": r.id,
                    "gold_image_path": r.gold_image_path,
                    "states": r.states,
                    "weight": r.weight,
                    "is_critical": r.is_critical,
                }
                for r in self.regions
            ],
            "convergence_state": self.convergence_state,
            "candidate_workspace": self.candidate_workspace,
        }

    @staticmethod
    def _score_to_dict(s: Score) -> dict[str, Any]:
        return {
            "global_similarity": s.global_similarity,
            "geometry": s.geometry, "color": s.color,
            "typography": s.typography, "decoration": s.decoration,
            "layout": s.layout, "token_align": s.token_align,
            "interaction": s.interaction,
            "minimum_region_similarity": s.minimum_region_similarity,
            "interaction_coverage": s.interaction_coverage,
            "state_coverage": s.state_coverage,
            "route_coverage": s.route_coverage,
            "scroll_coverage": s.scroll_coverage,
            "runtime_errors": s.runtime_errors,
            "console_errors": s.console_errors,
            "h1_engineering_pass": s.h1_engineering_pass,
            "h2_evidence_pass": s.h2_evidence_pass,
            "uif_composite": s.uif_composite(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunState":
        """Deserialize from dict (checkpoint restore)."""
        bs = d.get("best_score", {})
        ls = d.get("latest_score", {})

        state = cls(
            run_id=d["run_id"],
            task_name=d.get("task_name", ""),
            status=RunStatus(d["status"]),
            phase=Phase(d["phase"]),
            started_at=d.get("started_at", utc_now()),
            updated_at=d.get("updated_at", utc_now()),
            iteration=d.get("iteration", 0),
            current_task_id=d.get("current_task_id"),
            task_queue=d.get("task_queue", []),
            completed_tasks=d.get("completed_tasks", []),
            best_score=Score(**{k: bs.get(k, 0.0) for k in Score.__dataclass_fields__}),
            latest_score=Score(**{k: ls.get(k, 0.0) for k in Score.__dataclass_fields__}),
            consecutive_no_progress=d.get("consecutive_no_progress", 0),
            consecutive_stagnant=d.get("consecutive_stagnant", 0),
            consecutive_diverging=d.get("consecutive_diverging", 0),
            last_checkpoint=d.get("last_checkpoint"),
            blocker=d.get("blocker"),
            wall_clock_start=d.get("wall_clock_start", 0.0),
            wall_clock_deadline_utc=d.get("wall_clock_deadline_utc", 0.0),
            wall_clock_budget_seconds=d.get("wall_clock_budget_seconds", 21600),
            kimi_calls_used=d.get("kimi_calls_used", 0),
            kimi_calls_budget=d.get("kimi_calls_budget", 40),
            total_model_calls=d.get("total_model_calls", 0),
            pages=d.get("pages", []),
            current_page=d.get("current_page", ""),
            regions=[RegionGold(**r) for r in d.get("regions", [])],
            convergence_state=d.get("convergence_state"),
            candidate_workspace=d.get("candidate_workspace"),
        )
        return state


@dataclass(slots=True)
class CandidateWorkspace:
    """Candidate workspace for isolated Gate validation (P0-2 fix).

    Uses git worktree to create isolated copy where worker can modify files.
    Gate failure → remove worktree, main tree untouched.
    Gate pass → merge changes back to main tree, remove worktree.
    """
    worktree_path: str
    branch_name: str
    created_at: str
    patch_id: str  # Unique ID for this patch attempt


# ── Goal Manifest ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class GoalManifestViewport:
    id: str
    width: int
    height: int
    device_scale_factor: float = 1.0
    required: bool = True


@dataclass(slots=True)
class GoalManifestRoute:
    id: str
    prototype_path: str
    implementation_path: str


@dataclass(slots=True)
class GoalManifestDiscovery:
    scroll_enabled: bool = True
    capture_full_page: bool = True
    step_ratio: float = 0.75
    settle_ms: int = 400
    hover_enabled: bool = True
    click_enabled: bool = True
    destructive_actions: str = "deny"
    overlays_required: bool = True
    sidebar_states: list[str] = field(default_factory=lambda: ["expanded", "collapsed"])


@dataclass(slots=True)
class GoalManifestAcceptance:
    route_coverage: float = 1.0
    interaction_coverage: float = 1.0
    state_coverage: float = 1.0
    scroll_coverage: float = 1.0
    global_similarity: float = 0.99
    minimum_region_similarity: float = 0.985
    critical_region_similarity: float = 0.995
    geometry_score: float = 0.995
    typography_score: float = 0.99
    color_score: float = 0.99
    token_compliance: float = 1.0
    console_errors: int = 0
    runtime_errors: int = 0
    required_gates: list[str] = field(default_factory=lambda: [
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8a",
    ])


@dataclass(slots=True)
class GoalManifestModelRouting:
    default_model: str = "deepseek-v4-flash"
    visual_model: str = "kimi-k3"
    max_visual_calls: int = 40
    orchestration_model: str = "deepseek-v4-pro"


@dataclass(slots=True)
class GoalManifestSafety:
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=list)
    max_files_per_patch: int = 8
    max_changed_lines_per_patch: int = 400
    rollback_on_regression: bool = True


@dataclass(slots=True)
class GoalManifest:
    """Machine-readable goal contract. Replaces ambiguous natural-language goals.

    All run parameters: budget, prototype config, acceptance thresholds,
    model routing, safety constraints — in one file.
    """
    schema_version: int = 2
    run_id: str = ""
    task_name: str = ""
    mode: str = "goal"
    unattended: bool = True

    target_repo: str = ""
    prototype_base_url: str = ""

    budget_wall_clock_seconds: int = 21600
    budget_max_iterations: int = 120
    budget_max_target_attempts: int = 8
    budget_max_consecutive_no_progress: int = 4
    budget_checkpoint_every_seconds: int = 60

    viewports: list[GoalManifestViewport] = field(default_factory=list)
    routes: list[GoalManifestRoute] = field(default_factory=list)
    discovery: GoalManifestDiscovery = field(default_factory=GoalManifestDiscovery)
    acceptance: GoalManifestAcceptance = field(default_factory=GoalManifestAcceptance)
    model_routing: GoalManifestModelRouting = field(default_factory=GoalManifestModelRouting)
    safety: GoalManifestSafety = field(default_factory=GoalManifestSafety)

    screenshot_document: str = ""
    additional_screenshots: list[str] = field(default_factory=list)
    token_set_hash: str = ""


# ── Phase Thresholds ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PhaseThresholds:
    """Per-phase score and coverage thresholds (Grok L0-L6 Hierarchy Gate).

    Each phase declares what dimensions matter and their minimum thresholds.
    """
    phase: Phase
    d1_d5_min: float = 0.0         # geometry/color/typography/decoration/layout
    d6_token_min: float = 0.0       # token alignment
    d7_interaction_min: float = 0.0 # interaction coverage
    state_coverage_required: bool = False
    description: str = ""


# Threshold table aligned with plan §IV (分阶段阈值)
PHASE_THRESHOLDS: dict[Phase, PhaseThresholds] = {
    Phase.DISCOVERY: PhaseThresholds(
        phase=Phase.DISCOVERY,
        description="Route enumeration, state inventory, scroll coverage",
    ),
    Phase.TOKENS: PhaseThresholds(
        phase=Phase.TOKENS,
        d6_token_min=0.80,         # ladder exists, codegen builds
        description="Token bootstrap complete, codegen produces valid output",
    ),
    Phase.SHELL: PhaseThresholds(
        phase=Phase.SHELL,
        d1_d5_min=0.95,
        d6_token_min=0.97,
        d7_interaction_min=1.0,   # shell states (expand/collapse) must be 100%
        description="Shell geometry ≥ 0.95, sidebar multi-state 100%",
    ),
    Phase.REGIONS: PhaseThresholds(
        phase=Phase.REGIONS,
        d1_d5_min=0.97,
        d6_token_min=0.98,
        d7_interaction_min=0.50,  # region-related interactions tracked
        description="Per-region composite ≥ 0.97, no missing required regions",
    ),
    Phase.ELEMENTS: PhaseThresholds(
        phase=Phase.ELEMENTS,
        d1_d5_min=0.98,
        d6_token_min=0.99,         # raw values near zero
        d7_interaction_min=0.50,
        description="Element visual ≥ 0.98, token compliance ≥ 0.99",
    ),
    Phase.INTERACTIONS: PhaseThresholds(
        phase=Phase.INTERACTIONS,
        d1_d5_min=0.97,
        d6_token_min=0.98,
        d7_interaction_min=1.0,   # interaction checklist MUST be 100%
        state_coverage_required=True,
        description="All hover/click/scroll/overlay interactions pass",
    ),
    Phase.POLISH: PhaseThresholds(
        phase=Phase.POLISH,
        d1_d5_min=0.99,
        d6_token_min=0.99,
        d7_interaction_min=1.0,
        description="Cross-page consistency, proto.*→semantic migration, UIF-99",
    ),
    Phase.FINAL_AUDIT: PhaseThresholds(
        phase=Phase.FINAL_AUDIT,
        d1_d5_min=0.99,
        d6_token_min=0.99,
        d7_interaction_min=1.0,
        description="Full gate chain C1-C8a all green, final status computed",
    ),
}


# ── Event Logging ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class RunEvent:
    """Single append-only event for execution-events.jsonl."""
    ts: str
    event: str                      # page_start | gate_fail | fix_round | ...
    page: str | None = None
    phase: Phase | None = None
    task_id: str | None = None
    score: float | None = None
    convergence: ConvergenceStatus | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        import json
        return json.dumps({
            "ts": self.ts,
            "event": self.event,
            "page": self.page,
            "phase": str(self.phase) if self.phase else None,
            "task_id": self.task_id,
            "score": self.score,
            "convergence": str(self.convergence) if self.convergence else None,
            "detail": self.detail,
        }, ensure_ascii=False)
