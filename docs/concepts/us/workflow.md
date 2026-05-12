# Workflow (工作流体系)

> **From ad-hoc prompts to disciplined engineering processes.**

---

## Three-Layer Architecture

Carror OS is structured as a three-stage rocket. Each layer adds capability without removing anything from the layer below.

### Layer 1: Harness Only (Kernel)

The base layer. 32 physical hook scripts (30 registered in settings.json, 2 standalone tools) that intercept AI actions at the filesystem level. No user-facing commands, no active workflows -- just silent protection.

- Gate interception (completion, permission, privacy, context)
- Error DNA recording
- Session lifecycle management

### Layer 2: Base Edition (Guard)

Layer 1 + 10 automated Skill gates. 7 run during commit workflows:

| Skill | Purpose |
| :---- | :------ |
| `lx-pre-commit` | Quality gate: type check, incremental build, test, code review |
| `lx-pre-push` | Security gate: commit format + compliance checks |
| `lx-code-review` | Language-agnostic code review with auto-fix |
| `lx-react-review` | React/TypeScript-specific review |
| `lx-security-review` | Vulnerability and hardcoded secret scanning |
| `lx-style-guide` | CSS/Tailwind style compliance |
| `lx-web-perf` | Web performance audit (bundles, vitals, rendering) |

In Base Edition, these run automatically when you trigger `pre-commit`. You do not need to learn individual commands.

### Layer 3: Enhanced Edition (Userland)

Layer 2 + 14 active workflow Skills. These require learning but deliver industrial-grade AI-assisted development.

---

## RPE Development Mode

**Research -> Plan -> Execute** is the primary workflow for complex feature development. It is the structured alternative to vibe coding.

### Phase 1: Research

Investigate the problem space. Read existing code, identify affected modules, document constraints. Output: research document.

### Phase 2: Plan

Design the solution architecture. Define interfaces, data flow, and acceptance criteria. Plan nodes gate on evidence before proceeding to execution.

### Phase 3: Execute

Implement following the plan. Each step requires passing gates (tests, code review, security scan). At 50% context, automatically hands off to a fresh session.

Key properties:

- **50% context handoff** -- switches to a clean session before quality degrades.
- **A/B blind review** -- a second AI agent with a clean context reviews the implementation independently.
- **Evidence gating** -- each phase must produce verified artifacts before the next phase starts.

---

## Advanced Workflows

| Workflow | Trigger | Purpose |
| :------- | :------ | :------ |
| **Race** | `/lx-race` | Parallel candidate generation. Multiple AI agents produce independent solutions, then a judge selects or merges the best. |
| **OMA** | `/lx-oma` | Optimized Multi-Agent -- concurrent specialized agents working on different parts of a large task with lock management. |

---

## Related

- [Editions: Three-layer comparison](../governance/us/editions.md)
- [Quickstart: Install Base](../guides/us/quickstart.md)
- [For Experts: Enhanced activation](../guides/us/for-experts.md)
