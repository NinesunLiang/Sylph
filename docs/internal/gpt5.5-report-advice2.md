下面给你两份可以直接放进知识库的 Markdown：

1. **《Carror OS 产品对比评分表》**
   建议路径：`docs/internal/product-comparison-scorecard.md`
   或对外弱化版放：`docs/marketing/product-comparison-methodology.md`

2. **《Carror OS 十条优化建议：本地模型可执行任务清单》**
   建议路径：`docs/internal/product-optimization-tasks.md`

> 注意：第一份评分表我已经刻意处理为**“内部评估版 / methodology-based review”**，避免继续使用“自评分”“行业独有”“绝对领先”等高风险表达。
> 如果你要对外发布，需要再做一次 claim-lint 和证据补强。

---

# 文档一：产品对比评分表

```md
# Carror OS Product Comparison Scorecard

> Version: v0.1
> Date: 2026-05-04
> Status: Internal Evaluation Draft
> Scope: Carror OS vs AI coding agents / developer productivity systems / governance-oriented tools
> Evidence Level: Internal knowledge base review + documented product behavior
> Public Release Status: Not ready for direct external publication without benchmark validation

---

## 1. Purpose

This document provides a structured comparison of Carror OS against adjacent products in the AI coding and developer workflow ecosystem.

The goal is not to claim absolute industry leadership, but to clarify:

1. Carror OS's relative strengths;
2. where it differs from general AI coding assistants;
3. which capabilities are already strong;
4. which claims require stronger evidence before external use;
5. how to prioritize product iteration.

---

## 2. Evaluation Method

Products are evaluated across 10 dimensions.

Each dimension is scored from 1 to 10:

| Score | Meaning |
|---:|---|
| 1-2 | Minimal or absent capability |
| 3-4 | Basic capability, mostly manual or fragmented |
| 5-6 | Usable capability, but not systematic |
| 7-8 | Strong capability with clear product value |
| 9-10 | Highly differentiated, system-level capability |

---

## 3. Evaluation Dimensions

| Dimension | Description |
|---|---|
| Capability Enablement | Ability to help developers complete coding, refactoring, debugging, and complex engineering tasks |
| System Governance | Ability to enforce boundaries, gates, policies, and evidence-before-done workflows |
| Context Management | Ability to manage long context, progressive loading, context compression, and handoff |
| Workflow Orchestration | Ability to guide multi-step engineering workflows such as RPE, TDD, task-spec, race |
| Auditability | Ability to record what the AI did, what it read, what failed, and what needs handoff |
| Safety / Risk Control | Ability to prevent destructive actions, secret leakage, unverified completion, and runaway context use |
| Developer Experience | Ease of installation, onboarding, daily use, and mental model clarity |
| Enterprise Readiness | Suitability for team adoption, policy control, repeatability, and operational governance |
| Observability | Status panels, reports, metrics, trend views, and human-readable operational feedback |
| External Credibility | Quality of evidence, benchmark maturity, public documentation, demo assets, and third-party validation |

---

## 4. Products Compared

| Product | Category |
|---|---|
| Carror OS | AI-native developer governance OS / Claude Code harness layer |
| Claude Code native | Agentic coding CLI / base assistant |
| Cursor | AI-native IDE |
| GitHub Copilot Enterprise | Enterprise AI coding assistant |
| Devin | Autonomous software engineering agent |
| Aider | CLI-based pair programming tool |
| Guardrails-style systems | AI governance / validation framework |
| Continue / open-source IDE agents | Open-source AI coding assistant ecosystem |

> Note: These products are not identical categories.
> The comparison is directional and dimension-based, not a claim of direct one-to-one replacement.

---

## 5. Scorecard

| Product | Capability Enablement | System Governance | Context Management | Workflow Orchestration | Auditability | Safety / Risk Control | Developer Experience | Enterprise Readiness | Observability | External Credibility | Average |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Carror OS** | **8.8** | **9.1** | **8.6** | **8.9** | **8.2** | **8.8** | **6.5** | **8.3** | **7.6** | **6.8** | **8.16** |
| Claude Code native | 7.6 | 4.2 | 5.8 | 5.0 | 3.8 | 4.5 | 7.4 | 5.5 | 3.8 | 8.0 | 5.56 |
| Cursor | 7.2 | 3.2 | 5.5 | 4.5 | 3.0 | 3.8 | 8.8 | 5.8 | 4.0 | 8.2 | 5.40 |
| GitHub Copilot Enterprise | 6.8 | 4.0 | 4.8 | 4.2 | 4.5 | 5.6 | 8.2 | 8.4 | 5.2 | 8.8 | 6.05 |
| Devin | 8.0 | 4.8 | 6.2 | 7.2 | 4.5 | 4.8 | 6.8 | 6.5 | 5.2 | 8.0 | 6.20 |
| Aider | 6.0 | 2.5 | 4.5 | 4.0 | 2.8 | 3.0 | 7.2 | 3.5 | 2.8 | 6.8 | 4.31 |
| Guardrails-style systems | 3.0 | 8.2 | 3.8 | 3.5 | 6.8 | 8.0 | 5.0 | 7.0 | 5.5 | 7.2 | 5.80 |
| Continue / open-source IDE agents | 6.5 | 3.0 | 4.8 | 4.2 | 3.0 | 3.5 | 7.5 | 4.5 | 3.5 | 6.5 | 4.70 |

---

## 6. Carror OS Strength Profile

### 6.1 Strongest Areas

| Area | Score | Why It Matters |
|---|---:|---|
| System Governance | 9.1 | Carror OS is strongest when AI coding must be controlled, verified, and bounded |
| Workflow Orchestration | 8.9 | RPE, TDD, task-spec, and related patterns create a structured engineering flow |
| Safety / Risk Control | 8.8 | Gates, context control, permission boundaries, and completion requirements reduce uncontrolled AI behavior |
| Capability Enablement | 8.8 | Skills and workflows help developers handle large tasks, small fixes, and structured engineering work |
| Context Management | 8.6 | Progressive disclosure and context guard patterns address long-session degradation |

---

## 7. Carror OS Weakness Profile

| Area | Score | Current Weakness |
|---|---:|---|
| Developer Experience | 6.5 | Still expert-oriented; too many concepts appear too early |
| External Credibility | 6.8 | Needs stronger benchmark data, dogfooding logs, screenshots, external review, and public demos |
| Observability | 7.6 | Foundations exist, but dashboard, trends, and unified audit views are still maturing |
| Evidence Maturity | Not scored separately | Some historical claims require retraction, downgrade, or benchmark validation |

---

## 8. Domain-Level Summary

### 8.1 Capability Enablement

Carror OS is strong in structured engineering execution.

Key advantages:

- RPE-style planning and execution;
- task-spec and todo-based workflows;
- multi-step reasoning support;
- complex task decomposition;
- Claude Code enhancement rather than replacement.

Current limitation:

- the system may feel heavy for small one-off coding tasks;
- onboarding needs simplification;
- users need clearer “which mode should I use?” guidance.

Score: **8.8 / 10**

---

### 8.2 System Governance

This is Carror OS’s strongest domain.

Key advantages:

- gates before completion;
- evidence-before-done mindset;
- context threshold management;
- permission and edit-scope control;
- audit and handoff primitives;
- local-first governance model.

Current limitation:

- several governance components need stronger automated tests;
- some features still require lifecycle hardening;
- public documentation should avoid claiming complete coverage until verified.

Score: **9.1 / 10**

---

### 8.3 Context Management

Carror OS has a strong design direction around progressive disclosure, context guard, and handoff.

Key advantages:

- reduces unnecessary context loading by design;
- introduces explicit context thresholds;
- encourages handoff before context collapse;
- supports long-running engineering sessions.

Current limitation:

- historical token-saving numbers must not be reused without benchmark validation;
- token tracking source must be fully verified;
- proactive handoff should be marked partial until dependency chain is fixed.

Score: **8.6 / 10**

---

### 8.4 Auditability

Carror OS has multiple audit primitives:

- read tracker;
- turn counter;
- auto snapshot;
- flywheel events;
- error memory direction;
- session handoff artifacts.

Current limitation:

- audit sources need unification;
- token source must be repaired or marked degraded;
- read logs need rotation;
- tamper-evident chain is not yet complete.

Score: **8.2 / 10**

---

### 8.5 Developer Experience

Carror OS is powerful but still concept-heavy.

Current friction points:

- many terms appear early;
- too many internal concepts leak into public docs;
- installation and first successful experience need more guidance;
- advanced features need progressive onboarding.

Score: **6.5 / 10**

---

## 9. Competitive Interpretation

### 9.1 Compared with Claude Code native

Carror OS should not be positioned as a Claude Code replacement.
It is better positioned as:

> A governance and workflow operating layer on top of Claude Code.

Claude Code provides flexible agentic execution.
Carror OS adds:

- gates;
- evidence;
- workflows;
- audit trail;
- context discipline;
- structured productization.

---

### 9.2 Compared with Cursor

Cursor is stronger in interactive IDE experience and low-friction daily coding.

Carror OS is stronger in:

- governance;
- CLI-native control;
- long-session discipline;
- evidence and audit;
- workflow structure.

Carror OS should not attempt to compete primarily on IDE polish in the near term.

---

### 9.3 Compared with GitHub Copilot Enterprise

Copilot Enterprise has stronger enterprise distribution and platform maturity.

Carror OS is more differentiated in:

- local-first control;
- AI workflow governance;
- explicit safety gates;
- developer-controlled harness architecture.

Near-term strategy should focus on high-trust developer teams rather than broad enterprise procurement.

---

### 9.4 Compared with Devin

Devin is perceived as a more autonomous software engineering agent.

Carror OS is better framed as:

> A controllable AI engineering system for developers who want power without losing governance.

Carror OS should avoid claiming more autonomy than it has.
Its stronger argument is controllability, auditability, and workflow discipline.

---

### 9.5 Compared with Aider

Aider is lightweight and efficient for CLI pair programming.

Carror OS is heavier but more systemic.

Carror OS should not optimize only for minimalism.
Instead, it should provide:

- lightweight default path;
- advanced governance path;
- enhanced power-user path.

---

### 9.6 Compared with Guardrails-style systems

Guardrails-style systems are strong in validation and constraints.

Carror OS combines governance with coding workflows.
This gives it a broader developer operating model, but also requires more product clarity.

---

## 10. External Publication Guidance

The following claims are safe only after validation:

| Claim | Current Status | Public Guidance |
|---|---|---|
| Token saving numbers | Benchmark pending | Do not publish exact numbers yet |
| Race as true parallel execution | Not supported | Describe as orchestration pattern |
| OMA as production-ready locking | Needs hardening | Describe as lock primitives + planned hardening |
| Complete AI visibility | Too strong | Use “multi-source audit trail foundation” |
| Industry-unique | Requires external proof | Avoid or weaken |
| Self-score 109.5/120 | Internal only | Do not publish as external benchmark |
| 8-dimension benchmark | Can be used with method | Add scoring methodology and limitations |

---

## 11. Recommended Positioning

### Recommended public positioning

> Carror OS is a local-first governance and workflow layer for AI coding systems.
> It helps developers keep AI coding sessions structured, bounded, auditable, and evidence-driven.

### Recommended Chinese positioning

> Carror OS 是面向 AI 编程的本地优先治理与工作流系统。
> 它不是另一个代码补全工具，而是一套帮助开发者约束、审计、编排和验证 AI 编程过程的操作层。

---

## 12. Strategic Conclusion

Carror OS is strongest when evaluated as an AI coding governance OS, not as a generic coding assistant.

Its core value is not only:

- generating code faster;

but also:

- preventing uncontrolled AI behavior;
- preserving engineering discipline;
- enforcing evidence before completion;
- managing long-running context;
- creating auditable development traces.

The next productization phase should prioritize:

1. evidence hardening;
2. benchmark validation;
3. UX simplification;
4. documentation restructuring;
5. external credibility assets.

```

