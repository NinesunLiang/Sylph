# Skill Atomization Architecture Guide

> **Carror OS — AI Native Developer Operating System**
>
> Version: v6.1.9 | Last Updated: 2026-05-13

---

## Overview

This guide defines the Skill atomization architecture specification in the lx-skills-v5 system. All Skills must follow this architectural layering to ensure reusability, maintainability, and cross-Skill consistency.

---

## 1. Three-Layer Architecture Specification

Each Skill follows a strict **three-layer directory structure**:

```
skills/lx-{name}/
├── SKILL.md         ← Layer 1: AI judgment layer (required)
├── scripts/         ← Layer 2: Deterministic execution layer (create when logic is fixed)
│   └── xxx.py       ← Pure Python, exit code, JSON output
└── references/      ← Layer 3: On-demand knowledge layer (create when large structured knowledge exists)
    └── xxx.md       ← Load timing hard-coded in SKILL.md
```

### Layer 1: AI Judgment Layer (SKILL.md)

- Contains `name` / `description` / `when_to_use` and other metadata
- Declares the common nodes, reference schemas, and state machine types used by this Skill
- Writes executable Step flows, prioritizing readability for each Step
- Requires AI semantic understanding to execute → stays in SKILL.md

### Layer 2: Deterministic Execution Layer (scripts/)

- Steps are fixed, no AI judgment needed → placed in scripts/
- Pure Python implementation, no Node.js/Go or other runtime dependencies
- Follows stdin JSON / stdout JSON / exit code 2 protocol
- Exit code `0` = normal pass, `2` = block/failure, `1` = system error

### Layer 3: On-Demand Knowledge Layer (references/)

- Large structured knowledge (>30 lines), loaded by phase → references/
- Explicitly controlled loading timing by SKILL.md, not auto-injected

---

## 2. Common Node System

Skills assemble workflows by reusing common nodes under `.claude/nodes/`, avoiding duplicate implementation of the same logic.

### Current Common Nodes

| Node | Purpose |
|------|---------|
| `target_resolver.md` | Parse scan/review targets from arguments/git diff |
| `context_collector.md` | Collect project framework/version/convention context |
| `scanner.md` | Execute scanning by rule set |
| `auto_fixer.md` | Auto-fix P0/P1 issues |
| `verifier.md` | Re-scan verification after fixes |
| `gate_checker.md` | Gate determination |
| `report_generator.md` | Report generation |
| `behavior_rules.md` | Behavior constraint rules |
| `interactive_prompt.md` | Guided Q&A |
| `orchestrator.md` | Multi-step orchestration |
| `execute_node.md` | Step execution node |
| `generator.md` | Content generation node |
| `a_terminal.md` | A terminal (acceptance criteria generation) |
| `b_terminal.md` | B terminal (acceptance execution) |

### Reference Path Specification

Referencing from `skills/lx-{name}/SKILL.md`:
- Common nodes: `../../nodes/{node_name}.md`
- Common schemas: `../../schemas/atomic/{schema_name}.yaml`
- task_sys components: `../../task_sys/{component}.md`

---

## 3. Schema System

`schemas/` is organized into four categories:

| Directory | Purpose |
|-----------|---------|
| `atomic/` | Atomic schemas reused by 3+ Skills |
| `contract/` | State machine contracts (reference documents, not mandatory) |
| `input/` | Task-driven input schemas |
| `output/` | Output format registry |

### Atomic Schema Inventory

| Schema | Description |
|--------|-------------|
| `scan_target.yaml` | Scan/review/verify target definition |
| `severity.yaml` | Issue severity classification (P0-P3) |
| `finding.yaml` | Individual issue/finding |
| `scan_report.yaml` | Scan/review/verify report |
| `fix_record.yaml` | Fix record |
| `gate_result.yaml` | Gate determination result |
| `context_summary.yaml` | Context collection summary |
| `verdict.yaml` | Final verdict (common to all Skills) |

---

## 4. State Machine Types

Skills should declare their state machine type and specify whether they reference `orchestrator.md`:

| Type | Description | Example |
|------|-------------|---------|
| **scan→fix→re-scan loop** | Review-type Skills | lx-code-review, lx-security-review |
| **analyze→generate→verify flow** | Generation-type Skills | lx-tdd-spec, lx-rpe |
| **Gate type** | Gate chain | lx-pre-commit, lx-pre-push |
| **Custom X-phase** | Does not reference orchestrator.md | Must explain why |

---

## 5. Atomization Principles

### 1. Single Responsibility

Each Skill does one thing and does it well. If a SKILL.md contains multiple unrelated domain logics, it should be split into multiple Skills.

### 2. Node Reuse Priority

Identical logic found in two Skills → extract as a common node into `.claude/nodes/` instead of repeating in two SKILL.md files.

### 3. Node Independence

Each node can be loaded independently without relying on execution order. Node inputs and outputs are defined through explicitly declared Schema contracts.

### 4. Zero-Consumer Cleanup

Schemas/nodes marked as zero-consumer in `registry.yaml` should be deleted to keep the system lean.

### 5. Reference Paths

All cross-SKILL.md references use relative paths, ensuring resolvability after file moves:
- Skill → nodes: `../../nodes/{name}.md`
- Skill → schemas: `../../schemas/{category}/{name}.yaml`
- Skill → task_sys: `../../task_sys/{name}.md`

---

## 6. Skill Metadata Specification

Each SKILL.md must include the following metadata (YAML frontmatter):

```yaml
---
name: lx-{name}
version: v{version}
description: "{one-sentence description of skill scope}"
when_to_use: "{trigger scenario description}"
model: {sonnet|opus|haiku}
argument-hint: "[argument hint]"
paths:
  - "*.{ext}"
harness_version: ">=1.1.0"
---
```

---

## 7. Creating a New Skill

1. Copy `.claude/skills/TEMPLATE.md` to `skills/lx-{name}/SKILL.md`
2. Replace all `{name}`, `{description}` and other placeholders
3. Declare the common nodes used (select from the existing 14 nodes)
4. Declare the referenced schemas (select from `schemas/registry.yaml`)
5. Write the Skill's private rules/check sets
6. If there is fixed logic → create `scripts/xxx.py` as needed
7. If there is large structured knowledge → create `references/xxx.md` as needed
8. Declare boundaries (what it does NOT do), explicitly stating scope limits
9. Register this Skill as a Schema consumer in `schemas/registry.yaml`

---

## 8. Node Creation/Upgrade Principles

- When extracting common nodes, simultaneously update the consumer list in `schemas/registry.yaml`
- New nodes require updating the "Common Nodes" inventory in this file
- Node interface changes must synchronously update all consumer SKILL.md files
- Node destruction requires confirmation of zero consumers
