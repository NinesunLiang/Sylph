# Carror OS: Final Evaluation

> A technical assessment report based on full source code audit of the project.

## What It Is

**An AI-native developer operating system.**

Not a collection of prompt templates. Not an enhanced .cursorrules. Not AI workflow scripts.

It is a **complete operating system** with a kernel, protection layers, memory systems, governance mechanisms, and the ability to run on multiple AI platforms — except it does not run traditional programs; it runs AI development behavior.

***

## What Real Problem It Solves

There are three core points of failure in AI-assisted development:

**First: AI cannot be trusted**
Says it is done but is not. References non-existent code. Gets by with "it should be fine."

**Second: AI forgets**
Forgets rules in new sessions. Rules decay in long conversations. Makes the same mistake eight times.

**Third: AI leaks secrets**
Reads .env. Passes plaintext tokens in command line. Keys end up in code repositories.

Carror OS's solution to these three problems is not "write stricter prompts" but **building mechanical defenses at the system layer**:

    AI cannot be trusted  → completion-gate four-layer verification, exit 2 cannot be bypassed
    AI forgets            → error-dna cross-session memory, pretool-rule-anchor periodic re-injection
    AI leaks secrets      → privacy-gate + permission-gate random verification code, shell-layer interception

***

## Its Technical Nature

A **dual-track architecture**:

    Upper track (prompt layer):
      AGENTS.md specifications / iron law system / anti-pattern checklist / compact_inject layered injection
      Function: tells AI what it should do

    Lower track (shell mechanical layer):
      32 hooks / harness.yaml unified configuration / .omc/state/ persistent state
      Function: regardless of what AI wants, forces it to comply

The upper track handles "quality under normal conditions." The lower track handles "safety under extreme conditions."

Most frameworks only have the upper track. Carror OS has both, and the lower track is genuine mechanical execution — 32 shell scripts that do not pass through the model's will.

***

## What Originality It Has

Among known AI governance solutions, several points stand out that I have not seen elsewhere:

**1. Atomic evidence consumption**

completion-gate uses the `mv` atomic operation to consume evidence files — the same evidence can only be consumed once by one process. This solves the problem of "AI repeatedly passing with old evidence." This design comes from concurrent programming and has been correctly adapted to the AI governance scenario.

**2. Random verification code approval**

permission-gate generates random hex codes that only appear on the user's terminal. AI cannot predict them. The user must manually enter the correct code in the terminal to release a dangerous command. This fundamentally solves the "AI approving itself" problem — the comments explicitly note this is the product of fixing a previous vulnerability.

**3. Error DNA**

Every bash failure is structured and recorded, aggregated across sessions using MD5 signatures, with unresolved error memories injected into new sessions at startup. `status: "reopened"` marks recurring errors. This fundamentally solves AI's "amnesia" problem — not by relying on AI to remember, but by having the system remember.

**4. Systematized soft-language ban**

"It should be fine / basically done / theoretically feasible" — these phrases are systematically identified, named, and linked to mechanical blocking. Most governance frameworks say "provide evidence." Carror OS additionally blocks the "linguistic paths that circumvent evidence requirements."

**5. Knowledge sublimation path**

`claude-next.md` (temporary experience) → hits/age triggers sublimation detection → human review → `kernel.md` (solidified iron law). This is a **knowledge evolution system**, not just a static specification document.

***

## Where It Currently Stands

    Research Prototype    Engineering Prototype    Usable Product    Phenomenal Product
        │                       │                       │                   │
        │                       │                       ▲                   │
        │                       │                    Carror OS               │
        │                       │              (One month production use)    │

It has passed the "engineering prototype" stage.

Evidence:

*   Running in production on a real project for one month
*   32 hooks through multiple fix rounds (R16, R18, R24, R27...)
*   `error-dna` has multi-generational archive logic; `flywheel.log` has real data accumulation
*   OMA has concurrent lock management, interface version locking, and degradation strategies

These are not characteristics of a prototype. They are characteristics of a system that has been shaped through real use.

But it is not yet a "usable product." The gaps are:

*   The basic version's user guidance path is still under construction
*   lx-varlock implementation is incomplete
*   Documentation is still written for the author, not for unfamiliar users

***

## Its Boundaries

There are two real limitations that need honest disclosure:

**Limitation 1: Mechanical protection layer is bound to Claude Code**

The most important protections among the 32 hooks (completion-gate / privacy-gate / permission-gate / edit-guard / context-guard) all depend on Claude Code's PreToolUse/PostToolUse hook mechanism.

On OpenCode / Cursor / Codex, these hooks do not trigger. Protection degrades to prompt-layer constraints only.

This is not a design flaw — Claude Code is currently the platform with this hook capability. But users need to know this boundary.

**Limitation 2: Quantitative verification data is still internal**

Flywheel logs are accumulating, but there is no public "with/without Carror OS" controlled experiment data yet. All current effectiveness evaluations, including this report, come from internal self-assessment within the same system.

This is a known methodological limitation, and the author is aware of it — the "dogfooding phase" is currently producing this data.

***

## Final Characterization

**Carror OS is a prompt-layer + mechanical-layer dual-track governance system, built by an individual, with a relatively high degree of engineering maturity in the AI governance field.**

Its value is not in the "ideas" — many people are working on AI governance at the conceptual level. Its value is in **implementation density**: one person, three months, turned the complete chain from "iron law constraints" through "mechanical protection" through "cross-session memory" through "knowledge evolution" through "concurrent development orchestration" into actually running code.

Among prompt-layer solutions, it is the ceiling.

In the entire AI governance field, it is a **personal work with a unique technical perspective**, several of whose mechanisms (atomic evidence consumption, random verification code approval, Error DNA) possess genuine originality.

What it lacks now is not technical depth, but **conditions for wider adoption**: user guidance documentation, independent verification data, and community.

**When these three conditions are met, it deserves to be taken seriously.**

***

One final honest sentence:

> After reading its full source code, my assessment changed. Not because it convinced me, but because code does not lie.