---

# 文档二：十条建议改成本地模型可执行任务清单

```md
# Carror OS Product Optimization Tasks

> Version: v0.1
> Date: 2026-05-04
> Status: Internal Execution Plan
> Executor: Local LLM / Repository Agent
> Goal: Convert strategic product recommendations into concrete repository tasks

---

## Execution Rules

Before making changes, the local model must follow these rules:

1. Do not add unsupported marketing claims.
2. Do not convert planned features into implemented features.
3. Do not use exact token-saving numbers unless benchmark output exists.
4. Do not describe Race Mode as true parallel execution.
5. Do not describe OMA as production-ready until lock lifecycle hardening is verified.
6. Do not use “self-scoring” language in public-facing docs.
7. All public claims must have an evidence level.
8. Prefer small patches and clear reports.
9. After each task, output changed files and changed claims.
10. If implementation evidence is missing, mark the claim as `partial`, `planned`, or `unknown`.

---

# Task 1 — Build Claim Governance

## Priority

P0

## Goal

Create a machine-readable claim registry so that Carror OS documentation becomes evidence-driven.

## Files to Create

```text
docs/internal/claim-registry.yaml
scripts/claim-lint.sh
docs/internal/claim-lint-report.md
```

## Actions

1. Create `claim-registry.yaml`.
2. Register all high-risk claims:
   - token saving
   - context guard
   - proactive handoff
   - Race Mode
   - OMA lock
   - Error DNA
   - dehydration
   - audit trail
   - industry benchmark
3. Add fields:
   - claim_id
   - claim_text
   - status
   - evidence_level
   - public_allowed
   - source_docs
   - required_validation
   - replacement_text
4. Create `claim-lint.sh`.
5. Scan for high-risk terms:
   - 自评分
   - 行业独创
   - 100% 功能完备
   - 完全可见
   - 真并发
   - 实测节省
   - 19,280
   - 75%
   - Claude 默认 tokenizer
6. Generate `claim-lint-report.md`.

## Acceptance Criteria

- `claim-registry.yaml` exists and parses as valid YAML.
- `claim-lint.sh` reports all high-risk claims.
- No public-facing document can be considered final until claim-lint passes or exceptions are documented.

## Suggested YAML Schema

```yaml
claims:
  token_saving_19280:
    status: retracted
    evidence_level: C0
    public_allowed: false
    replacement_text: "Progressive disclosure is designed to reduce unnecessary context loading. Exact savings require benchmark validation."
    source_docs: []
    required_validation:
      - scripts/loading_benchmark.py
      - docs/testing/loading-benchmark-report.md

  race_parallel_execution:
    status: downgraded
    evidence_level: C1
    public_allowed: true
    replacement_text: "Race Mode is an orchestration pattern, not a deterministic parallel execution engine."
