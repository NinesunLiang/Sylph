"""CarrorOS Benchmark — 数据结构定义

All schemas used across the benchmark framework.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ─── Enums ───

class AblationGroup(str, Enum):
    A_BARE = "A_bare"
    B_ENTRY_PROMPT = "B_entry_prompt"
    C_ROUTING_KERNEL = "C_routing_kernel"
    D_WITHOUT_HARNESS = "D_without_harness"
    E_FULL = "E_full"
    F_FULL_FIXED_BUDGET = "F_full_fixed_budget"
    G_FULL_TEST_TIME_SCALING = "G_full_test_time_scaling"


class Stack(str, Enum):
    CLAUDE_CODE = "claude-code"
    OPENCODE = "opencode"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADVERSARIAL = "adversarial"


class FailureClass(str, Enum):
    NONE = "none"                           # Verified success
    FUNCTIONAL_FAIL = "functional_fail"     # Visible tests failed
    HIDDEN_TEST_FAIL = "hidden_test_fail"   # Hidden tests failed
    REGRESSION = "regression"               # Regression introduced
    CONSTRAINT_VIOLATION = "constraint_violation"
    BUDGET_EXCEEDED = "budget_exceeded"
    GOVERNANCE_VIOLATION = "governance_violation"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    TIMEOUT = "timeout"
    STATE_LOST = "state_lost"
    COMPACT_FAILURE = "compact_failure"
    CRITICAL_ERROR = "critical_error"
    OTHER = "other"


# ─── Task Definition ───

@dataclass
class TaskDefinition:
    """A single benchmark task."""
    task_id: str
    category: str                  # e.g. "01_repo_locate"
    difficulty: Difficulty
    title: str
    description: str               # Task prompt (must not leak solution)
    repo_url: str
    repo_commit: str               # Fixed commit SHA
    allowed_files: list[str]       # Glob patterns for editable files
    forbidden_files: list[str]     # Glob patterns for protected files
    max_tool_calls: int
    max_wall_time_seconds: int
    verify_script: str             # Path to hidden verification script
    build_command: str | None = None
    lint_command: str | None = None
    test_command: str | None = None
    depends_on: list[str] = field(default_factory=list)  # Prerequisite task IDs
    seeds: list[int] = field(default_factory=lambda: [1, 2, 3])


# ─── Experiment Run ───

@dataclass
class Budget:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    max_tool_calls: int = 0
    actual_tool_calls: int = 0
    wall_time_seconds: int = 0
    cost_usd: float = 0.0


@dataclass
class Routing:
    expected_workflow: str = ""
    selected_workflow: str = ""
    first_path_correct: bool = False
    route_switches: int = 0
    irrelevant_docs_loaded: int = 0
    time_to_first_correct_hypothesis_s: float = 0.0
    tool_calls_before_first_evidence: int = 0


@dataclass
class Context:
    context_peak_ratio: float = 0.0
    checkpoints: int = 0
    lossless_compactions: int = 0
    l5_lossy_compactions: int = 0
    stable_prefix: bool = False
    cache_hit_rate: float | None = None
    artifacts_written: int = 0
    artifacts_missing: int = 0
    preview_stability: float = 1.0


@dataclass
class Recovery:
    forced_interruptions: int = 0
    successful_resumes: int = 0
    duplicate_actions_after_resume: int = 0
    stale_state_events: int = 0
    fault_injections: int = 0
    faults_recovered: int = 0


@dataclass
class Verification:
    agent_claimed_complete: bool = False
    visible_tests_pass: bool = False
    hidden_tests_pass: bool = False
    regression_pass: bool = False
    evidence_complete: bool = False
    verify_override_attempted: bool = False
    verify_override_escaped: bool = False
    governance_violation: bool = False
    constraints_pass: bool = False


@dataclass
class ExperimentRun:
    """Single experiment run result."""
    schema_version: int = 1

    # Identity
    run_id: str = ""
    task_id: str = ""
    timestamp: str = ""
    stack: Stack = Stack.CLAUDE_CODE
    model: str = ""
    model_revision: str = ""
    provider: str = ""
    group: AblationGroup = AblationGroup.A_BARE
    seed: int = 0
    repository_commit: str = ""

    # Budget & cost
    budget: Budget = field(default_factory=Budget)

    # Routing
    routing: Routing = field(default_factory=Routing)

    # Context health
    context: Context = field(default_factory=Context)

    # Recovery
    recovery: Recovery = field(default_factory=Recovery)

    # Verification
    verification: Verification = field(default_factory=Verification)

    # Results
    verified_success: bool = False
    silent_false_success: bool = False
    human_interventions: int = 0
    failure_class: FailureClass = FailureClass.NONE
    failure_detail: str = ""
    session_transcript_path: str = ""

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "identity": {
                "run_id": self.run_id,
                "task_id": self.task_id,
                "timestamp": self.timestamp,
                "stack": self.stack.value,
                "model": self.model,
                "model_revision": self.model_revision,
                "provider": self.provider,
                "group": self.group.value,
                "seed": self.seed,
                "repository_commit": self.repository_commit,
            },
            "budget": {
                "input_tokens": self.budget.input_tokens,
                "output_tokens": self.budget.output_tokens,
                "cached_tokens": self.budget.cached_tokens,
                "max_tool_calls": self.budget.max_tool_calls,
                "actual_tool_calls": self.budget.actual_tool_calls,
                "wall_time_seconds": self.budget.wall_time_seconds,
                "cost_usd": self.budget.cost_usd,
            },
            "routing": {
                "expected_workflow": self.routing.expected_workflow,
                "selected_workflow": self.routing.selected_workflow,
                "first_path_correct": self.routing.first_path_correct,
                "route_switches": self.routing.route_switches,
                "irrelevant_docs_loaded": self.routing.irrelevant_docs_loaded,
                "time_to_first_correct_hypothesis_s": self.routing.time_to_first_correct_hypothesis_s,
                "tool_calls_before_first_evidence": self.routing.tool_calls_before_first_evidence,
            },
            "context": {
                "context_peak_ratio": self.context.context_peak_ratio,
                "checkpoints": self.context.checkpoints,
                "lossless_compactions": self.context.lossless_compactions,
                "l5_lossy_compactions": self.context.l5_lossy_compactions,
                "stable_prefix": self.context.stable_prefix,
                "cache_hit_rate": self.context.cache_hit_rate,
                "artifacts_written": self.context.artifacts_written,
                "artifacts_missing": self.context.artifacts_missing,
                "preview_stability": self.context.preview_stability,
            },
            "recovery": {
                "forced_interruptions": self.recovery.forced_interruptions,
                "successful_resumes": self.recovery.successful_resumes,
                "duplicate_actions_after_resume": self.recovery.duplicate_actions_after_resume,
                "stale_state_events": self.recovery.stale_state_events,
                "fault_injections": self.recovery.fault_injections,
                "faults_recovered": self.recovery.faults_recovered,
            },
            "verification": {
                "agent_claimed_complete": self.verification.agent_claimed_complete,
                "visible_tests_pass": self.verification.visible_tests_pass,
                "hidden_tests_pass": self.verification.hidden_tests_pass,
                "regression_pass": self.verification.regression_pass,
                "evidence_complete": self.verification.evidence_complete,
                "verify_override_attempted": self.verification.verify_override_attempted,
                "verify_override_escaped": self.verification.verify_override_escaped,
                "governance_violation": self.verification.governance_violation,
                "constraints_pass": self.verification.constraints_pass,
            },
            "result": {
                "verified_success": self.verified_success,
                "silent_false_success": self.silent_false_success,
                "human_interventions": self.human_interventions,
                "failure_class": self.failure_class.value,
                "failure_detail": self.failure_detail,
                "session_transcript_path": self.session_transcript_path,
            },
        }


# ─── Ablation Config ───

@dataclass
class AblationConfig:
    """Which CarrorOS components are enabled for a given group."""
    group: AblationGroup
    description: str

    # Core governance documents
    agents_md: bool = False
    claude_md: bool = False
    kernel_md: bool = False
    index_yaml: bool = False

    # Prompt/planning
    prompt_engine: bool = False

    # Context management
    context_engine: bool = False

    # Harness + hooks
    harness_engine: bool = False
    settings_json_hooks: bool = False
    pretool_gate_py: bool = False
    user_approve_py: bool = False

    # Workflow scripts
    carros_base_scripts: bool = False

    # Skills
    skills: bool = False

    # Error tracking
    error_dna: bool = False

    # Oracle
    oracle: bool = False

    def to_dict(self) -> dict:
        return {
            "group": self.group.value,
            "description": self.description,
            "agents_md": self.agents_md,
            "claude_md": self.claude_md,
            "kernel_md": self.kernel_md,
            "index_yaml": self.index_yaml,
            "prompt_engine": self.prompt_engine,
            "context_engine": self.context_engine,
            "harness_engine": self.harness_engine,
            "settings_json_hooks": self.settings_json_hooks,
            "pretool_gate_py": self.pretool_gate_py,
            "user_approve_py": self.user_approve_py,
            "carros_base_scripts": self.carros_base_scripts,
            "skills": self.skills,
            "error_dna": self.error_dna,
            "oracle": self.oracle,
        }


# ─── Aggregate Report ───

@dataclass
class AggregateMetrics:
    """Aggregated metrics across multiple experiment runs."""
    total_runs: int = 0
    verified_success_rate: float = 0.0
    hard_task_success_rate: float = 0.0
    first_path_correct_rate: float = 0.0
    silent_false_success_rate: float = 0.0
    regression_escape_rate: float = 0.0
    dollar_per_verified_success: float = 0.0
    cost_multiplier: float = 0.0

    # Per group
    groups: dict[str, dict] = field(default_factory=dict)

    # Per difficulty
    by_difficulty: dict[str, dict] = field(default_factory=dict)
