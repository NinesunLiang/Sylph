# Carror OS Product Guide: Three-Stage Product Structure and Full Feature Reference

> **Version**: v6.1.9 | **Updated**: 2026-05-13
> **Design Philosophy**: Guard First, Arm Later

---

## Design Philosophy

An operating system never forces users to learn complex system calls right after boot. It should silently manage memory and processes in the background.

Carror OS proposes the **"Guard First, Arm Later"** progressive delivery philosophy, dividing the system into three progressive layers like a rocket architecture:

- **Level 1 - Harness Only**: The lowest-level kernel firewall. Physical interceptors only, zero cognitive burden.
- **Level 2 - Base Edition**: Silent guardian. Adds 10 automated review gates, passively triggered, fully automatic.
- **Level 3 - Enhanced Edition**: Advanced arsenal. 24 pipeline Skills, actively scheduled, requires command authority.

---

## Level 1 — Harness Only (Pure Kernel Edition)

**Composition**: 32 low-level Hook scripts (30 registered and active + 2 standalone tools)
**Design**: Zero cognitive burden. No active workflow. AI is simply fitted with safety restraints.

| Capability Module | Specific Contents | Description |
|:-----------------|:-----------------|:------------|
| Bottom-Layer Defenses (Hooks) | `privacy-gate`, `context-guard`, `permission-gate` and 32 other Hooks | Intercepts privacy leaks, dangerous commands, 80% Context circuit break, records Error DNA |

**Suitable for**: Minimalists who want to add a physical foolproof lock to AI without seeing any complex configuration.

---

## Level 2 — Base Edition (Basic Guardian, Default Recommended)

**Composition**: All Level 1 defenses + 10 automated review gate Skills
**Design**: Silent quality control. Passively triggered, fully automatic.
**Installation**: `bash install.sh base`

| Capability | Function | Trigger Method |
|:-----------|:---------|:---------------|
| Bottom-Layer Interception (Hooks) | Physical blocking of AI hallucinations, destructive commands, privacy leaks, and long-conversation intelligence decay | Silent interception (anytime) |
| `lx-pre-commit` | Pre-commit quality gate controller, includes type detection, incremental build, tests, and code review | `/lx-pre-commit` or integrated as Git Hook |
| `lx-pre-push` | Pre-push security and compliance gate, includes commit format validation | `/lx-pre-push` |
| `lx-code-review` | Language-independent general code review (with Auto-fix) | Gate auto-wake / manual invocation |
| `lx-style-guide` | Style specification review | Gate auto-wake / manual invocation |
| `lx-oma` | OMA concurrent lock management | Silent background / manual invocation |
| `lx-oma-hier` | Hierarchical PRD decomposition — splits ultra-large PRDs by functional domain into Sub PRDs | Silent background / manual invocation |
| `lx-perf-analysis` | Performance analysis and diagnostics | Silent background / manual invocation |

**Suitable for**:
- Newcomers to AI-assisted development who do not want to change their existing development habits
- Those who just need a "code-literate AI" to chat with and automatically catch issues before committing

---

## Level 3 — Enhanced Edition (Full-Stack Enhanced)

**Composition**: All Level 2 capabilities + 14 active workflow Skills
**Design**: High learning cost, high return rate. Actively scheduled, requires command authority.
**Installation**: `bash install.sh enhanced`

### Three Task-Driven Engines

| Skill | Positioning | Description |
|:------|:------------|:------------|
| `/lx-rpe` | Large feature pipeline | Research → Plan → Execute three-phase, with 50% sweet-spot handoff and A→B→A cross-verification adversarial |
| `/lx-task-spec` | Medium complex tasks | Precise AC-driven, no lengthy PRD required |
| `/lx-todo` | Scattered small tasks | ≤3 files, 5-step fast loop, auto-upgrade if exceeded |

### Advanced Diagnostics and Generation

| Skill | Description |
|:------|:------------|
| `/lx-root-cause-analysis` | 5-Why root cause tracing |
| `/lx-frontend-test` | Frontend-specific automated test framework |

### Professional Operations and Monitoring

| Skill | Description |
|:------|:------------|
| `/lx-status` | Health monitoring dashboard: Token savings, error self-healing rate, task execution chain diagram |
| `/lx-varlock` | Enterprise DLP privacy masking proxy, bidirectional transparent obfuscation |
| `/lx-validate-skill` | Skill integrity verification, auto-detects metadata/script drift |
| `/lx-race` | Race condition detection |

**Suitable for**:
- Tech Leads, architects, senior full-stack engineers
- Those taking on extremely complex refactoring projects requiring strict engineering discipline
- "One-Man Army" hackers who need AI to execute complex multi-step debugging and need real-time monitoring of token efficiency and self-healing rates

---

## Seamless Switching

Carror OS's architecture is decoupled. You can switch between the three levels at any time. The underlying Hooks never go offline and are lossless:

```bash
# Minimalism: bottom-layer defenses only
bash install.sh harness

# Default guardian: automatic gates and review before commit
bash install.sh base

# Full power: activate large model workflow pipelines
bash install.sh enhanced
```

---

## Post-Installation Verification

### Semi-Automated Verification (Recommended for new members, daily regression)

| File | Description |
|:-----|:------------|
| `docs/tests/auto-feature-test.md` | Verification execution manual. Say "please execute Zone 1 tests" to AI to start |
| `docs/tests/auto-feature-test-log.md` | Verification report template, record while testing |

### Full Manual Verification (Formal delivery, security audit, Zero Trust)

| File | Description |
|:-----|:------------|
| `docs/tests/manual-acceptance-test.md` | 49-item full manual verification checklist, covering all 32 Hooks and core Skills |
| `docs/tests/manual-acceptance-test-log.md` | Corresponding report template; failed items must include root cause and fix plan |

### Ultimate Judgment (Dogfooding prerequisite)

| File | Description |
|:-----|:------------|
| `docs/tests/final-exam.md` | Ultimate manual judgment checklist, zero trust principle, every item must be personally executed |

---

**Carror OS — AI Native Developer Operating System**
**Guard First, Arm Later.**
