# Skills Catalog

> Source-extracted from `.claude/skills/`. 25 `lx-` skills organized by functional domain.

## Quick Reference

| Category | Count | Purpose |
|----------|-------|---------|
| [Execution Modes](#execution-modes) | 2 | Autonomous unattended execution |
| [OMA Pipeline](#oma-pipeline) | 4 | PRD → decomposition → orchestration → governance |
| [Quality Gates](#quality-gates) | 2 | Pre-commit / pre-push checks |
| [Task Management](#task-management) | 4 | todo → task-spec → RPE → PRD |
| [Code Review](#code-review) | 4 | Go / React / Security / Performance |
| [Testing](#testing) | 6 | Test generation / TDD / debugging / visual |
| [Infrastructure](#infrastructure) | 3 | Status panel / privacy proxy / swarm |

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

**Typical flow**: `hier` (decompose large PRD) → `split` (into features) → `orch` (orchestrate execution) → `gov` (govern changes).

---

## Quality Gates

Automated checks before commit and push.

| Skill | Summary |
|-------|---------|
| `/lx-pre-commit` | Project type detection → build → test → code review |
| `/lx-pre-push` | Commit message validation → test coverage → security scan → verdict |

Operation layer executed by `.claude/scripts/`, AI handles result interpretation and routing.

---

## Task Management

Graded task system from lightweight bug fixes to full PRD-driven development.

| Skill | Complexity | Use Case |
|-------|------------|----------|
| `/lx-todo` | L1 | Lightweight 5-step loop: capture → triage → fix → verify → close (≤3 files) |
| `/lx-task-spec` | L2 | Medium complexity. 3 guided questions → AC-driven → clarify → plan → execute → verify |
| `/lx-rpe` | L3 | Full RPE-driven feature dev: TDD → review → security → acceptance |
| `/lx-prd` | L3 | ~~PRD production pipeline~~ Replaced by `/lx-oma-split` |

**How to choose**:
- Fix a typo / single-line bug → `/lx-todo`
- Needs precise AC but not a full PRD → `/lx-task-spec`
- New feature / architectural change → `/lx-rpe`
- Needs PRD (replaced by `/lx-oma-split`) → `/lx-oma-split`

---

## Code Review

| Skill | Target | Rules |
|-------|--------|-------|
| `/lx-code-review` | General code | 8 categories, 39 rules (error handling, concurrency, interfaces, performance, observability) |
| `/lx-react-review` | React/Next.js/Vue/Svelte | Render perf, Hooks, component design, state management, TS quality |
| `/lx-security-review` | General code + deps | Vulnerability scan → auto-fix → re-scan → commit verdict |
| `/lx-web-perf` | Frontend projects | 6 categories, 24 rules (Bundle, Web Vitals, Next.js, rendering, network, assets) |

---

## Testing

| Skill | Summary |
|-------|---------|
| `/lx-test-gen` | Language-agnostic test generator. Auto-detects language (Go/TS/Python), routes to patterns |
| `/lx-tdd-spec` | Generate testable specs from behavior matrix + GWT acceptance criteria |
| `/lx-golang-test` | Pattern-routed test generation: table-driven, mocks, HTTP handlers, benchmarks, fuzz, race (methodology-agnostic, Go implementation) |
| `/lx-browser-verify` | Playwright visual acceptance. 5 categories, 24 items (multi-resolution, visual regression, interactive flows, cross-browser) |
| `/lx-debug-spec` | Root cause investigation → hypothesis verification → fix → regression |
| `/lx-root-cause-analysis` | 5-Why root cause tracing, evidence chains, confidence scoring, immunity defense |

---

## Infrastructure

| Skill | Summary |
|-------|---------|
| `/lx-status` | Health panel v3.0: Token savings, task pass rate, blocked errors, knowledge points + audit summary |
| `/lx-varlock` | Privacy sanitization proxy — passwords, API keys, tokens never leak into AI context |
| `/lx-race` | Swarm coordination layer: register subtasks → dispatch → collect → report |
| `/lx-validate-skill` | Validate new skills against atomization architecture rules (11 checks) |

---

## Skill Relationship Graph

```
Task complexity increasing →
  /lx-todo (L1, lightweight)
    → /lx-task-spec (L2, medium)
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
  /lx-code-review + /lx-react-review (code review)
  /lx-security-review (security)
  /lx-web-perf (performance)
  /lx-test-gen + /lx-golang-test (testing)

Autonomous execution →
  /lx-ghost (direction-driven exploration)
  /lx-goal (goal-driven execution)
```

---

## Non-lx Skills (OMC Infrastructure)

These are managed via the `omc-reference` skill and belong to the OMC infrastructure layer:

`autopilot` `ultrawork` `ralph` `team` `ccg` `ralplan` `deep-interview` `ai-slop-cleaner` `omc-setup` `omc-doctor` `omc-plan` etc.

Full list at `/omc-reference`.
