# Carror OS Model Routing Strategy

> Version: v1 | 2026-05-10
> Description: Three-tier model (haiku/sonnet/opus) allocation strategy and current skill mapping table

---

## Three-Tier Model Capability Matrix

| Tier | Capability | Use Case | Cost-Effectiveness |
|------|-----------|----------|-------------------|
| **haiku** | Lightweight fast | Status panel, simple validation, deterministic scripts | Low cost, high throughput |
| **sonnet** | Standard development | Coding, review, testing, security analysis, RCA | Default choice |
| **opus** | Complex architecture | Architecture decisions, cross-system analysis, security policy design | On-demand |

---

## Current Skill Model Allocation

### model: haiku (Lightweight Skills)
| Skill | Lines | Complexity | Reason |
|-------|-------|-----------|--------|
| lx-status | 64 | beginner | Panel aggregation, reads state files + formats output |
| lx-validate-skill | -- | beginner | 11 deterministic compliance checks |

### model: sonnet (Standard Skills -- Default Tier)
| Skill | Lines | Complexity | Reason |
|-------|-------|-----------|--------|
| lx-browser-verify | -- | intermediate | Browser end-to-end verification |
| lx-code-review | -- | intermediate | Code review, standard analysis |
| lx-debug-spec | -- | intermediate | Debug workflow guidance |
| lx-golang-test | -- | intermediate | Go test execution |
| lx-oma-gov | -- | intermediate | PRD governance |
| lx-oma-hier | -- | intermediate | Hierarchical decomposition |
| lx-oma-orch | -- | intermediate | Pipeline orchestration |
| lx-oma-split | -- | intermediate | OMA decomposition |
| lx-prd | -- | intermediate | PRD management |
| lx-pre-commit | -- | intermediate | Pre-commit gate |
| lx-pre-push | -- | intermediate | Pre-push gate |
| lx-race | -- | intermediate | Race condition detection |
| lx-react-review | -- | intermediate | React review |
| lx-root-cause-analysis | 212 | intermediate | Root cause analysis, standard RCA |
| lx-rpe | 212 | intermediate | 9-step closed loop (refactored and simplified) |
| lx-security-review | -- | intermediate | Security review |
| lx-task-spec | -- | intermediate | Structured tasks |
| lx-tdd-spec | -- | intermediate | TDD workflow |
| lx-todo | -- | intermediate | Todo management |
| lx-web-perf | -- | intermediate | Web performance analysis |

---

## Model Selection Principles

1. **Default sonnet**: Unless there is a clear reason, all skills default to `model: sonnet`
2. **Downgrade to haiku conditions**:
   - Lines < 80
   - Complexity = beginner
   - No architecture decision / security analysis requirements
3. **Upgrade to opus conditions** (currently no skill qualifies):
   - Involves cross-system architecture decisions
   - Security policy / encryption protocol design
   - Deep refactoring analysis of multi-person team code

---

## Usage in SKILL.md

Each SKILL.md declares in YAML frontmatter:

```yaml
---
name: lx-example
model: sonnet  # haiku | sonnet | opus
complexity: intermediate  # beginner | intermediate | advanced
---
```

CLI tools or the orchestrator should read the `model:` field when invoking skills and pass it to the underlying model router.
