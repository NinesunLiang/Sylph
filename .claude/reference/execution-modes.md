# Execution Modes — Race & Stepwise

> **Purpose**: Define the two fundamental execution modes of the OMA system — Race (loose concurrent) and Stepwise (rigorous sequential)
> **Version**: v1.0.0
> **Status**: Draft
> **Last Updated**: 2026-05-09

---

## Design Philosophy

The OMA system recognizes two and only two fundamental execution modes. Every skill, workflow, and task in the system is a variant of one of these modes. By making the modes explicit, we gain:
- **Mode selection** as a conscious architectural decision (not accidental)
- **Standardized gates** per mode (no reinvention per skill)
- **Predictable failure handling** (declared upfront, not discovered mid-execution)

---

## Mode Selection

### Decision Matrix

Before any execution starts, evaluate the task against this matrix:

| Criterion | Race Mode | Stepwise Mode |
|-----------|-----------|---------------|
| Task count | ≥3 independent sub-tasks | Single / tightly coupled |
| Sub-task dependency | MECE (no ordering) | Sequential (each step depends on previous) |
| Complexity per unit | Low–Medium (can be isolated) | Medium–High (requires full context) |
| Failure blast radius | Isolated (one sub-task fails, others continue) | Cascading (failure at step N invalidates N+1) |
| Gate requirement | Lightweight (per-subtask completion) | Heavy (per-stage entry/exit criteria) |
| Recovery strategy | Skip failed sub-task, continue | Rollback or re-plan from failure point |
| Human oversight needed | Aggregate report review | Per-stage gate approval |

### Mode Selection Flow

```
Input task
  → Can task be MECE-decomposed into ≥3 independent sub-tasks?
    → Yes: Can each sub-task complete without results from others?
      → Yes: [Race Mode]
      → No: [Stepwise Mode]
    → No: Is the task complex enough to need staged gates?
      → Yes: [Stepwise Mode]
      → No: Direct execution (no formal mode needed)
```

### Existing Skill Mapping

| Skill | Mode | Rationale |
|-------|------|-----------|
| lx-race | **Race** | Explicit swarm coordination |
| lx-oma-split | **Race** | MECE decomposition → parallel RPE |
| lx-rpe | **Stepwise** | 9-step closed loop with gates |
| lx-root-cause-analysis | **Stepwise** | 5-phase depth-first reasoning |
| lx-todo | **Stepwise** | 5-step linear workflow |
| lx-task-spec | **Stepwise** | Task spec → plan → execute cycle |
| lx-code-review | **Stepwise** | Scan → fix → verify → report |
| lx-oma-hier | **Stepwise** | Read → analyze → generate → verify |
| lx-oma-gov | **Stepwise** | Reconcile → verify → propagate cycle |
| lx-oma-orch | **Race/Stepwise hybrid** | Status (read-only) + Advance (stepwise) + Run (race dispatch) |
| lx-status | **Race** | Aggregation of independent data sources |

---

## Race Mode — 松散并发模式

### Character

"Fan-out, execute independently, fan-in." Race mode is for workloads where sub-tasks are genuinely independent and the bottleneck is throughput, not sequential correctness.

### State Machine

```
idle
  → [evaluate] → evaluated
      → [reject: not MECE] → failed
      → [accept] → ready
  → [dispatch] → running (K concurrent workers)
      → on each completion → one_done
          → all dispatched → awaiting_collection
              → [all done] → collecting
              → [partial: some failed] → collecting (with failures)
          → [abort signal] → aborting → failed
  → [collect] → aggregating
      → [report generated] → done
```

### Entry Gate (评估 → 就绪)

```
[ ] Sub-tasks confirmed MECE — verify no shared state or ordering dependency
[ ] Each sub-task has a completion criterion (single sentence or AC-XXX)
[ ] Each sub-task has an evidence requirement (what constitutes "done")
[ ] Max concurrency K defined (default: min(count, 3))
[ ] Conflict strategy chosen:
    ├─ OMA Lock (shared mutable state)
    └─ No lock (read-only or partitioned state)
[ ] Aggregate report template defined
```

### Dispatch Protocol

