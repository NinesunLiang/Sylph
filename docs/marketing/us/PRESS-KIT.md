# Carror OS — Give Your AI Brakes

> **In one sentence**: Carror OS is the first open-source governance framework that provides physical-level behavioral constraints on AI at the Hook application layer. It doesn't "ask" — it "pulls the plug."

---

## The Problem

By 2026, AI-assisted coding has become mainstream. But every engineer has experienced:

- AI executing `rm -rf /var/www` without you noticing
- AI saying "done" — but doing nothing
- AI sending your `.env` file contents to a cloud API
- After 30 turns of conversation, AI starts editing files it shouldn't
- The same bug "fixed" 8 times, each time with "this should work now"

**Existing solutions all fail** — Cursor Rules, Claude Code Hooks, Copilot Instructions all operate at the Prompt layer, relying on "please" and "suggestions." AI can politely ignore them.

---

## The Solution

Carror OS chose a completely different path: **don't talk to the AI. Block its tool calls directly.**

```
Normal flow:   User → AI → Tool Call → Execute
Cursor:        User → AI → [Prompt Suggestion] → Tool Call → Execute
Carror OS:     User → AI → [⚠️ Hook Intercept] → Deny / Authorize / Audit
```

### Three-Layer Architecture

| Layer | What It Does | How It Works |
|------|------|---------|
| **Harness** (Kernel) | 32 application-layer Hooks, intercept before AI tool calls | `Exit 2` hard block, not Prompt request |
| **Skills** (Userland) | 24 workflow Skills, full cycle from PRD to commit | Markdown instruction sets + 19 Python tools |
| **Profiles** (Bridge) | One-click adaptation for 5 language environments | YAML config, zero-code switch |

---

## Key Capabilities

### 1. You Pulled the Plug on AI Before It Could `rm -rf`

32 Hooks covering six security domains:

| Domain | Representative Hook | What It Blocks |
|------|----------|---------|
| Permission Gate | `permission-gate.sh` | `rm -rf`, `DROP TABLE`, `git push --force` |
| Privacy Line | `privacy-gate.sh` | `.env`, `*.pem`, `id_rsa`, plaintext tokens |
| Context Breaker | `context-guard.sh` | Physically locks all writes when context >= 80% |
| Delivery Verification | `completion-gate.sh` | AI claiming "done" without VERIFIED evidence |
| Read-Write Guard | `edit-guard.sh` | Can't edit files not yet read |
| Scope Freeze | `pretool-edit-scope.sh` | File modifications outside task scope |

**All Hooks have passed L1-L4 four-layer testing (manual acceptance + auto Hook validation + code scanning + format gates) with full pass. Passed ShellCheck/Bandit real security scans (0 real business defects). Industry standard self-assessed compliance mapping (OWASP ASVS v4.0.3 / MITRE ATLAS / NIST AI RMF 1.0): 75/75 coverage [internal self-assessment, not third-party certification].**

### 2. AI Never Sees Your Real Secrets

`varlock` is an open-source bidirectional anonymization proxy:

```
AI sees:          curl -H "Authorization: {API_KEY}"
Actually runs:    curl -H "Authorization: sk-ant-abc123..."
AI writes back:   API_KEY={API_KEY}
Stored on disk:   API_KEY=sk-ant-abc123...
```

The AI always works in a data-isolated sandbox, never touching any plaintext credentials.

### 3. Long Conversations No Longer Mean Slow Dementia

Three-layer anti-drift mechanism running automatically — no manual `/compact` needed:

| Layer | Trigger | Action |
|------|---------|------|
| SessionStart | Every new session | Inject constitutional rules into context |
| Every 10 turns | Turn counter | Reiterate 7 constitutional principles |
| Every file write | Before write | Scope freeze + rule anchoring |
| 50% sweet spot | Context over half | Force handover, reset at cleanest state |

### 4. Not "Done" — Show Me the Evidence First

`completion-gate.sh` requires AI to provide `>= 20 characters` of VERIFIED evidence before marking a task complete. No test logs, no output screenshots, no verification commands → the task stays permanently "in progress."

---

## Protection Capability Comparison

> **Note**: Carror OS is a governance layer that runs on top of AI CLIs, not a coding tool or IDE. The table below compares **native defense capabilities at the execution layer** versus **full-stack protection with Carror OS governance added**, not Carror OS vs. coding tools as peers. Self-comparisons across Carror OS versions use a different format.

| Dimension | Carror OS | Devin | Cursor Rules | Claude Hooks |
|----------|:--:|:--:|:--:|:--:|
| Defense Layer | **Exit 2 Physical Block** | Commercial black-box | Prompt soft constraint | Hook primitives |
| DLP | **Bidirectional anonymization proxy** | None | None | None |
| Context Protection | **3-layer auto anti-drift** | Unknown | None | Manual /compact |
| A/B Adversarial Review | **A→B→A cross-verification** | None | None | None |
| Concurrent Collaboration | **File lock + MECE decomposition** | Built-in | None | None |
| Task Pipeline | **RPE 9-step closed loop** | Built-in | None | None |
| Cost | **$0** | $500/mo | In subscription | In subscription |
| Auditability | **Fully open-source** | Commercial black-box | Partially open | Closed |

