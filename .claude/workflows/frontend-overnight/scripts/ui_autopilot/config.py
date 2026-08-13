"""config.py — Path constants and configuration for UI Autopilot v2.

Centralizes all file paths so the orchestrator and scripts share a single
source of truth. Compatible with CarrorOS .omc/ path conventions.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Project Root Resolution ────────────────────────────────────────────────────

# Resolve project root from this file's location:
#   .claude/workflows/frontend-overnight/scripts/ui_autopilot/config.py
THIS_FILE = Path(__file__).resolve()
AUTOPILOT_DIR = THIS_FILE.parent
SCRIPTS_DIR = AUTOPILOT_DIR.parent
WORKFLOW_DIR = SCRIPTS_DIR.parent
CLAUDE_DIR = WORKFLOW_DIR.parent.parent
PROJECT_ROOT = CLAUDE_DIR.parent  # Carror_Base_OS root

# ── Workflow Paths ─────────────────────────────────────────────────────────────

WORKFLOW_CONFIG_DIR = WORKFLOW_DIR  # .claude/workflows/frontend-overnight/
GOAL_MANIFEST_TEMPLATE = WORKFLOW_CONFIG_DIR / "goal-manifest.template.yaml"
NIGHT_LOOP_MD = WORKFLOW_CONFIG_DIR / "night-loop.md"
README_MD = WORKFLOW_CONFIG_DIR / "README.md"
SOP_MD = WORKFLOW_CONFIG_DIR / "SOP.md"
PHASE0_CHECKLIST_MD = WORKFLOW_CONFIG_DIR / "phase0-checklist.md"

# ── CarrorOS Ecosystem Paths ────────────────────────────────────────────────────

CARROTOROS_GATES_DIR = PROJECT_ROOT / ".claude" / "workflows" / "frontend-overnight" / "scripts" / "carroros-gates"
LX_GOAL_DIR = CLAUDE_DIR / "skills" / "lx-goal"
LX_GOAL_SCRIPT = LX_GOAL_DIR / "scripts" / "lx-goal.py"
CARROS_BASE_SCRIPT = CLAUDE_DIR / "scripts" / "carros_base.py"

# CarrorOS gate scripts (read-only, not modified)
SCOPE_CHECK = CARROTOROS_GATES_DIR / "scope_check.py"
RUN_GATE = CARROTOROS_GATES_DIR / "run_gate.py"
C7_CHECK = CARROTOROS_GATES_DIR / "c7_check.py"           # Names the file; semantically C3 style constraints
STYLE_CHECK = CARROTOROS_GATES_DIR / "c7_check.py"        # C3: style constraints (raw values/px/!important/antd)
ABSTRACTION_CHECK = CARROTOROS_GATES_DIR / "abstraction_check.py"  # C3 supplement: component abstraction
EVIDENCE_CHECK = CARROTOROS_GATES_DIR / "evidence_check.py"         # C7: evidence chain completeness
FINALIZE_PAGE = CARROTOROS_GATES_DIR / "finalize_page.py"           # C8a: finalize from gate-results
CONTROL_PLANE_LOCK_GEN = CARROTOROS_GATES_DIR / "gen_control_plane_lock.py"
ASSERTION_CATALOG = CARROTOROS_GATES_DIR / "assertion-catalog.yaml"
GATE_CONTRACT = CARROTOROS_GATES_DIR / "gate-contract.yaml"

# ── Runtime Paths (.omc/) ──────────────────────────────────────────────────────

OMC_DIR = PROJECT_ROOT / ".omc"
OMC_TASKS = OMC_DIR / "tasks"
OMC_STATE = OMC_DIR / "state"
OMC_TOKENS = OMC_DIR / "tokens"
OMC_AUDIT = OMC_DIR / "audit"

# Autopilot runtime directory
AUTOPILOT_RUN_DIR = OMC_DIR / "ui-autopilot"

# lx-goal signal files
LXGOAL_TOKEN = OMC_STATE / "tokens" / "lx-goal.json"
AUTONOMOUS_ACTIVE = OMC_STATE / "tokens" / "autonomous.active"

# ── Prototype Input Paths ──────────────────────────────────────────────────────

INPUTS_DIR = PROJECT_ROOT / "inputs"
PROTOTYPE_DIR = INPUTS_DIR / "prototype"
MODULES_DIR = PROTOTYPE_DIR / "modules"  # User's static module screenshots

# ── Default Target Repo ────────────────────────────────────────────────────────

DEFAULT_TARGET_REPO = "packages/carroros-base"

# ── Timing Constants ───────────────────────────────────────────────────────────

DEFAULT_WALL_CLOCK_SECONDS = 21600   # 6 hours
GRACEFUL_SHUTDOWN_SECONDS = 300      # 5 min reserve for final audit
CHECKPOINT_EVERY_SECONDS = 60        # Save state every minute
HEARTBEAT_EVERY_SECONDS = 120        # Write heartbeat for liveness check

# ── Budget Constants ───────────────────────────────────────────────────────────

MAX_TOTAL_ITERATIONS = 120
MAX_TARGET_ATTEMPTS = 8
MAX_CONSECUTIVE_NO_PROGRESS = 4

# ── Model Routing ──────────────────────────────────────────────────────────────
def _model_from_env(role: str) -> str:
    """Resolve a Claude model role from the session environment."""
    role_var = f"ANTHROPIC_DEFAULT_{role.upper()}_MODEL"
    return os.environ.get(role_var) or os.environ.get("ANTHROPIC_MODEL", role.lower())


DEFAULT_MODEL = _model_from_env("haiku")
VISUAL_MODEL = _model_from_env("sonnet")
ORCHESTRATOR_MODEL = _model_from_env("opus")
MAX_VISUAL_CALLS = 40


def get_run_dir(task_id: str) -> Path:
    """Get the runtime directory for a specific autopilot task.

    Returns: .omc/ui-autopilot/{task_id}/
    """
    return AUTOPILOT_RUN_DIR / task_id


def get_checkpoint_dir(task_id: str) -> Path:
    """Get the checkpoint directory for a task.

    Returns: .omc/ui-autopilot/{task_id}/checkpoints/
    """
    return get_run_dir(task_id) / "checkpoints"


def get_event_log_path(task_id: str) -> Path:
    """Get the event log path for a task.

    Returns: .omc/ui-autopilot/{task_id}/event-log.jsonl
    """
    return get_run_dir(task_id) / "event-log.jsonl"


def get_score_history_path(task_id: str) -> Path:
    """Get the score history path for a task.

    Returns: .omc/ui-autopilot/{task_id}/score-history.jsonl
    """
    return get_run_dir(task_id) / "score-history.jsonl"


def get_run_state_path(task_id: str) -> Path:
    """Get the run state checkpoint path.

    Returns: .omc/ui-autopilot/{task_id}/run-state.json
    """
    return get_run_dir(task_id) / "run-state.json"


def ensure_run_dir(task_id: str) -> Path:
    """Create and return the run directory for a task."""
    run_dir = get_run_dir(task_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "checkpoints").mkdir(exist_ok=True)
    (run_dir / "evidence").mkdir(exist_ok=True)
    (run_dir / "diffs").mkdir(exist_ok=True)
    (run_dir / "prototype").mkdir(exist_ok=True)
    (run_dir / "implementation").mkdir(exist_ok=True)
    return run_dir
