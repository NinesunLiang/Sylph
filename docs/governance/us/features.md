# Carror OS — Full Feature Reference (v6.1.9 Cross-Platform Edition)

> **Version**: v6.1.9 | **Updated**: 2026-05-13
> **Philosophy**: Guard First, Arm Later.
> Carror OS ships in two editions — Base and Enhanced — load what you need.

---

## Base Edition: Silent Guardian, Zero Learning Cost

**For**: Developers who want AI to behave without learning new commands.
**Install**: `bash install.sh base`
**Includes**: Harness-kit (32 Hooks) + 10 gate Skills.

| Capability | Role | Trigger |
|:-----------|:-----|:--------|
| **Defense Net (Hooks)** | Physical blocking of AI hallucinations, destructive commands (`rm -rf`), privacy leaks, long-context degradation | **Silent intercept** (anytime) |
| `lx-pre-commit` | Pre-commit quality gate: type checking, incremental build, tests, code review | `/lx-pre-commit` or Git Hook |
| `lx-pre-push` | Pre-push security & compliance gate, `ANK-1.5.6.16` commit format validation | `/lx-pre-push` |
| `lx-code-review` | Language-agnostic code review with auto-fix | Auto-triggered / manual |
| `lx-style-guide` | Style convention review | Auto-triggered / manual |
| `lx-validate-skill` | Skill acceptance review: frontmatter, atomization declarations, 11-rule node reference check | Manual |

---

## Enhanced Edition: Advanced Arsenal

**For**: Engineers tackling complex refactoring, large features, deep debugging — one-person army mode.
**Install**: `bash install.sh enhanced`
**Includes**: All Base capabilities + 14 active workflow Skills below.

### 1. Task Driver Engines

* **/lx-rpe**: Large feature pipeline. Research → Plan → Execute with 50% sweet-spot context handoff and A→B→A adversarial verification.
* **/lx-task-spec**: Medium complexity tasks. Precise AC-driven, no verbose PRD required.
* **/lx-todo**: Small tasks. ≤3 file quick loop (5 steps), auto-escalation when exceeded.
* **/lx-oma**: One-person army HQ. Decomposes requirements into orthogonal feature branches. Supports directory/file input.
* **/lx-race**: Swarm coordination. Register subtasks → dispatch → collect → report. Reuses OMA Lock concurrency engine.

### 2. Advanced Diagnostics & Generation

* **/lx-root-cause-analysis**: 5-Why root cause tracing.
* **/lx-perf-analysis**: Go performance analysis — CPU/memory profiling, goroutine leak detection, benchmark analysis.

### 3. Specialized Operations & Monitoring

* **/lx-status**: Health dashboard — token savings, error self-healing rate, task execution trace.
* **/lx-varlock**: Enterprise DLP privacy proxy. AI uses masked placeholders for credentials; bidirectional transparent obfuscation prevents leaks. Usage: `varlock.py set KEY val` → `varlock.py read .env`

---

## Switching Between Editions

Upgrade or downgrade freely:

```bash
# Upgrade to full Enhanced
bash install.sh enhanced

# Roll back to Base
bash install.sh base
```

---

## Post-Install Verification

### Semi-Automated (Recommended for new members, daily regression)

| File | Description |
|:-----|:------------|
| **`../tests/cn/auto-feature-test.md`** | Test execution guide. Tell AI "run Zone 1 tests" — no manual commands needed. Covers Agentic UI gates, dashboard observability, OMA engine. |
| **`../tests/cn/auto-feature-test-log.md`** | Test log template. Record real-time results, sign off. |

### Full Manual (Formal delivery, security audit, Zero Trust)

| File | Description |
|:-----|:------------|
| **`../tests/cn/manual-acceptance-test.md`** | 49-item manual checklist covering all 32 Hooks and core Skills. Every command executed by you, every result verified by your eyes. |
| **`../tests/cn/manual-acceptance-test-log.md`** | 49-row blank log. Fail entries must include root cause and fix plan. Signed by acceptance officer. |

> For formal delivery, use the full manual process. AI summaries are not evidence — your hands-on execution and signature are.
