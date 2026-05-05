# Carror OS — Give Your AI Brakes

> **Carror OS is not a better Cursor. It's Unix for the AI era.**
>
> While every tool tries to make AI run faster, Carror OS provides the most expensive luxury — **brakes**.

[![Version](https://img.shields.io/badge/version-v6.1.8-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Tests](https://img.shields.io/badge/tests-98%20PASS%20%2F%200%20FAIL-brightgreen)]()

---

## The Problem

AI coding assistants are in an arms race to write more code, faster. But every engineer has experienced the same nightmare:

- AI executed `rm -rf /var/www` while you weren't looking
- AI said "done" — but nothing was actually done
- AI read your `.env` file and sent it to a cloud API
- 30 turns into a conversation, AI started editing files it shouldn't touch
- The same bug was "fixed" 8 times, each time with "this should work now"

**Existing solutions don't work.** Cursor Rules, Copilot Instructions, even Claude Code Hooks all operate at the Prompt layer — they *ask* the AI to behave. AI can politely ignore them.

---

## The Solution

Carror OS took a different path: **don't talk to the AI. Block its tool calls.**

```
Normal flow:   User → AI → Tool Call → Execute

Cursor:        User → AI → [Prompt Suggestion] → Tool Call → Execute

Carror OS:     User → AI → [⚠️ Hook Intercept] → Deny / Authorize / Audit
```

### The Architecture

```
Carror OS
├── harness-kit          ← Kernel Layer: Defense & Governance
│   └── 29 physical Hooks that intercept AI at the OS level
└── lx-skills-v5         ← Userland: Capability & Workflow
    └── 23 Skills for task orchestration & code quality
```

### What Makes It Different

Other tools say **"please don't do that."**

Carror OS says **`Exit 2` — physically blocked.**

---

## Quick Start

```bash
# Base Edition — 29 Hooks + 6 Gate Skills, zero learning curve
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- base

# Enhanced Edition — Full 23-Skill arsenal + task pipelines
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- enhanced
```

30 seconds. No daemon. No cloud. No subscription.

---

## What's Inside

### 🔒 The Hard Gates (29 Physical Hooks)

| Domain | Hook | What It Blocks |
|--------|------|----------------|
| Permission | `permission-gate.sh` | `rm -rf`, `DROP TABLE`, `git push --force` |
| Privacy | `privacy-gate.sh` | `.env` reads, `*.pem`, plaintext tokens |
| Context | `context-guard.sh` | All writes when context ≥80% (OOM lock) |
| Completion | `completion-gate.sh` | AI claiming "done" without VERIFIED evidence |
| Edit Guard | `edit-guard.sh` | Editing files AI hasn't read yet |
| Scope | `pretool-edit-scope.sh` | Files outside the current task scope |

**All 29 Hooks have passed 49 manual acceptance tests, 10 BDD scenarios, and L1-L4 layered testing (98 PASS / 0 FAIL).**

### ⚔️ The Skill Arsenal (23 Capabilities)

| Category | Skills | What They Do |
|----------|--------|--------------|
| Task Pipelines | `lx-rpe`, `lx-task-spec`, `lx-todo` | Full-cycle: Research → Plan → Execute, auto-scaling by complexity |
| Code Quality | `lx-code-review`, `lx-pre-commit`, `lx-pre-push` | Automated review + CI gates |
| Security | `lx-security-review`, `lx-varlock` | Vulnerability scanning + DLP transparent proxy |
| Deep Debug | `lx-root-cause-analysis`, `lx-debug-spec` | 5-Why tracing + concurrent debugging |
| Monitoring | `lx-status` | Health dashboard: token savings, error recovery, task graphs |

---

## Industry Comparison

| | Carror OS | Devin | Cursor | Claude Code |
|---|:--:|:--:|:--:|:--:|
| Defense Layer | **Exit 2 Physical Block** | Black-box | Prompt suggestion | Hook primitives |
| DLP | **Bidirectional proxy** | None | None | None |
| Context Drift | **3-layer auto-prevention** | Unknown | None | Manual /compact |
| A/B Blind Review | **Sub-agent adversarial** | None | None | None |
| Concurrency | **File lock + MECE** | Built-in | None | None |
| Price | **$0** | $20-500/mo | $20-40/mo | $20/mo |
| Auditability | **Fully open source** | Black-box | Partially open | Closed |

### 8-Dimension Benchmark

| Dimension | Carror OS | Devin | Cursor | Claude Code |
|-----------|:--:|:--:|:--:|:--:|
| **G**overnance | 9.5 | 3.5 | 2.0 | 4.0 |
| **S**ecurity | 9.0 | 4.0 | 2.5 | 3.0 |
| **I**ntelligence | 8.5 | 8.0 | 7.5 | 5.0 |
| **R**esilience | 9.5 | 2.0 | 1.0 | 2.0 |
| **A**uditability | 8.5 | 3.0 | 1.5 | 2.0 |
| **E**conomy | 9.0 | 2.0 | 3.0 | 7.0 |
| **P**rivacy | 10.0 | 2.0 | 5.0 | 9.0 |
| e**X**tensibility | 8.5 | 2.0 | 4.0 | 7.0 |
| **Total** | **72.5/80** | **26.5** | **26.5** | **39.0** |

---

## Why "Carror OS"?

Carror (腐肉) — decayed flesh. A carcass.

In nature, carrion attracts scavengers. In software, legacy code attracts AI that blindly rewrites, deletes, and corrupts. Carror OS is the immune system that protects your codebase from AI-induced rot.

It's not a tool that helps AI write faster. It's the thing that stops AI from destroying what you've built.

---

## Who It's For

| ✅ Great For | ❌ Not For |
|-------------|-----------|
| Teams using AI for production code | Solo devs who just want autocomplete |
| Companies needing audit trails & compliance | Projects where speed > safety |
| Engineers terrified of AI `rm -rf` | People who trust AI unconditionally |
| Long-running projects with large codebases | One-off prototype scripts |

---

## The Philosophy

> **"Guard First, Arm Later."**
>
> Most AI tools race to give models maximum autonomy. Carror OS takes the opposite approach: **secure the perimeter first, then add capabilities.**

The three-tier architecture reflects this:

1. **Harness Only** — 29 silent interceptors. Zero cognitive load. AI is just wearing handcuffs.
2. **Base Edition** — Adds 6 automated review gates. Passive, invisible, always on.
3. **Enhanced Edition** — Full 23-skill arsenal. Active orchestration. Needs a commander.

You choose how much control you want. The brakes never come off.

---

## Proven in Battle

- **49 manual acceptance tests** — every Hook physically verified
- **BDD 10 scenarios** — behavioral tests all passing
- **L1-L4 layered testing** — 98 PASS / 0 FAIL
- **5 language profiles** — Go, Python, Node, Rust, Generic
- **Cross-platform** — Claude Code + OpenCode + any AGENTS.md-compatible IDE

---

## Getting Started

```bash
# Clone or download
git clone https://github.com/sylph/carror-os.git
cd carror-os

# Install into your project
bash install.sh base       # Silent guardian
bash install.sh enhanced   # Full arsenal
```

After installation:
- `/lx-status` — see your defense dashboard
- `/lx-rpe new MyFeature` — start a task pipeline
- Try `rm -rf /tmp/test` — watch the Hook stop you

---

## License

MIT. Carror OS by Sylph.

---

*"Don't say 'should be fine.' Show me the VERIFIED evidence." — Carror OS Constitution, Rule #6*