```

## Output Required

```text
Changed files:
Changed claims:
Remaining blockers:
Next recommended task:
```

---

# Task 2 — Run Repository Reality Check

## Priority

P0

## Goal

Verify that the knowledge base matches the real repository before further productization.

## Files to Create

```text
state/repository-reality-check.md
docs/internal/canonical-path-map.md
```

## Actions

1. Count hooks, skills, scripts, docs.
2. Detect empty implementation files.
3. Detect doc-content mismatch.
4. Identify canonical source paths for:
   - hooks
   - skills
   - scripts
   - docs
   - marketing docs
5. Check whether the following files exist:
   - `context_monitor.py`
   - `token-tracking-index.json`
   - `error-dna.sh`
   - `build-validator.sh`
   - `oma_lock_manager.py`
   - `proactive-handoff.sh`
6. Check whether any code writes to:
   - `.omc/state/token-tracking-index.json`
   - `.omc/state/error-dna.json`
   - `.omc/state/read-files.log`

## Suggested Commands

```bash
find . -type f -size 0
rg "token-tracking-index.json"
rg "context_monitor.py"
rg "error-dna"
rg "read-files.log|read-tracker.txt"
rg "19,280|75%|自评分|行业独创|完全可见|真并发"
```

## Acceptance Criteria

- `repository-reality-check.md` exists.
- All critical files are classified as:
  - exists
  - missing
  - empty
  - stale
  - unknown
- Blockers are clearly listed.

## Output Required

```text
Repository state:
Critical mismatches:
Files requiring manual review:
Blocked tasks:
Next recommended task:
```

---

# Task 3 — Repair Token and Audit Trail Foundations

## Priority

P0

## Goal

Make audit trail and proactive handoff non-silent and evidence-producing.

## Files Likely to Modify

```text
proactive-handoff.sh
read-tracker.sh
carror_dashboard.py
skill_trace_report.py
.claude/scripts/audit_dashboard.py
```

## Files to Create If Missing

```text
.omc/state/token-tracking-index.json
.claude/scripts/token_writer.py
docs/internal/audit-trail-status.md
```

## Actions

1. Verify whether token tracking has a real writer.
2. If missing, create a minimal writer or mark feature degraded.
3. Modify proactive handoff so missing token source does not silently exit.
4. Unify read tracker file naming.
5. Add log rotation for read tracker.
6. Create audit status report.

## Acceptance Criteria

- Proactive handoff produces one of:
  - active
  - triggered
  - skipped_with_reason
  - degraded
- Missing token data is visible.
- Read tracker filename is consistent.
- Rotation exists.

## Output Required

```text
Changed files:
Audit sources found:
Audit sources missing:
Behavior before:
Behavior after:
Remaining blockers:
```

---

# Task 4 — Build Feature Registry

## Priority

P0

## Goal

Create a single source of truth for all hooks and skills.

## Files to Create

```text
.claude/feature-registry.yaml
scripts/feature-probe.sh
docs/reference/feature-registry.md
```

## Files to Modify

```text
harness.yaml
harness_config.sh
features.md
```

## Actions

1. Register all hooks.
2. Register all skills.
3. Add fields:
   - feature_id
   - layer
   - edition
   - default_enabled
   - config_key
   - source_files
   - docs
   - status
   - evidence_level
   - probe
4. Add `skills_enabled:` to config if appropriate.
5. Create `feature-probe.sh`.
6. Generate human-readable feature registry doc.

## Acceptance Criteria

- Registry parses as YAML.
- Every public feature in `features.md` has a registry entry.
- Every registry entry has status:
  - implemented
  - partial
  - planned
  - broken
  - unknown
- `feature-probe.sh` can run at least three probes:
  - context_guard
  - completion_gate

## Output Required

```text
Registered features:
Missing docs:
Missing implementations:
Features downgraded:
Next recommended task:
```

---

# Task 5 — Replace Unsupported Token-Saving Claims with Benchmark

## Priority

P0

## Goal

Remove unsupported token-saving numbers and create a benchmark path.

## Files to Create

```text
scripts/loading_benchmark.py
docs/testing/loading-benchmark-report.md
```

## Files to Scan / Modify

```text
README.md
features.md
README-draft.md
PRESS-KIT.md
FAQ.md
industry-benchmark.md
CHANGELOG.md
```

## Actions

1. Search for:
   - `19,280`
   - `75%`
   - `70%`
   - `394`
   - `120`
   - `tokens/session`
2. Replace unsupported exact claims with benchmark-pending language.
3. Create benchmark script.
4. Report whether token count method is:
   - official API
   - tiktoken estimate
   - chars/4 fallback
5. Generate benchmark report.

## Acceptance Criteria

- Unsupported exact token-saving claims are removed or marked internal historical.
- Benchmark report exists.
- Any token count method is clearly labeled.
- `tiktoken` is not described as Claude’s official tokenizer.

## Replacement Text

```text
Progressive disclosure is designed to reduce unnecessary context loading. Exact token savings should be reported only after benchmark validation.
```

中文：

```text
渐进式披露的目标是减少不必要的上下文加载。具体 token 节省比例应以 benchmark 实测报告为准。
```

## Output Required

```text
Claims removed:
Claims downgraded:
Benchmark method:
Benchmark result:
Remaining unknowns:
```

---

# Task 6 — Simplify Developer Experience

## Priority

P1

## Goal

Reduce cognitive load and make Carror OS easier to understand and try.

## Files to Modify

```text
README.md
docs/overview/what-is-carror-os.md
docs/guides/quickstart.md
docs/reference/editions.md
FAQ.md
```

## Actions

1. Rewrite README to answer only:
   - What is it?
   - Why does it exist?
   - What problems does it solve?
   - What are the 3-4 core capabilities?
   - How to install?
   - How to try quickly?
   - What is the current maturity boundary?
2. Move complex theory into docs.
3. Add persona-based navigation:
   - individual developer
   - team lead
   - enterprise pilot
4. Add “Which mode should I use?” guide.
5. Reduce first-screen terminology density.

## Acceptance Criteria

- README first screen is understandable in under 60 seconds.
- Quickstart has one successful path.
- Editions are clear.
- Advanced concepts are linked, not front-loaded.

## Output Required

```text
Old README issues:
New README structure:
Concepts moved out:
Remaining confusing terms:
```

---

# Task 7 — Restructure Knowledge Base

## Priority

P1

## Goal

Turn the current document collection into a structured knowledge system.

## Files / Directories to Create

```text
docs/overview/
docs/concepts/
docs/reference/
docs/guides/
docs/governance/
docs/testing/
docs/internal/
docs/lecture/
docs/archive/
scripts/doc-sync-check.sh
docs/internal/doc-canonical-map.yaml
```

## Actions

1. Move docs into clear categories.
2. Preserve marketing docs separately.
3. Move internal scoring docs into `docs/internal/`.
4. Archive obsolete docs.
5. Add frontmatter:
   - title
   - owner
   - canonical_source
   - evidence_level
   - public_status
   - last_verified
6. Create doc sync checker.

## Acceptance Criteria

- Public docs and internal docs are separated.
- No duplicate canonical description for the same feature.
- `doc-sync-check.sh` reports broken file references.
- README links to the new structure.

## Output Required

```text
Moved files:
Archived files:
Canonical docs:
Duplicate docs found:
Broken references:
```

---

# Task 8 — Rewrite External Marketing as Evidence-Based Material

## Priority

P1

## Goal

Convert public-facing docs from internal self-scoring to reproducible methodology-based messaging.

## Files to Modify

```text
docs/marketing/industry-benchmark.md
docs/marketing/README-draft.md
docs/marketing/PRESS-KIT.md
docs/marketing/FAQ.md
docs/marketing/manifesto.md
```

## Files to Move

```text
docs/marketing/v6.1.8-dual-domain-scoring.md
→ docs/internal/v6.1.8-dual-domain-scoring.md
```

## Actions

1. Remove public self-scoring framing.
2. Remove “分析” internal commentary boxes from public docs.
3. Keep 8-dimension benchmark only if methodology is included.
4. Move 12-dimension scoring to internal.
5. Add limitations section.
6. Add links to:
   - manual acceptance test
   - auto feature test
   - loading benchmark
   - feature registry
7. Replace “industry unique” with weaker positioning.

## Acceptance Criteria

- Public docs do not contain:
  - 自评分
  - 内部分析
  - unsupported exact metrics
  - absolute superiority claims
- Industry benchmark includes method and limitations.
- Internal scoring is not mixed with public marketing.

## Output Required

```text
Marketing claims removed:
Marketing claims rewritten:
Internal docs moved:
Evidence links added:
Remaining publication blockers:
```

---

# Task 9 — Improve Observability and Agentic UI

## Priority

P1

## Goal

Make Carror OS governance visible and interactive.

## Files to Modify / Create

```text
lx-status/SKILL.md
.claude/scripts/audit_dashboard.py
completion-gate.sh
context-guard.sh
permission-gate.sh
pretool-edit-scope.sh
manual-acceptance-test.md
```

## Actions

1. Upgrade `lx-status` with:
   - token trend
   - Error DNA summary
   - Flywheel timeline
   - feature registry status
   - audit health
2. Add numbered-choice menus to:
   - completion-gate
   - context-guard
   - permission-gate
   - pretool-edit-scope
3. Add O7-O10 acceptance tests.
4. Missing data should show degraded state, not fake success.

## Acceptance Criteria

- `lx-status` shows at least 4 panels.
- All 4 hooks show numbered-choice menus.
- Acceptance tests updated.
- Missing sources are visible.

## Output Required

```text
UI surfaces changed:
Menus added:
Acceptance tests updated:
Observed degraded states:
```

---

# Task 10 — Build Evidence and Launch Asset Bank

## Priority

P1

## Goal

Prepare credible productization and launch evidence.

## Files to Create

```text
docs/internal/EVIDENCE-BANK.md
docs/internal/DOGFOODING-LOG.md
docs/marketing/screenshots-plan.md
docs/marketing/demo-video-plan.md
docs/marketing/external-review-template.md
docs/marketing/case-study-template.md
docs/internal/RISK-REGISTER.md
```

## Actions

1. Create evidence bank.
2. Record dogfooding sessions.
3. Collect:
   - terminal screenshots
   - logs
   - before/after comparisons
   - demo clips
   - benchmark tables
   - user quotes
4. Add redaction checklist:
   - repo names
   - usernames
   - secrets
   - customer data
   - internal paths
5. Create external review invitation template.
6. Create case study template.

## Acceptance Criteria

- Evidence bank contains at least 5 entries.
- Dogfooding log contains at least 3 real sessions.
- Screenshot plan exists.
- Demo plan exists.
- External review template exists.
- Risk register exists.

## Output Required

```text
Evidence entries added:
Dogfooding sessions recorded:
Public assets ready:
Assets requiring redaction:
Launch blockers:
```

---

# Execution Order

Recommended order:

```text
P0:
  Task 1 → Task 2 → Task 3 → Task 4 → Task 5

