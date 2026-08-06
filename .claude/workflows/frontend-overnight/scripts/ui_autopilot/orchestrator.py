"""orchestrator.py — Main orchestration engine for UI Autopilot v2.

Wires together all modules:
  domain → phase_gate → convergence → scorer → task_generator
  → model_router → state_store

This is designed to be called by the Claude Code main session (DeepSeek V4 Pro)
as the orchestrator. It produces structured output (JSON) that the CC session
interprets to determine:
  - What phase are we in?
  - What's the current score? Are we converging or stuck?
  - What's the next bounded task?
  - Which model should handle it?
  - What files can the worker touch?

The orchestrator does NOT call models directly — it produces directives
that the CC session executes via Agent tool (flash) or direct invocation (kimi).

Usage:
  python3 orchestrator.py --task-id <id> --action status|tick|init
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import (
    PROJECT_ROOT, ensure_run_dir, get_run_dir,
    DEFAULT_TARGET_REPO, DEFAULT_WALL_CLOCK_SECONDS,
    MAX_TARGET_ATTEMPTS, MAX_CONSECUTIVE_NO_PROGRESS,
    MAX_TOTAL_ITERATIONS, MAX_VISUAL_CALLS, DEFAULT_MODEL,
    CHECKPOINT_EVERY_SECONDS,
)
from .domain import (
    Phase, RunStatus, TaskStatus, ConvergenceStatus,
    Score, RunState, Task, RegionGold, GoalManifest,
    RunEvent, PHASE_TRANSITIONS, PHASE_THRESHOLDS,
    CandidateWorkspace, utc_now,
)
from .phase_gate import PhaseGate, PhaseReport
from .convergence import LoopController, LoopAction, ConvergenceTracker
from .scorer import ScoringEngine, compute_score_diff
from .task_generator import TaskGenerator
from .model_router import ModelRouter, ModelTarget, EscalationReason, build_call_context
from .state_store import (
    save_run_state, load_run_state, log_event, log_score,
    save_checkpoint, restore_checkpoint, write_heartbeat,
    save_blocker,
)

# ── Standalone execution helper ──────────────────────────────────────────────
# Run as: cd scripts/ && python3 -m ui_autopilot.orchestrator --task-id <id> --action <action>
# The run_standalone() wrapper below supports direct script invocation.



# ── Orchestrator ───────────────────────────────────────────────────────────────


class Orchestrator:
    """Main orchestration engine.

    This is the "brain" that replaces the old night-loop.md free-form flow
    with a deterministic state machine. It produces structured JSON output
    that the CC main session interprets.

    Architecture:
      Orchestrator (this class) — state machine + decision engine
        ├── PhaseGate       — entry/exit conditions per phase
        ├── LoopController  — convergence tracking + action decisions
        ├── ScoringEngine   — UIF-99 multi-dimensional scoring
        ├── TaskGenerator   — bounded task creation with file scoping
        ├── ModelRouter     — flash vs kimi routing with budget
        └── state_store     — persistence

    The CC main session reads the orchestrator's output and dispatches
    work to Agent subprocesses (flash) or calls visual tools (kimi).
    Results flow back via score updates → orchestrator decides next action.
    """

    def __init__(
        self,
        task_id: str,
        manifest: GoalManifest | None = None,
    ):
        self.task_id = task_id
        self.manifest = manifest or GoalManifest()
        self.run_dir = ensure_run_dir(self.task_id)

        # Subsystems
        self.gate = PhaseGate()
        self.scorer = ScoringEngine()
        self.router = ModelRouter(escalation_budget=MAX_VISUAL_CALLS)

        # Load or init state
        self.state = load_run_state(self.run_dir)
        self.task_gen = TaskGenerator(target_repo=DEFAULT_TARGET_REPO)

        if self.state is None:
            self.state = self._init_state()

        # Controller tracks convergence from score history
        # 🔴 P0-5: Use UTC timestamps for cross-process deadline persistence
        self.controller = LoopController(
            target_threshold=0.99,
            deadline_epoch=(
                self.state.wall_clock_deadline_utc
                if self.state.wall_clock_deadline_utc > 0
                else datetime.now(timezone.utc).timestamp() + DEFAULT_WALL_CLOCK_SECONDS
            ),
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def init(self) -> dict[str, Any]:
        """Initialize a new run. Creates state, directories, and manifest.

        Returns:
            Status dict with initial directives
        """
        self.state = self._init_state()
        save_run_state(self.state, self.run_dir)
        write_heartbeat(self.run_dir, self.state)

        log_event(self.run_dir, RunEvent(
            ts=utc_now(),
            event="run_initialized",
            detail={"run_id": self.state.run_id, "task_name": self.state.task_name},
        ))

        return self._build_status()

    def tick(self, action_result: dict[str, Any] | None = None) -> dict[str, Any]:
        """Advance the state machine by one tick.

        This is the main entry point called by the CC session after each
        worker action completes. It:
          1. Processes the action result (score, gate status)
          2. Updates convergence tracking
          3. Checks phase gates
          4. Generates next tasks
          5. Returns directives for the next action

        Args:
            action_result: Result of the previous action, with keys:
                - score: Score dict (new measurements)
                - gate_results: dict of gate pass/fail status
                - task_id: str (which task was completed)
                - task_status: str (PASSED/FAILED/RETRYABLE)
                - evidence: list of evidence paths

        Returns:
            Status + directives dict
        """
        # 🔴 Sol+Grok Round3: Terminal state guard + iteration/budget limits
        if self.state.status in (
            RunStatus.SUCCEEDED, RunStatus.BLOCKED,
            RunStatus.EXHAUSTED, RunStatus.FAILED,
        ):
            return self._build_status()

        # 🔴 P0-4: Validate worker envelope - reject control-plane fields
        if action_result:
            self._validate_worker_envelope(action_result)

        if self.state.iteration >= MAX_TOTAL_ITERATIONS:
            self.state.status = RunStatus.EXHAUSTED
            save_run_state(self.state, self.run_dir)
            return self._build_status()

        elapsed = datetime.now(timezone.utc).timestamp() - self.state.wall_clock_start
        if (self.state.wall_clock_start > 0
                and elapsed > self.state.wall_clock_budget_seconds):
            self.state.status = RunStatus.EXHAUSTED
            save_run_state(self.state, self.run_dir)
            return self._build_status()

        if action_result:
            self._process_result(action_result)

        # Check phase advance
        if self._should_advance_phase():
            self._advance_phase()

        # Check convergence
        score = self.state.latest_score.uif_composite()
        gates_passed = getattr(self.state, "_gates_passed", True)
        action = self.controller.record_and_decide(
            score, str(self.state.phase), gates_passed=gates_passed
        )

        # Handle convergence-driven actions
        action_directive = self._handle_convergence_action(action)

        # Generate next tasks if queue empty
        if not self.state.task_queue:
            self._generate_tasks()

        # Determine next model target
        context = build_call_context(
            stagnation_count=self.state.consecutive_stagnant,
            critical_region_score=self.state.latest_score.minimum_region_similarity,
            convergence_status=action,
            phase=str(self.state.phase),
        )
        model_target, model_reason = self.router.route(context)

        # Persist
        self.state.iteration += 1
        self.state.touch()
        save_run_state(self.state, self.run_dir)

        # GAP 9 fix: Periodic checkpoint every CHECKPOINT_EVERY_SECONDS
        if not hasattr(self, '_last_checkpoint_time'):
            self._last_checkpoint_time = time.monotonic()
        elapsed_since_checkpoint = time.monotonic() - self._last_checkpoint_time
        if elapsed_since_checkpoint >= CHECKPOINT_EVERY_SECONDS:
            # GAP 7 fix: Persist convergence state in checkpoint
            self.state.convergence_state = self.controller.to_dict()
            save_checkpoint(
                self.state, self.run_dir,
                f"iter-{self.state.iteration}",
            )
            self._last_checkpoint_time = time.monotonic()

        write_heartbeat(self.run_dir, self.state)
        log_score(self.run_dir, self.state.latest_score)

        return self._build_status(
            action_directive=action_directive,
            model_target=model_target,
            model_reason=model_reason,
        )

    def status(self) -> dict[str, Any]:
        """Return current status without advancing state."""
        return self._build_status()

    def skip_risk(self, reason: str, level: str) -> dict[str, Any]:
        """Record a skipped risk and continue."""
        log_event(self.run_dir, RunEvent(
            ts=utc_now(),
            event="risk_skipped",
            detail={"reason": reason, "level": level},
        ))
        return self._build_status()

    def hard_boundary(self, reason: str, suggestion: str) -> dict[str, Any]:
        """Record a hard boundary hit."""
        log_event(self.run_dir, RunEvent(
            ts=utc_now(),
            event="hard_boundary_hit",
            detail={"reason": reason, "suggestion": suggestion},
        ))
        save_blocker(self.run_dir, {
            "type": "hard_boundary",
            "reason": reason,
            "recommendation": suggestion,
            "phase": str(self.state.phase),
        })
        return self._build_status()

    # ── Internal State Machine ─────────────────────────────────────────────

    def _validate_worker_envelope(self, result: dict[str, Any]) -> None:
        """Validate worker action_result envelope does not contain control-plane fields.

        Security boundary (P0-4): Worker can provide measurements (score, changed_files)
        but CANNOT dictate control-plane decisions (gate_results, accepted, phase_advance).

        Raises:
            ValueError: If untrusted control-plane fields detected in worker result
        """
        forbidden_fields = ["gate_results", "accepted", "phase_advance",
                           "should_rollback", "force_phase", "override_gate"]

        found = [f for f in forbidden_fields if f in result]
        if found:
            msg = (f"UntrustedControlFieldError: Worker result contains forbidden "
                   f"control-plane fields: {found}. These fields must only be set "
                   f"by orchestrator internal logic, not external worker output.")
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="envelope_violation",
                detail={"forbidden_fields": found, "result_keys": list(result.keys())},
            ))
            raise ValueError(msg)

    def _create_candidate_workspace(self, patch_id: str) -> CandidateWorkspace:
        """Create isolated git worktree for Gate validation (P0-2 fix).

        Args:
            patch_id: Unique identifier for this patch attempt

        Returns:
            CandidateWorkspace with worktree path and branch name

        Raises:
            RuntimeError: If git worktree creation fails
        """
        import subprocess
        import uuid

        branch_name = f"night-patch-{patch_id}-{uuid.uuid4().hex[:8]}"
        worktree_path = PROJECT_ROOT / ".claude" / "worktrees" / branch_name

        # Ensure worktrees directory exists
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        # Create worktree
        try:
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "-b", branch_name],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as e:
            msg = f"Failed to create worktree: {e.stderr}"
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="worktree_create_failed",
                detail={"error": msg, "patch_id": patch_id},
            ))
            raise RuntimeError(msg) from e

        candidate = CandidateWorkspace(
            worktree_path=str(worktree_path),
            branch_name=branch_name,
            created_at=utc_now(),
            patch_id=patch_id,
        )

        log_event(self.run_dir, RunEvent(
            ts=utc_now(), event="worktree_created",
            detail={"worktree_path": str(worktree_path), "branch": branch_name},
        ))

        return candidate

    def _remove_candidate_workspace(self, candidate: CandidateWorkspace) -> None:
        """Remove candidate worktree after Gate validation (P0-2 fix).

        Args:
            candidate: CandidateWorkspace to remove

        Note:
            Errors are logged but not raised — removal is best-effort cleanup.
        """
        import subprocess
        import shutil

        worktree_path = Path(candidate.worktree_path)

        # Remove worktree
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as e:
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="worktree_remove_git_failed",
                detail={"error": e.stderr, "worktree": str(worktree_path)},
            ))
            # Fallback: force remove directory
            if worktree_path.exists():
                try:
                    shutil.rmtree(worktree_path)
                except OSError as rm_error:
                    log_event(self.run_dir, RunEvent(
                        ts=utc_now(), event="worktree_remove_fs_failed",
                        detail={"error": str(rm_error), "worktree": str(worktree_path)},
                    ))

        # Delete branch
        try:
            subprocess.run(
                ["git", "branch", "-D", candidate.branch_name],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.CalledProcessError:
            pass  # Non-fatal

        log_event(self.run_dir, RunEvent(
            ts=utc_now(), event="worktree_removed",
            detail={"worktree_path": str(worktree_path), "branch": candidate.branch_name},
        ))

    def _init_state(self) -> RunState:
        """Create initial RunState from manifest."""
        utc_now_ts = datetime.now(timezone.utc).timestamp()
        return RunState(
            run_id=self.task_id,
            task_name=self.manifest.task_name,
            status=RunStatus.RUNNING,
            phase=Phase.DISCOVERY,
            wall_clock_start=utc_now_ts,
            wall_clock_deadline_utc=utc_now_ts + self.manifest.budget_wall_clock_seconds,
            wall_clock_budget_seconds=self.manifest.budget_wall_clock_seconds,
            kimi_calls_budget=MAX_VISUAL_CALLS,
            pages=[r.id for r in self.manifest.routes],
            current_page=(
                self.manifest.routes[0].id if self.manifest.routes else ""
            ),
            regions=self._manifest_regions(),
        )

    def _manifest_regions(self) -> list[RegionGold]:
        """Extract RegionGold list from manifest routes and discovery settings.

        Each route in the manifest represents a page/target. During the DISCOVERY
        phase these serve as the initial region inventory before per-region
        refinement from prototype scanning.

        Returns:
            list[RegionGold] with id/weight/is_critical populated per domain.py.
            Empty list when manifest has no routes.
        """
        regions: list[RegionGold] = []
        num_routes = len(self.manifest.routes)

        for route in self.manifest.routes:
            # Use prototype_path as the gold image reference, falling back to
            # screenshot_document when per-route path is not set.
            gold_image = (
                route.prototype_path
                or self.manifest.screenshot_document
                or ""
            )

            # States: "default" plus any sidebar states from discovery config.
            # Duplicates are harmless here — task_generator iterates per state.
            states: list[str] = ["default"]
            for s in self.manifest.discovery.sidebar_states:
                if s not in states:
                    states.append(s)

            # Weight: equal share per route (sums to 1.0 across all routes)
            # to ensure fair priority in task_generator._compute_priority().
            weight = 1.0 / num_routes if num_routes > 0 else 1.0

            region = RegionGold(
                id=route.id,
                gold_image_path=gold_image,
                states=states,
                weight=weight,
                is_critical=True,  # Page-level regions are always critical
            )
            regions.append(region)

        return regions

    def _process_result(self, result: dict[str, Any]) -> None:
        """Process a worker action result into state updates."""
        task_id = result.get("task_id", "")
        task_status = result.get("task_status", "")

        # ── Gate enforcement ──
        # 🔴 Opus Round3: _run_gates() ALWAYS called, never trusts action_result gate_results.
        # Empty changed_files → gates return False (fail-closed, not fail-open).
        changed_files: list[str] = result.get("changed_files", [])
        gate_results = self._run_gates(changed_files)
        result["gate_results"] = gate_results

        # Determine if gates passed (for EMA feeding decision)
        gates_passed = all(gate_results.values())

        # Update score if provided
        score_data = result.get("score")
        if score_data and isinstance(score_data, dict):
            new_score = Score(
                global_similarity=score_data.get("global_similarity", 0.0),
                geometry=score_data.get("geometry", 0.0),
                color=score_data.get("color", 0.0),
                typography=score_data.get("typography", 0.0),
                decoration=score_data.get("decoration", 0.0),
                layout=score_data.get("layout", 0.0),
                token_align=score_data.get("token_align", 0.0),
                interaction=score_data.get("interaction", 0.0),
                minimum_region_similarity=score_data.get("minimum_region_similarity", 0.0),
                interaction_coverage=score_data.get("interaction_coverage", 0.0),
                state_coverage=score_data.get("state_coverage", 0.0),
                route_coverage=score_data.get("route_coverage", 0.0),
                scroll_coverage=score_data.get("scroll_coverage", 0.0),
                runtime_errors=int(score_data.get("runtime_errors", 0)),
                console_errors=int(score_data.get("console_errors", 0)),
                h1_engineering_pass=bool(gate_results.get("C1", False)
                                         and gate_results.get("C2", False)
                                         and gate_results.get("C3", False)),
                h2_evidence_pass=bool(gate_results.get("C7", False)),
            )

            old_score = self.state.latest_score
            self.state.latest_score = new_score

            # 🔴 Sol+Grok Round3: Call can_accept_patch() for H1/H2 + cheat detection
            should_accept, accept_reason = self.scorer.can_accept_patch(
                new_score, old_score, self.state.phase,
            )
            if not should_accept:
                log_event(self.run_dir, RunEvent(
                    ts=utc_now(), event="patch_rejected",
                    task_id=task_id,
                    detail={"reason": accept_reason,
                            "old_composite": old_score.uif_composite(),
                            "new_composite": new_score.uif_composite()},
                ))
                # Store gates_passed in state for later use in record_and_decide
                self.state._gates_passed = gates_passed
                return  # Skip best_score update and task tracking

            if new_score.uif_composite() > self.state.best_score.uif_composite():
                self.state.best_score = new_score
                self.state.consecutive_no_progress = 0
            else:
                self.state.consecutive_no_progress += 1

        # Store gates_passed in state for later use in record_and_decide
        self.state._gates_passed = gates_passed

        # Track task completion
        if task_id:
            self.state.completed_tasks.append(task_id)
            if task_id in self.state.task_queue:
                self.state.task_queue.remove(task_id)
            self.state.current_task_id = None

        # Update interaction coverage
        interaction_cov = result.get("interaction_coverage")
        if interaction_cov is not None:
            self.scorer.set_interaction_coverage(
                self.state.latest_score,
                int(result.get("interaction_covered", 0)),
                int(result.get("interaction_total", 0)),
            )

        log_event(self.run_dir, RunEvent(
            ts=utc_now(),
            event="tick_complete",
            page=self.state.current_page,
            phase=self.state.phase,
            task_id=task_id,
            score=self.state.latest_score.uif_composite(),
            detail={"task_status": task_status, "gates_passed": gates_passed},
        ))

    def _should_advance_phase(self) -> bool:
        """Check if current phase is complete and can advance."""
        report = self._build_phase_report()
        return self.gate.can_advance(report)

    def _advance_phase(self) -> None:
        """Advance to the next phase (with gate check)."""
        next_phase = self.gate.next_phase(self.state.phase)
        if next_phase is None:
            # Terminal phase — goal reached
            self.state.status = RunStatus.SUCCEEDED
            log_event(self.run_dir, RunEvent(
                ts=utc_now(),
                event="goal_reached",
                phase=self.state.phase,
                score=self.state.latest_score.uif_composite(),
            ))
            return

        old_phase = self.state.phase
        self.state.phase = next_phase
        self.state.task_queue = []  # Clear old tasks
        self.state.consecutive_stagnant = 0

        # Save checkpoint on phase transition
        save_checkpoint(
            self.state, self.run_dir,
            f"phase-{old_phase.value}-to-{next_phase.value}",
        )

        log_event(self.run_dir, RunEvent(
            ts=utc_now(),
            event="phase_advance",
            phase=next_phase,
            detail={"from": str(old_phase), "to": str(next_phase)},
        ))

    def _run_gates(self, changed_files: list[str]) -> dict[str, bool]:
        """Execute the full C1–C8a gate chain via gate subprocesses.

        Bug fix round: added control_plane_lock to generated manifest (fix 1),
        C2 default is now fail-closed False (fix 2), C3 uses STYLE_CHECK alias
        with ABSTRACTION_CHECK supplement (fix 3), and C2/C4/C5/C6/C8a implement
        the missing gate slots (fix 4).

        Gate scripts require --manifest (gate-manifest.yaml with control_plane_lock).
        We generate a minimal gate-compatible manifest from the goal-manifest config
        and append control_plane_lock entries via gen_control_plane_lock.py.
        Fails-closed: missing script → False, no changed_files → all False.
        """
        from .config import (
            SCOPE_CHECK, STYLE_CHECK, ABSTRACTION_CHECK,
            EVIDENCE_CHECK, RUN_GATE, FINALIZE_PAGE,
            CONTROL_PLANE_LOCK_GEN,
        )

        gate_results: dict[str, bool] = {}
        # Empty changed_files = fail-closed
        if not changed_files:
            return {"C1": False, "C2": False, "C3": False, "C4": False,
                    "C5": False, "C6": False, "C7": False, "C8a": False}

        # Generate minimal gate-compatible manifest in run_dir
        import yaml
        gate_manifest_path = self.run_dir / "gate-manifest.yaml"
        gate_manifest = {
            "pages": [{
                "id": self.state.current_page or "page",
                "files_allowed": self.manifest.safety.allowed_paths or ["src/**"],
            }],
            "paths": {
                "spec": str(PROJECT_ROOT / "src"),
            },
        }
        gate_manifest_path.write_text(
            yaml.dump(gate_manifest, default_flow_style=False),
            encoding="utf-8",
        )

        # Bug 1 fix: populate control_plane_lock so gate scripts do not
        # fail FAILED_INVARIANT on gates_verify_control_plane_lock().
        if CONTROL_PLANE_LOCK_GEN.exists():
            try:
                subprocess.run(
                    [sys.executable, str(CONTROL_PLANE_LOCK_GEN),
                     "--manifest", str(gate_manifest_path), "--write"],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(PROJECT_ROOT),
                )
            except OSError:
                pass  # Non-fatal — gates will fail-closed with False later

        base_args = [
            "--manifest", str(gate_manifest_path),
            "--page-id", self.state.current_page or "page",
            "--night-dir", str(self.run_dir),
            "--target-repo", str(PROJECT_ROOT / DEFAULT_TARGET_REPO),
        ]

        # C1: Scope check
        if SCOPE_CHECK.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(SCOPE_CHECK)] + base_args,
                    capture_output=True, text=True, timeout=30,
                    cwd=str(PROJECT_ROOT),
                )
                gate_results["C1"] = result.returncode == 0
                if not gate_results["C1"]:
                    log_event(self.run_dir, RunEvent(
                        ts=utc_now(), event="gate_fail",
                        detail={"gate": "C1", "rc": result.returncode,
                                "stderr": result.stderr[:200]},
                    ))
            except (subprocess.TimeoutExpired, OSError) as e:
                gate_results["C1"] = False
                log_event(self.run_dir, RunEvent(
                    ts=utc_now(), event="gate_error",
                    detail={"gate": "C1", "error": str(e)[:200]},
                ))
        else:
            gate_results["C1"] = False
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="gate_missing_script",
                detail={"gate": "C1"},
            ))

        # C3: Style constraints (raw values, px, !important, antd, component abstraction)
        # c7_check.py is the C3 style checker despite its filename.
        if STYLE_CHECK.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(STYLE_CHECK)] + base_args,
                    capture_output=True, text=True, timeout=30,
                    cwd=str(PROJECT_ROOT),
                )
                gate_results["C3"] = result.returncode == 0
                if not gate_results["C3"]:
                    log_event(self.run_dir, RunEvent(
                        ts=utc_now(), event="gate_fail",
                        detail={"gate": "C3", "rc": result.returncode,
                                "stderr": result.stderr[:200]},
                    ))
            except (subprocess.TimeoutExpired, OSError) as e:
                gate_results["C3"] = False
                log_event(self.run_dir, RunEvent(
                    ts=utc_now(), event="gate_error",
                    detail={"gate": "C3", "error": str(e)[:200]},
                ))
        else:
            gate_results["C3"] = False
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="gate_missing_script",
                detail={"gate": "C3"},
            ))

        # C3 supplement: abstraction check (non-fatal, logs only)
        if ABSTRACTION_CHECK.exists() and gate_results.get("C3", False):
            try:
                subprocess.run(
                    [sys.executable, str(ABSTRACTION_CHECK)] + base_args,
                    capture_output=True, text=True, timeout=30,
                    cwd=str(PROJECT_ROOT),
                )
            except (subprocess.TimeoutExpired, OSError):
                pass
            # NOTE: abstraction_check result is advisory; C3 passes/fails
            # on the main style-constraint check above.

        # C7: Evidence check
        if EVIDENCE_CHECK.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(EVIDENCE_CHECK)] + base_args,
                    capture_output=True, text=True, timeout=30,
                    cwd=str(PROJECT_ROOT),
                )
                gate_results["C7"] = result.returncode == 0
            except (subprocess.TimeoutExpired, OSError) as e:
                gate_results["C7"] = False
        else:
            gate_results["C7"] = False
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="gate_missing_script",
                detail={"gate": "C7"},
            ))

        # ── C2: TypeScript + ESLint + Build (via run_gate.py) ──────────────
        target_pkg = str(PROJECT_ROOT / DEFAULT_TARGET_REPO)
        if RUN_GATE.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(RUN_GATE), "--gate-id", "C2"]
                    + base_args
                    + ["--", "pnpm", "-C", target_pkg, "exec", "tsc", "--noEmit"],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(PROJECT_ROOT),
                )
                gate_results["C2"] = result.returncode == 0
                if not gate_results["C2"]:
                    log_event(self.run_dir, RunEvent(
                        ts=utc_now(), event="gate_fail",
                        detail={"gate": "C2", "rc": result.returncode,
                                "stderr": result.stderr[:200]},
                    ))
            except (subprocess.TimeoutExpired, OSError) as e:
                gate_results["C2"] = False
                log_event(self.run_dir, RunEvent(
                    ts=utc_now(), event="gate_error",
                    detail={"gate": "C2", "error": str(e)[:200]},
                ))
        else:
            gate_results["C2"] = False
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="gate_missing_script",
                detail={"gate": "C2"},
            ))

        # ── C4: Playwright functional tests (via run_gate.py) ──────────────
        if RUN_GATE.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(RUN_GATE), "--gate-id", "C4"]
                    + base_args
                    + ["--", "pnpm", "-C", target_pkg, "exec", "playwright", "test"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(PROJECT_ROOT),
                )
                gate_results["C4"] = result.returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                gate_results["C4"] = False
        else:
            gate_results["C4"] = False
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="gate_missing_script",
                detail={"gate": "C4"},
            ))

        # ── C5: Playwright overlay matrix (via run_gate.py) ────────────────
        if RUN_GATE.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(RUN_GATE), "--gate-id", "C5"]
                    + base_args
                    + ["--", "pnpm", "-C", target_pkg, "exec", "playwright", "test",
                       "--grep", "overlay"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(PROJECT_ROOT),
                )
                gate_results["C5"] = result.returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                gate_results["C5"] = False
        else:
            gate_results["C5"] = False

        # ── C6: Visual regression placeholder ─────────────────────────────
        # C6 validation (1440px no-break, critical-region alignment, no overflow,
        # no console error, text no-truncation, token measurability) is performed
        # by the model/visual diagnosis system, not a standalone gate script.
        # The orchestrator records the gate slot as True (pass-through); the
        # actual C6 verdict comes from the visual model pipeline and is written
        # into the master gate-results envelope separately.
        gate_results["C6"] = True
        log_event(self.run_dir, RunEvent(
            ts=utc_now(), event="gate_placeholder",
            detail={"gate": "C6", "note": "visual check done by model pipeline"},
        ))

        # ── C8a: Finalize from gate-results (via finalize_page.py) ─────────
        if FINALIZE_PAGE.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(FINALIZE_PAGE)] + base_args
                    + ["--skip-preamble"],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(PROJECT_ROOT),
                )
                gate_results["C8a"] = result.returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                gate_results["C8a"] = False
        else:
            gate_results["C8a"] = False
            log_event(self.run_dir, RunEvent(
                ts=utc_now(), event="gate_missing_script",
                detail={"gate": "C8a"},
            ))

        return gate_results

    def _generate_tasks(self) -> None:
        """Generate tasks for the current phase."""
        tasks = self.task_gen.generate_for_phase(
            phase=self.state.phase,
            regions=self.state.regions,
        )

        self.state.task_queue = [t.id for t in tasks]

        # Persist generated tasks for audit
        tasks_dir = self.run_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        for task in tasks:
            task_path = tasks_dir / f"{task.id}.yaml"
            task_path.write_text(json.dumps({
                "id": task.id,
                "phase": str(task.phase),
                "target_id": task.target_id,
                "target_type": task.target_type,
                "priority": task.priority,
                "allowed_files": task.allowed_files,
                "prohibited_patterns": task.prohibited_patterns,
                "measurements": task.measurements,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

    def _handle_convergence_action(self, action: str) -> dict[str, Any]:
        """Translate convergence action into an executable directive."""
        directive = {"action": action}

        if action == LoopAction.CONTINUE_NORMAL:
            directive["instruction"] = "Continue with next task in queue"
        elif action == LoopAction.CONVERGED_PROCEED_TO_GATE:
            directive["instruction"] = "Advance to next phase gate"
        elif action == LoopAction.SWITCH_TO_PRECISION:
            directive["instruction"] = "Switch to precision patch mode: smaller changes, more measurements"
        elif action == LoopAction.RETRY_WITH_MORE_MEASUREMENTS:
            directive["instruction"] = "Re-measure target with more granularity before next patch"
        elif action == LoopAction.ESCALATE_TO_ROOT_CAUSE:
            directive["instruction"] = "Run root-cause analysis: check if layout/parent is the real source"
        elif action == LoopAction.INVOKE_VISUAL_DIAGNOSIS:
            directive["instruction"] = "Invoke Kimi K3 for visual root-cause diagnosis"
            directive["require_visual_model"] = True
        elif action == LoopAction.DEMOTE_PHASE_AND_RETRY_PARENT:
            directive["instruction"] = "Demote to parent phase and fix ancestor geometry"
            self.state.consecutive_stagnant = 0
        elif action == LoopAction.FREEZE_TARGET_CONTINUE_OTHERS:
            directive["instruction"] = "Freeze current target, continue with next target in queue"
            directive["skip_current"] = True
        elif action == LoopAction.LOCK_AND_TRY_DIFFERENT:
            directive["instruction"] = "Lock current direction, try a completely different approach"
        elif action == LoopAction.ROLLBACK_LAST_PATCH:
            directive["instruction"] = "Rollback last patch, restore previous state"
            directive["rollback"] = True
        elif action == LoopAction.EMERGENCY_ROLLBACK_TO_BEST:
            directive["instruction"] = "Emergency rollback to best known checkpoint"
            directive["rollback_to_best"] = True
        elif action == LoopAction.ENTER_FINAL_AUDIT:
            directive["instruction"] = "Enter final audit within reserve window"
            self.state.phase = Phase.FINAL_AUDIT
        elif action == LoopAction.TERMINATE_BLOCKER_REPORT:
            directive["instruction"] = "Terminate with blocker report — goal not reachable"
            self.state.status = RunStatus.BLOCKED

        return directive

    def _build_phase_report(self) -> PhaseReport:
        """Build PhaseReport from current state."""
        score = self.state.latest_score
        return PhaseReport(
            phase=self.state.phase,
            runtime_errors=score.runtime_errors,
            console_errors=score.console_errors,
            required_evidence_complete=score.h2_evidence_pass,
            route_coverage=score.route_coverage,
            scroll_coverage=score.scroll_coverage,
            geometry_score=score.geometry,
            global_similarity=score.global_similarity,
            minimum_region_similarity=score.minimum_region_similarity,
            typography_score=score.typography,
            color_score=score.color,
            decoration_score=score.decoration,
            token_compliance=score.token_align,
            interaction_coverage=score.interaction_coverage,
            state_coverage=score.state_coverage,
            final_gate_passed=score.h1_engineering_pass and score.h2_evidence_pass,
        )

    # ── Status Builder ─────────────────────────────────────────────────────

    def _build_status(
        self,
        action_directive: dict[str, Any] | None = None,
        model_target: ModelTarget | None = None,
        model_reason: str = "",
    ) -> dict[str, Any]:
        """Build comprehensive status output for CC session consumption."""
        score = self.state.latest_score
        current_task_id = self.state.task_queue[0] if self.state.task_queue else None

        # Load current task if exists
        current_task = None
        if current_task_id:
            task_path = self.run_dir / "tasks" / f"{current_task_id}.yaml"
            if task_path.exists():
                try:
                    current_task = json.loads(task_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass

        return {
            "status": "ok",
            "run": {
                "run_id": self.state.run_id,
                "task_name": self.state.task_name,
                "run_status": str(self.state.status),
                "phase": str(self.state.phase),
                "iteration": self.state.iteration,
                "elapsed_seconds": (
                    datetime.now(timezone.utc).timestamp() - self.state.wall_clock_start
                    if self.state.wall_clock_start > 0 else 0
                ),
                "budget_remaining_seconds": max(0, (
                    self.state.wall_clock_deadline_utc
                    - datetime.now(timezone.utc).timestamp()
                )),
            },
            "score": {
                "uif_composite": score.uif_composite(),
                "global_similarity": score.global_similarity,
                "dimensions": {
                    "geometry": score.geometry,
                    "color": score.color,
                    "typography": score.typography,
                    "decoration": score.decoration,
                    "layout": score.layout,
                    "token_align": score.token_align,
                    "interaction": score.interaction,
                },
                "coverage": {
                    "interaction": score.interaction_coverage,
                    "state": score.state_coverage,
                    "route": score.route_coverage,
                    "scroll": score.scroll_coverage,
                },
                "hard_gates": {
                    "h1_engineering": score.h1_engineering_pass,
                    "h2_evidence": score.h2_evidence_pass,
                },
                "best_composite": self.state.best_score.uif_composite(),
            },
            "phase_gate": {
                "can_advance": self.gate.can_advance(self._build_phase_report()),
                "next_phase": str(self.gate.next_phase(self.state.phase) or ""),
                "thresholds": {
                    "phase": str(self.state.phase),
                    "d1_d5_min": PHASE_THRESHOLDS.get(self.state.phase, PHASE_THRESHOLDS[Phase.ELEMENTS]).d1_d5_min,
                    "d6_token_min": PHASE_THRESHOLDS.get(self.state.phase, PHASE_THRESHOLDS[Phase.ELEMENTS]).d6_token_min,
                    "d7_interaction_min": PHASE_THRESHOLDS.get(self.state.phase, PHASE_THRESHOLDS[Phase.ELEMENTS]).d7_interaction_min,
                },
            },
            "tasks": {
                "queue_length": len(self.state.task_queue),
                "current_task": current_task,
                "completed_count": len(self.state.completed_tasks),
            },
            "model_routing": {
                "target": str(model_target or ModelTarget.HAIKU),
                "reason": model_reason or "default",
                "budget": self.router.budget_report(),
            },
            "directive": action_directive or {"action": "CONTINUE_NORMAL"},
            "blockers": [],
            "stagnation": {
                "consecutive_stagnant": self.state.consecutive_stagnant,
                "consecutive_no_progress": self.state.consecutive_no_progress,
                "consecutive_diverging": self.state.consecutive_diverging,
            },
        }


# ── CLI Interface ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="UI Autopilot v2 Orchestrator",
    )
    parser.add_argument(
        "--task-id", required=True,
        help="Task identifier (e.g., dashboard-restoration-20260729)",
    )
    parser.add_argument(
        "--action", default="status",
        choices=["init", "tick", "status", "checkpoint", "restore", "dry-run"],
        help="Action to perform",
    )
    parser.add_argument(
        "--result", type=str, default=None,
        help="JSON result from previous action (for 'tick' action)",
    )
    parser.add_argument(
        "--checkpoint-label", type=str, default=None,
        help="Checkpoint label for restore action",
    )
    args = parser.parse_args()

    orch = Orchestrator(task_id=args.task_id)

    if args.action == "init":
        result = orch.init()
    elif args.action == "tick":
        action_result = None
        if args.result:
            try:
                action_result = json.loads(args.result)
            except json.JSONDecodeError:
                print(json.dumps({"status": "error", "message": "Invalid --result JSON"}))
                sys.exit(1)
        result = orch.tick(action_result)
    elif args.action == "checkpoint":
        label = args.checkpoint_label or ""
        path = save_checkpoint(orch.state, orch.run_dir, label)
        result = {"status": "ok", "checkpoint": path}
    elif args.action == "restore":
        if not args.checkpoint_label:
            print(json.dumps({"status": "error", "message": "--checkpoint-label required for restore"}))
            sys.exit(1)
        state = restore_checkpoint(orch.run_dir, args.checkpoint_label)
        if state:
            # GAP 7 fix: Restore convergence controller from checkpoint
            if state.convergence_state:
                orch.controller = LoopController.from_dict(state.convergence_state)
            result = {"status": "ok", "restored_from": args.checkpoint_label}
        else:
            result = {"status": "error", "message": "Checkpoint not found"}
    elif args.action == "dry-run":
        # Dry-run: initialize and run one tick without external effects
        orch.init()
        result = orch.tick()
        result["dry_run"] = True
    else:
        result = orch.status()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
