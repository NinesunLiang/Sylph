# For Experts

> **You are not here for guardrails. You are here for force multipliers.**

## What Changes

The **Enhanced Edition** unlocks the full Carror OS -- active workflows, multi-agent blind review, DLP transparent proxy, and RPE development pipeline.

Install it:

```bash
curl -fsSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s -- enhanced
```

## What You Get (Beyond Base)

### Execution Modes

| Skill | What It Does |
| :---- | :----------- |
| `/lx-ghost` | Direction-driven autonomous exploration — give a direction, AI iterates incrementally with downgraded safety nets. |
| `/lx-goal` | Goal-driven autonomous execution — give a goal, AI executes to completion and reports. |

### Task Management (Increasing Complexity)

| Skill | Level | What It Does |
| :---- | :---: | :----------- |
| `/lx-todo` | L1 | Lightweight 5-step loop: capture → triage → fix → verify → close (≤3 files). |
| `/lx-task-spec` | L2 | 3 guided questions → AC-driven, medium complexity, no full PRD needed. |
| `/lx-rpe` | L3 | Research → Plan → Execute pipeline with 50% context handoff and A/B blind review. |

### OMA One-Man Army Pipeline

| Skill | What It Does |
| :---- | :----------- |
| `/lx-oma-hier` | Decompose large PRDs into MECE Sub-PRDs by functional domain. |
| `/lx-oma-split` | Split Sub-PRDs into orthogonal feature branches. |
| `/lx-oma-orch` | Pipeline orchestrator: status, stage advancement, Oracle gates, parallel management. |
| `/lx-oma-gov` | PRD governance: incremental sync, conflict arbitration, drift detection. |

### Quality Gates

| Skill | What It Does |
| :---- | :----------- |
| `/lx-pre-commit` | Pre-commit: project type detection → build → test → code review. |
| `/lx-pre-push` | Pre-push: commit message validation → test coverage → security scan → verdict. |

### Code Quality

| Skill | Target | Rules |
| :---- | :----- | :---- |
| `/lx-code-review` | General code | 8 categories, 39 rules (error handling, concurrency, interfaces, performance, observability). |

### Testing & Debugging

| Skill | What It Does |
| :---- | :----------- |
| `/lx-test-gen` | Language-agnostic test generation (Go/TS/Python auto-detection). |
| `/lx-root-cause-analysis` | 5-Why root cause tracing + evidence chains + confidence scoring. |

### Infrastructure

| Skill | What It Does |
| :---- | :----------- |
| `/lx-status` | Health panel v3.0: Token savings, task pass rate, blocked errors, knowledge points. |
| `/lx-varlock` | DLP transparent proxy — sensitive credentials never leak into AI context. |
| `/lx-race` | Swarm coordination: register subtasks → dispatch → collect → report. |

> Full catalog (with triggers, selection guides, relationship graph) at [Skills Catalog](skills-catalog.md).

### RPE Workflow

The primary expert workflow is **Research → Plan → Execute**:

1. **Research**: Investigate the problem space, document constraints, read affected code.
2. **Plan**: Design architecture, define interfaces, set acceptance criteria.
3. **Execute**: Implement with evidence gating at every step. Automatic context handoff at 50%.

## When to Upgrade

Upgrade from Base to Enhanced when you:

- Are taking on a complex refactoring that spans multiple modules.
- Need multi-agent blind review to catch your own blind spots.
- Want structured RPE discipline for large feature development.
- Need to manage concurrent AI agents working on different parts of a codebase.

The upgrade is safe and in-place. Your existing configuration and memories are preserved:

```bash
bash install.sh enhanced
```

Downgrade is also safe:

```bash
bash install.sh base
```

## Next Steps

| Goal | Path |
| :--- | :--- |
| RPE deep dive | [Workflow Concepts](../concepts/workflow.md) |
| Full feature reference | [Features](../governance/features.md) |
| Upgrade instructions | [Editions](../governance/editions.md) |