| Concern | Rule |
|---------|------|
| Worker creation | Platform-native (Task() API / Claude Code team / sub-agent) |
| Context isolation | Each worker receives sub-task spec only (no full parent context) |
| Write conflict | OMA Lock for shared files; partitioned paths for independent state |
| Worker lifecycle | Timeout = 2× estimated max sub-task duration |
| Progress tracking | `race_manager.sh` register → status → report |

### Collect Protocol

```
1. Await all workers (success or failure)
2. For each completed sub-task:
   a. Read evidence file
   b. Verify against entry-gate completion criterion
   c. Classify: ✅ pass / ❌ fail / ⚠️ partial
3. For each failed sub-task:
   a. Classify: retriable / permanent
   b. Skipped: document reason in aggregate report
4. Generate aggregate report
```

### Exit Gate (汇总 → 完成)

```
[ ] All sub-tasks accounted for (no orphan workers)
[ ] Aggregate report written (path: .omc/race/{id}/report.json)
[ ] Pass rate documented: N/M completed
[ ] For each failure: reason documented
[ ] Lessons learned: was race mode appropriate? record for next evaluation
```

### Failure Handling

| Failure Type | Action | Escalation |
|-------------|--------|------------|
| Individual sub-task fails | Isolate, continue other sub-tasks | Max 2 retries per sub-task |
| OMA Lock conflict | Backoff and retry (exponential: 1s, 2s, 4s) | 3 conflicts → skip sub-task |
| Worker timeout | Kill worker, mark sub-task as failed | Document in report |
| Mass failure (>50% sub-tasks fail) | Continue but flag in report | Advisory (not abort) |
| Race mode mis-selection (sub-tasks not actually independent) | **Abort race mode**, fall back to stepwise | **Must** note in lessons |

---

## Stepwise Mode — 严谨逐级模式

### Character

"Stage gate, prove, advance." Stepwise mode is for problems where each step builds on the previous, and correctness at each stage is a precondition for the next. This is the default mode for complex single-threaded work.

### State Machine

```
idle
  → [plan stages] → planned
      → [entry gate failed] → failed
      → [entry gate passed] → stage_1_ready
  → [execute stage N] → stage_N_active
      → [stage gate: fail] → retry_stage_N (max 2)
          → [retry fail] → choose:
              ├─ rollback → rollback_N
              │   → [rolled back] → re_plan
              └─ re_plan_N → re_planning
                  → [re-planned] → stage_N_active (new plan)
      → [stage gate: pass] → stage_N_complete
          → [more stages] → stage_N+1_ready
          → [all complete] → final_gate
              → [passed] → done
              → [failed] → re_plan
  → [abort] → aborting → failed
```

### Stage Definition

Each stage in a stepwise execution must be declared in advance (not ad-hoc):

```yaml
stage:
  id: "S-N"
  name: "Stage Name"
  entry_criteria:
    - "Previous stage exit gate passed"
    - "Input artifacts available: [list files/info needed]"
  execution_plan: "What this stage does"
  exit_criteria:
    - "Criterion 1 (verifiable: file:line or command output)"
    - "Criterion 2"
  evidence_requirements:
    - "Evidence file path or command to run"
  rollback:
    action: "git checkout / file restore / config revert"
    scope: "Files modified in this stage only"
  max_retries: 2
```

### Stage Gate (每阶段准入/准出)

**Entry Gate (per stage)** — must pass before executing:

```
[ ] Previous stage exit gate confirmed (or "first stage" if S-1)
[ ] Input artifacts verified (files exist, data is fresh)
[ ] Rollback plan for this stage confirmed
[ ] Max retries for this stage: 2
[ ] No unresolved blockers from previous stage
```

**Exit Gate (per stage)** — must pass before advancing:

```
[ ] All exit criteria met (each verifiable with file:line or command)
[ ] Evidence for each criterion written to executor.md or evidence file
[ ] Rollback plan for this stage NOT executed (but defined)
[ ] Any tech-debt discovered logged (not fixed — scope freeze)
[ ] Cross-stage consistency checked (this stage's output doesn't contradict S-1's assumptions)
```

### Final Gate (整体完成)