**Core competitive advantage**: Carror OS doesn't compete on "code writing speed." It solves a problem nobody else has seriously addressed — **how to constrain AI's lower bound of behavior at an engineering level.**

---

## Model Cost Freedom: High-End Reliability with Affordable Models

**The real bottleneck in AI coding isn't model intelligence — it's reliability.**

90% of daily development tasks — CRUD, refactoring, bug fixes, test writing — don't need a top-tier model's deep reasoning. They need a disciplined system: don't fabricate file:line references, don't claim "done" without verification, don't drift from the goal mid-task.

| Setup | Model Cost (per 1M tokens) | Reliability Mechanism |
|-------|---------------------------|----------------------|
| Opus 4.6 bare (CLAUDE.md only) | ~$15 | Model self-discipline |
| **DeepSeek v4 Flash + Carror OS** | ~$0.27 | **Physical hook enforcement + dual review** |
| **DeepSeek v4 Pro + Carror OS** | ~$1.10 | **Physical hook enforcement + dual review** |

> DeepSeek v4 Flash costs less than **1/50th** of Opus. Pro costs less than **1/13th**.

Carror OS bridges the model capability gap on three fronts:

1. **Discipline compensates for intelligence** — 41 explicit hook-blocked events (recorded in `skipped-errors.md`), all discipline issues (false completion, dangerous commands, context drift), not intelligence problems. A smarter model makes the same mistakes.

2. **Dual review compensates for blind spots** — Oracle + Meta-Oracle independent agent review system. Two review rounds found **zero overlapping** issues. Compute trades for coverage, filling single-model review gaps.

3. **Memory compensates for forgetting** — 76 battle-tested lessons accumulate across sessions. The knowledge-condenser automatically sublimates high-frequency lessons into permanent rules. Knowledge grows with usage time, independent of model version.

**Who benefits most:**
- **Individual developers** — DeepSeek v4 Flash pricing, near-Opus daily reliability
- **Small teams / startups** — Cover 90% of daily tasks with DeepSeek v4 Pro, reserve Opus for architecture decisions and complex algorithms
- **Anyone AI-bill-conscious** — Carror OS progressive loading + context compaction saves 14%-53% tokens in real sessions (20-turn measured data, `benchmark-report.md:178-179`)

> **The model is the engine. Carror OS is the brakes, seatbelts, and airbags.** A family car with safety systems gets you home more reliably than a race car with no brakes.

---

## Differentiation

The following designs have **no known comparable implementations** in the open-source community:

1. **varlock bidirectional anonymization proxy** — AI always works in a data-isolated sandbox
2. **completion-gate evidence gate** — Physically prevents AI from claiming completion without evidence
3. **Three-layer anti-drift mechanism** — Full-cycle coverage from SessionStart to every file write
4. **50% sweet-spot active handover** — Force reset when AI state is at its cleanest

---

## Capability Score

### Four-Dimension Capability Matrix

```
                    Long-term Gov.   AI Intelligence   Economy         Security
                    ────────        ────────         ────────        ────────
Carror OS           ████████▌       ███████▌        ████████▌       █████████
Devin Guardrails    ██████▌         ████████▌       ██████          ██████▌
Cursor Rules        ███▌            ██████▌         ██████▌         ██▌
Claude Code Hooks   █████▌          ██████▌         ██████▌         █████
Copilot Custom      ██▌             ██████▌         ██████▌         ██
```

### Composite Score (Opus 4.7 + GPT-5 model assessment, [internal assessment, not industry standard])

| Dimension | Score | Explanation |
|----------|:--:|------|
| Design Philosophy | 9.0 | "Guard First, Arm Later" philosophy is mature; three-stage rocket model is precise |
| Architecture Completeness | 8.5 | Kernel/userland layering + Hook/Skill/Script three-tier collaboration |
| Code Implementation | 7.5 | Hook and Python script quality is solid; package release process needs improvement |
| Documentation Quality | 9.0 | CHANGELOG 53KB, SKILL.md 471 lines, testing docs 49 items |
| Test Coverage | 8.0 | L1-L4 four-layer testing: 98 PASS / 0 FAIL / 0 SOFT, ShellCheck/Bandit 0 defects |
| Differentiation | 9.0 | 5 designs with no known comparable in open-source |
| Engineering Maturity | 7.0 | packages packaging needs fixing |
| Practicality | 7.0 | Strongly dependent on Claude Code/OpenCode Hook protocol |
| **Composite** | **8.1** | Advanced philosophy, solid design, engineering finishing touches in progress |

---

## Applicable Scenarios

| Suitable | Not Suitable |
|---------|------------|
| Teams collaborating on AI-assisted coding | Individual users wanting one-click power-up |
| Enterprises needing audit and compliance | Dev scenarios using only Web IDE |
| Security teams worried about AI data leaks | Free spirits who want no constraints at all |
| Long-term maintained large projects | One-off prototype development |

---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- base
```

Base edition: 32 Hook security foundation + 10 gate review Skills, zero learning curve.

```bash
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- enhanced
```

Enhanced edition: Full 24 Skills + RPE pipeline + full-stack arsenal.

---

## License

Open-source, MIT License. Carror OS by Sylph.

---

*"Don't say 'should be fine' or 'theoretically supported.'" — Carror OS Constitution, Rule #6, the Soft Completion Language Ban*
