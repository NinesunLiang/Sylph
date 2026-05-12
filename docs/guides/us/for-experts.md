# For Experts

> **You are not here for guardrails. You are here for force multipliers.**

## What Changes

The **Enhanced Edition** unlocks the full Carror OS -- active workflows, multi-agent blind review, DLP transparent proxy, and RPE development pipeline.

Install it:

```bash
curl -fsSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s -- enhanced
```

## What You Get (Beyond Base)

### Active Workflow Skills

| Skill | What It Does |
| :---- | :----------- |
| `/lx-rpe` | Research -> Plan -> Execute pipeline with 50% context handoff and A/B blind review. |
| `/lx-task-spec` | Medium-complexity tasks driven by precise acceptance criteria (no PRD needed). |
| `/lx-todo` | Lightweight 5-step bug fix loop for small tasks (3 files or fewer). |
| `/lx-prd` | Automated product requirements document generation. |
| `/lx-tdd-spec` | TDD test scenario generation from behavior matrices. |
| `/lx-browser-verify` | Playwright E2E visual acceptance testing. |
| `/lx-root-cause-analysis` | 5-Why root cause tracing for deep debugging. |
| `/lx-debug-spec` | Concurrency debugging for deep-water issues. |
| `/lx-golang-test` | Go-specific test framework. |
| `/lx-frontend-test` | Frontend test framework. |
| `/lx-varlock` | DLP transparent proxy -- the AI works with masked credentials; the local vault substitutes them at execution time. |
| `/lx-status` | Health dashboard with token savings, self-heal rate, and execution profile. |

### RPE Workflow

The primary expert workflow is **Research -> Plan -> Execute**:

1. **Research**: Investigate the problem space, document constraints, read affected code.
2. **Plan**: Design architecture, define interfaces, set acceptance criteria.
3. **Execute**: Implement with evidence gating at every step. Automatic context handoff at 50%.

### Advanced Workflows

- **Race** (`/lx-race`): Parallel candidate generation with judge-based selection.
- **OMA** (`/lx-oma`): Optimized multi-agent concurrent development with lock management.

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
