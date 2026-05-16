# Carror OS: Three-Stage Product Structure & Editions

> **The Three-Stage Rocket**
> **Not feature gating — progressive cognitive release.**

---

## 1. The Philosophy

In previous iterations, we found that pushing all 24 AI development pipelines (Skills) to a new user at once creates **cognitive overload**. They don't know where to start. They're afraid of typing the wrong command.

A real operating system never forces users to learn complex syscalls on first boot. It manages memory and processes quietly in the background.

Carror OS proposes **"Guard First, Arm Later"** — progressive delivery across three layers:

- **Level 1 — Harness Only**: The lowest-level **Kernel firewall**. No application Skills, only physical interceptors. It only steps in when you're about to make a fatal mistake.
- **Level 2 — Base Edition**: The **silent guardian**. Adds 10 code review and security gate Skills on top of the kernel. No new commands to learn — just let AI run `pre-commit` as usual.
- **Level 3 — Enhanced Edition**: The **Userland arsenal**. All 24 pipeline Skills — tools you need to actively learn and command for "one-person army" automation.

---

## 2. What's Included

### Level 1 — Harness Only

- **Contents**: 32 Hook scripts (30 registered in settings.json, 2 standalone tools)
- **Design**: Zero cognitive load. No active workflows. The AI simply wears a safety straitjacket.

| Capability | Includes | Description |
|:-----------|:---------|:------------|
| **Defense Layer (Hooks)** | `privacy-gate`, `context-guard`, `permission-gate` etc. — 32 Hooks | Intercepts privacy leaks, dangerous commands, 80% context memory fuse, records error DNA |

### Level 2 — Base Edition (Default)

- **Contents**: All Level 1 defenses + 10 automated gate Skills
- **Design**: Silent quality control. Passive trigger, fully automated.

| Capability | Includes | Description |
|:-----------|:---------|:------------|
| **Commit Gates (Skills)** | `lx-pre-commit`, `lx-pre-push` | User says "run pre-commit" — gates handle the rest |
| **Deep Analysis (Skills)** | `lx-oma`, `lx-perf-analysis`, `lx-race` | Concurrent lock management, performance analysis, race detection — silent background operation |

### Level 3 — Enhanced Edition

- **Contents**: All Level 2 capabilities + 14 active workflow Skills
- **Design**: High learning cost, high return. Active scheduling, requires command authority.

| Capability | Additional Skills | Description |
|:-----------|:-----------------|:------------|
| **Large Feature Pipeline** | `lx-rpe` | Research → Plan → Execute with 50% sweet-spot handoff and A→B→A adversarial verification |
| **Medium/Small Task Driver** | `lx-task-spec`, `lx-todo` | AC-driven medium tasks and ≤3 file quick bug fix loops |

---

## 3. Who Is It For?

**Harness Only:**
- Minimalists who just want a physical lock on AI and zero configuration

**Base:**
- Developers new to AI-assisted coding who don't want to change existing habits
- Anyone needing a "code-aware AI" that catches issues before commit

**Enhanced:**
- Tech leads, architects, senior full-stack engineers
- Those tackling complex refactoring requiring strict engineering discipline
- One-person-army hackers needing multi-step debugging, real-time token monitoring, and self-healing rate tracking

---

## 4. How to Switch

Carror OS is decoupled by design. Switch between tiers anytime — Hooks never drop, zero data loss:

```bash
# Minimal: defense only
bash install.sh harness

# Default: commit gates and reviews
bash install.sh base

# Full power: workflow pipelines
bash install.sh enhanced
```
