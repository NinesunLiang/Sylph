# The First Turn of the Flywheel: How Dogfooding Fed Back Into Carror OS Itself

> **Philosophy #4 "Not Verified = Not Done" proves itself**
> *When a framework is used to govern its own improvement, it becomes a living system.*

---

## Prologue: An Ordinary Decomposition Task

On May 12, 2026, a large frontend project (26 PRDs, React/TypeScript) started a PRD hierarchical decomposition. The goal was to use `lx-oma-hier` skill to split 26 master PRDs into 5 functional domain Sub PRDs.

This was a routine invocation of Carror OS on a real project. Routine enough that nobody expected it would change Carror OS itself.

---

## Act 1: Oracle Raised Red Flags

Decomposition complete. Five domains (platform infrastructure, ecosystem resources, playground, visualization dashboard, configurator) — structurally sound, business logic accurate. Everything looked normal.

Then Oracle began its review.

**Round 1, Product Review: 3 FAILs.**

- Session entity ownership conflict — D03's table says "Own", D05's prose says "lifecycle managed by D05." *One domain claims Own in a table row, another claims it in prose. The grep script only checked table rows.*
- 3 NFR numbers with zero traceability — 1500ms, 10 tokens/s, 2000ms — three critical performance metrics that couldn't be found anywhere in the master PRD. Violation of Iron Law #7.
- Dependency type confusion — component-level code reuse mislabeled as service dependency in INDEX.md, which would mislead development ordering.

**Round 2, Process Review: 43/100.**

Not 43 for content quality — 43 for process compliance. §3.2 MECE checklist completely skipped. §8 Pipeline integration not executed. §9 Observability not written. §11 Manual gate checklist never triggered. The AI executed the content but skipped every validation step the framework required.

**Round 3, Business Review: 2 more FAILs.**

Knowledge base registration document with no domain assignment. D02 lacks cohesion (circuit breaker infrastructure + resource registry + marketplace browsing all in one domain).

Three review passes. Every pass found blood.

---

## Act 2: The Dogfood Aftertaste

Normally the story ends here — find problems, fix Sub PRDs, project moves on. That's what QA does.

But Carror OS has an unusual principle:

> **Dogfooding Feedback Loop Protocol (AGENTS.md §Dogfooding Feedback Loop)**
> *Core cycle: discover problem → fix problem → add mechanism → propagate fix to source/ and packages/*

When an AI agent discovers Carror OS's own problems, it doesn't just fix them in the client project — it feeds the mechanism improvements back into Carror OS itself.

So we made a critical triage decision:

| Finding | Domain | Action |
|---------|--------|--------|
| Session ownership conflict | Script validation blindspot — **framework issue** | → claude-next.md DG-01 |
| NFR sources untraceable | Input-stage validation missing — **framework issue** | → claude-next.md DG-02 |
| Manual/pipeline mode confusion | Skill design flaw — **framework issue** | → claude-next.md DG-03 |
| Checkbox execution pattern | Skill rhythm — **framework issue** | → claude-next.md DG-04 |
| Single-pass Oracle insufficient | Review methodology — **framework issue** | → claude-next.md DG-05 |
| D02 lack of cohesion | Project-specific business logic | → Skip, not framework |
| Evaluator tool independence | Project-specific product decision | → Skip, not framework |

7 framework-level lessons were extracted from 20+ findings in the client project.

---

## Act 3: The Framework Evolved

These lessons then flowed back into Carror OS's core skill.

`lx-oma-hier` upgraded from v1.2.0 to v1.3.0, 7 changes:

| Section | From | To | Why |
|---------|------|----|-----|
| **§2** | Default path + no mode detection | Execution mode detection + path priority rule (kernel.md > user > default) | Dogfood found "triple path mismatch" and DG-03 mode confusion |
| **§3.1** | Entity recognition implicit | Mandatory explicit entity table + conflict pre-check | Oracle round 1 found Session conflict — explicit output would have caught it |
| **§3.2** | 10-item checkbox per domain (50 iterations) | Unified MECE summary table after all domains | DG-04 — AI doesn't execute in human "check-as-you-go" rhythm |
| **§3.3** | Dependency graph no type | INDEX.md "dependency type" column (service/code) | P2 — code dependency mislabeled as service misleads ordering |
| **§8** | Pipeline write always executed | Manual mode skip + report note | DG-03 — no pipeline.yaml should not error |
| **§9** | Telemetry write without check | Environment detection + silent skip | DG-03 — no .omc/state should not error |
| **§11** | Gate chapter existed but never triggered | Mandatory checklist output + pending issues table | Oracle found §11 was never triggered in any execution |

Simultaneously, `claude-next.md` gained 10 new lessons (5 DG + 5 META), and source mirrors were synced.

---

## Act 4: The Flywheel Data

The entire cycle formed a complete flywheel:

```
  Client project (20+ findings)
        ↓
  Oracle review (3 passes, 3x filter)
        ↓
  Triage → 7 framework lessons + 5 meta-lessons
        ↓
  lx-oma-hier v1.2.0 → v1.3.0 (7 changes)
        ↓
  claude-next.md +10 lessons
        ↓
  Source mirror sync (lx-skills-v5 + harness-kit)
        ↓
  Next dogfood → flywheel turns again
```

| Metric | Value |
|--------|-------|
| Raw findings | ~20+ |
| Framework lessons extracted | 7 (DG-01~DG-05 + META-01~META-02 combined) |
| Skill version upgrade | v1.2.0 → v1.3.0 |
| Files changed | 5 (SKILL.md ×2 + claude-next.md ×2 + dogfood record) |
| Processing time | ~1 session (reading, analysis, modification, recording) |

---

## Epilogue: A Living System

The most fascinating part of this story isn't the technical details. It's what it proves about Carror OS's core design hypothesis:

> **A system that governs its own improvement is alive.**
>
> ——the ultimate manifestation of Philosophy #6 (Zero Trust in AI)

Carror OS's Oracle, when called upon to review a decomposition task, found 3 FAILs — 2 of which were "automated script missed prose-described entity conflict" and "NFR sources not validated at input stage." These weren't bugs in the client project. They were **validation blind spots in Carror OS's own framework**.

If Carror OS were just a passive toolset, these blind spots would never have been discovered. But because it dogfoods — uses itself to govern its own development — these blind spots were exposed in a real client project and immediately fed back into the framework itself.

This isn't a story about "Project A completed a PRD decomposition."
This is a story about "Framework X discovered its own blind spots during a routine call, and fixed itself in the same session."

The flywheel has turned. This is just the first revolution.

---

*Recorded 2026-05-14, based on #7 dogfooding processing meta-record.*
*Source data: `.omc/state/dogfood/dogfood-20260512-lx-oma-hier.yaml`*
*Meta record: `.omc/state/dogfood/dogfood-20260514-processing-pipeline.yaml`*