```
[ ] All stages completed and exit-gate verified
[ ] Evidence consolidated (single summary or per-stage references)
[ ] Rollback plan for entire execution documented
[ ] Lessons learned recorded
[ ] Mode selection validated: stepwise was appropriate choice?
```

### Failure Handling

| Failure Type | Action | Escalation |
|-------------|--------|------------|
| Stage exit gate fails (1st time) | Fix within stage, retry | — |
| Stage exit gate fails (2nd time) | **Stop.** Two choices: rollback or re-plan | Escalate to user |
| Rollback chosen | Execute rollback action → re-verify S-1 exit gate → re-plan remaining stages | User confirms rollback result |
| Re-plan chosen | Document why original plan wrong → new plan for remaining stages → user approves | User approves new plan |
| Cross-stage inconsistency found | Flag as Blocker. Compare S-N output vs S-(N-1) assumptions | User decides: fix inconsistency or update assumptions |
| Total failure budget exceeded (3 escalations) | Abort entire execution. Document lessons. | User must restart with new approach |

### Failure Budget

Each stepwise execution has a total failure budget of **3 escalations**:
- Each stage-gate retry escalation counts: 1
- Each rollback counts: 2
- Each re-plan counts: 1
- Budget exceeded → abort execution entirely

### Context Guard Integration

Stepwise executions are long-running. Integrate with context-guard:

| Context Level | Action |
|---------------|--------|
| <50% | Normal execution |
| 50-79% | Emit handoff warning (stderr advisory) |
| 80%+ | Context-guard blocks Edit/Write (hard stop). Must execute recovery: write snapshot, summarize current stage, prepare handoff for next session |
| Pre-emptive | At each stage exit gate, if context >60%, proactively compact |

---

## Mode Interaction

### Race → Stepwise Cascade

A Race execution may contain Stepwise sub-tasks (each sub-task is itself a stepwise process):

```
[Race: Master Task]
  ├── [Stepwise: Sub-task A] → gates A1 → A2 → A3
  ├── [Stepwise: Sub-task B] → gates B1 → B2
  └── [Race collect] → aggregate report
```

In this case, each sub-task's stepwise failure is isolated within that sub-task (per Race failure rules).

### Stepwise → Race Expansion

A Stepwise stage may expand into a Race for its sub-operations:

```
[Stepwise: Stage 3 — Implement Features]
  ├── [Race: Fan-out feature implementation]
  │   ├── feat-A (independent worker)
  │   ├── feat-B (independent worker)
  │   └── feat-C (independent worker)
  └── [Stage gate: all features implemented]
```

This is valid as long as the Race executes within the Stage boundary and the Stage gate verifies the aggregated result.

---

## When NOT to Use Either Mode

Some tasks don't need a formal mode:

| Task Type | Recommended Action |
|-----------|-------------------|
| Single file edit | Direct execution + evidence gate |
| Simple bug fix (1-2 files) | Direct execution + evidence gate |
| Read-only investigation | No formal mode needed |
| One-command operation | No formal mode needed |

The formality of mode selection is proportional to task complexity. When in doubt, ask: "Is this task complex enough that an incorrect approach would waste significant time?" If no → skip mode, just execute.

---

## Mapping to Existing System

### Harness integration points

| Gate | Race | Stepwise |
|------|------|----------|
| `completion-gate` | Per sub-task evidence | Per stage evidence |
| `context-guard` | N/A (short-lived workers) | Integrated (per-stage check) |
| `pretool-write-lock` | OMA Lock for shared files | Standard write lock |
| `plan-gate` | Entry gate: MECE check | Entry gate: stage definition |
| `current-scope` | Per sub-task scope check | Standard scope check |

### Skill integration

Every skill now declares its mode in its SKILL.md frontmatter (as of v6.1.9):

```yaml
execution_mode: race | stepwise  # standard field (frontmatter is source of truth)
role: "..."                       # one-line identity description
```

The orchestrator (`lx-oma-orch`) reads `execution_mode` from frontmatter to apply mode-appropriate gates and failure handling without hardcoding per skill. See `nodes/mode_selector.md` for the callable mode selection node.

For a complete mapping, see the mode_selector node's skill table, which aggregates all skills by mode.
