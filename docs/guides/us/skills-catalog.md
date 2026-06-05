# Skills Catalog

> Source-extracted from `.claude/skills/`. 26 `lx-` skills organized by functional domain.

## Quick Reference

| Category | Count | Purpose |
|----------|-------|---------|
| [Execution Modes](#execution-modes) | 2 | Autonomous unattended execution |
| [OMA Pipeline](#oma-pipeline) | 5 | PRD → decomposition → orchestration → governance |
| [Quality Gates](#quality-gates) | 2 | Pre-commit / pre-push checks |
| [Governance](#governance) | 4 | Oracle review / validate-skill / purify / skillify |
| [Task Management](#task-management) | 5 | todo → task-spec → RPE → stepwise → sync |
| [Code Review & Testing](#code-review--testing) | 3 | Code review / test-gen / root-cause |
| [Infrastructure](#infrastructure) | 5 | Status / dogfood / varlock / race / learner / update |

---

## Execution Modes

Autonomous execution with downgraded safety nets — no pausing to ask.

| Skill | Summary | Triggers |
|-------|---------|----------|
| `/lx-ghost` | Direction-driven incremental exploration. Give a direction, AI explores step by step | `ghost mode` |
| `/lx-goal` | Goal-driven autonomous execution. Give a goal, AI executes to completion with report | `goal mode`, `unattended` |

**How to choose**:
- Vague direction, needs iterative exploration → `/lx-ghost`
- Clear goal, know what result you want → `/lx-goal`

---

## OMA Pipeline

One-Man Army development pipeline — from PRD to feature.

| Skill | Summary |
|-------|---------|
| `/lx-oma-hier` | Decompose large PRDs into MECE Sub-PRDs by functional domain |
| `/lx-oma-split` | Split Sub-PRDs into orthogonal feature branches |
| `/lx-oma-orch` | Pipeline orchestrator — status, stage advancement, Oracle gates, parallel management |
| `/lx-oma-gov` | Incremental PRD sync, conflict arbitration, drift detection |
| `/lx-rpe` | Full RPE-driven feature dev: TDD → review → security → acceptance |

**Typical flow**: `hier` (decompose large PRD) → `split` (into features) → `orch` (orchestrate execution) → `gov` (govern changes). RPE handles individual feature execution.

---

## Quality Gates

Automated checks before commit and push.

| Skill | Summary |
|-------|---------|
| `/lx-pre-commit` | Project type detection → build → test → code review |
| `/lx-pre-push` | Commit message validation → test coverage → security scan → verdict |

Operation layer executed by `.claude/scripts/`, AI handles result interpretation and routing.

---

## Governance

| Skill | Summary |
|-------|---------|
| `/lx-oracle` | Oracle independent review agent — code review, plan audit, mechanism validation |
| `/lx-oracle-v2` | (Deprecated) Use `/lx-oracle` instead |
| `/lx-validate-skill` | Validate new skills against atomization architecture rules (11 checks) |
| `/lx-purify` | Dual-judge review pipeline: Oracle (static) → Meta-Oracle (runtime) |
| `/lx-skillify` | Convert successful approaches into reusable skills |

---

## Task Management

| Skill | Complexity | Use Case |
|-------|------------|----------|
| `/lx-todo` | L1 | Lightweight 5-step loop: capture → triage → fix → verify → close (≤3 files) |
| `/lx-task-spec` | L2 | Medium complexity. 3 guided questions → AC-driven → clarify → plan → execute → verify |
| `/lx-stepwise` | L3 | High-difficulty serial debugging: unknown root cause, cross-module, complex state machines |
| `/lx-race` | L3 | Swarm coordination: register subtasks → dispatch → collect → report |
| `/lx-sync` | L2 | Drift detection and synchronization between source mirrors |

**How to choose**:
- Fix a typo / single-line bug → `/lx-todo`
- Needs precise AC but not a full PRD → `/lx-task-spec`
- Hard debugging / cross-module issue → `/lx-stepwise`
- Multiple parallel subtasks → `/lx-race`
- Check config drift → `/lx-sync`

---

## Code Review & Testing

| Skill | Target | Rules |
|-------|--------|-------|
| `/lx-code-review` | General code | 8 categories, 39 rules (error handling, concurrency, interfaces, performance, observability) |
| `/lx-test-gen` | Language-agnostic test generator | Auto-detects language (Go/TS/Python), routes to patterns |
| `/lx-root-cause-analysis` | Bug analysis | 5-Why root cause tracing, evidence chains, confidence scoring, immunity defense |

---

## Infrastructure

| Skill | Summary |
|-------|---------|
| `/lx-status` | Health panel v3.0: Token savings, task pass rate, blocked errors, knowledge points + audit summary |
| `/lx-dogfood` | Systematic exploratory QA testing — find AI behavior issues before they reach production |
| `/lx-learner` | Knowledge distillation — extract reusable patterns from completed tasks |
| `/lx-varlock` | Privacy sanitization proxy — passwords, API keys, tokens never leak into AI context |
| `/update-carror-os` | Update CarrorOS itself to the latest version |

---

## Skill Relationship Graph

```
Task complexity increasing →
  /lx-todo (L1, lightweight)
    → /lx-task-spec (L2, medium)
      → /lx-stepwise (L3, serial deep-dive)
      → /lx-rpe (L3, full feature)

OMA pipeline flow →
  /lx-oma-hier (decompose large PRD)
    → /lx-oma-split (split into features)
      → /lx-oma-orch (orchestrate execution)
        → /lx-oma-gov (govern changes)

Gate chain →
  /lx-pre-commit (pre-commit)
    → /lx-pre-push (pre-push)

Quality quartet →
  /lx-oracle (independent review)
    → /lx-purify (dual-judge pipeline)
      → /lx-skillify (extract to skill)

Autonomous execution →
  /lx-ghost (direction-driven exploration)
  /lx-goal (goal-driven execution)
```

---

## Non-lx Skills (OMC Infrastructure)

These are managed via the `omc-reference` skill and belong to the OMC infrastructure layer:

`autopilot` `ultrawork` `ralph` `team` `ccg` `ralplan` `deep-interview` `ai-slop-cleaner` `omc-setup` `omc-doctor` `omc-plan` etc.

Full list at `/omc-reference`.