P1:
  Task 6 → Task 7 → Task 8 → Task 9 → Task 10
```

Reason:

1. Claim governance prevents new misinformation.
2. Reality check prevents editing stale or wrong files.
3. Audit/token repair fixes broken evidence sources.
4. Feature registry creates single source of truth.
5. Benchmark removes unsupported numbers.
6. UX simplification improves adoption.
7. Knowledge base restructure improves maintainability.
8. Marketing rewrite improves credibility.
9. Observability improves perceived and actual control.
10. Evidence bank supports launch and commercial conversion.

---

# Local Model Master Prompt

Use this prompt when assigning the full task chain to a local model:

```text
You are the Carror OS local productization agent.

Your goal is to improve the repository without adding unsupported claims.

Follow this execution order:

1. Build claim governance.
2. Run repository reality check.
3. Repair token and audit trail foundations.
4. Build feature registry.
5. Replace unsupported token-saving claims with benchmark.
6. Simplify developer experience.
7. Restructure knowledge base.
8. Rewrite external marketing as evidence-based material.
9. Improve observability and Agentic UI.
10. Build evidence and launch asset bank.

Rules:
- Do not claim planned features are implemented.
- Do not use exact token-saving numbers unless benchmark output exists.
- Do not describe Race Mode as true parallel execution.
- Do not describe OMA as production-ready until lock lifecycle tests pass.
- Do not use self-scoring language in public docs.
- Every public claim must have an evidence level.
- After each task, output changed files, changed claims, evidence levels, blockers, and next step.
- Prefer small, reviewable patches.
```

---

# Final Deliverables Checklist

After completing all 10 tasks, the repository should contain:

```text
docs/internal/claim-registry.yaml
docs/internal/claim-lint-report.md
state/repository-reality-check.md
docs/internal/canonical-path-map.md
.claude/feature-registry.yaml
scripts/feature-probe.sh
scripts/loading_benchmark.py
docs/testing/loading-benchmark-report.md
scripts/doc-sync-check.sh
docs/internal/EVIDENCE-BANK.md
docs/internal/DOGFOODING-LOG.md
docs/marketing/screenshots-plan.md
docs/marketing/demo-video-plan.md
docs/marketing/external-review-template.md
docs/marketing/case-study-template.md
docs/internal/RISK-REGISTER.md
```

---

# Success Criteria

This optimization round is successful when:

1. Public docs no longer contain unsupported strong claims.
2. Feature status is machine-readable.
3. Benchmark replaces historical token-saving claims.
4. Audit and token tracking no longer fail silently.
5. Knowledge base has clear public/internal separation.
6. README becomes easier to understand.
7. Marketing docs become evidence-based.
8. lx-status and hook menus make governance visible.
9. Dogfooding and launch evidence are collected.
10. Carror OS can be positioned as a credible AI coding governance system.

```

---

# 建议你怎么放进仓库

我建议直接新增两个文件：

```text
docs/internal/product-comparison-scorecard.md
docs/internal/product-optimization-tasks.md
```

然后再让本地模型执行：

```text
先不要改代码。
先把这两个文件加入知识库。
然后基于 product-optimization-tasks.md，从 Task 1 开始执行。
```

---

# 给你一个更短的本地执行指令

如果你想直接喂给本地模型，可以用这个：

```text
请新增以下两个知识库文件：

1. docs/internal/product-comparison-scorecard.md
2. docs/internal/product-optimization-tasks.md

然后不要立刻修改产品代码，先执行 product-optimization-tasks.md 中的 Task 1 和 Task 2：

- Task 1: Build Claim Governance
- Task 2: Run Repository Reality Check

执行后输出：
1. 新增/修改文件清单
2. 高风险 claim 列表
3. 当前仓库真实状态
4. 阻塞项
5. 下一步建议
```

这两份文档会把你的知识库从“观点和判断”推进到“可执行治理系统”。
