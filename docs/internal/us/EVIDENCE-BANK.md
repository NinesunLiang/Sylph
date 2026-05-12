# Evidence Bank

> **Purpose**: Central repository for all product evidence — screenshots, logs, benchmark data, dogfooding results, and external validation.
> **Status**: Active
> **Last Updated**: 2026-05-09

---

## Guidelines

1. Each evidence entry must include capture date, context, and file path.
2. Screenshots should be placed in `docs/internal/assets/` or linked to external hosting.
3. Redact sensitive information (repo names, usernames, secrets, internal paths) before storing.
4. Tag each entry with evidence level (L1-L4 per AGENTS.md for internal gates, or C1-C5 for external audience).

---

## Evidence Entries

| # | Type | Date | Description | Evidence Level | File/Link | Status |
|---|------|------|-------------|---------------|-----------|--------|
| 1 | Document | 2026-05-09 | Hermes 三维度质量审计报告 rev2 — 综合评分 72/100 | L3 | `docs/internal/audit-v6.1.8-rev2.md` | ✅ |
| 2 | Document | 2026-05-07 | 架构审查报告 — 诚实评分 ~81/100 | L3 | `docs/technical/architecture-review.md` | ✅ |
| 3 | Document | 2026-05-09 | Oracle 仲裁提交 — Hermes 4 争议点及双方立场 | L3 | `.omc/state/oracle-submission-hermes.md` | ✅ |
| 4 | Document | 2026-05-04 | 手动验收测试报告 — 66 项验收测试 | L3 | `docs/tests/manual-acceptance-test.md` | ✅ |
| 5 | Script | 2026-05-09 | Harness Smoke Test 脚本 — 66 项回归测试 | L3 | `.claude/scripts/harness-smoke-test.sh` | ✅ |
| 6 | Hook | 2026-05-09 | Completion Gate 证据门禁 — 阻断无证据完成声明 | L3 | `.claude/hooks/completion-gate.sh` | ✅ |
| 7 | Hook | 2026-05-09 | Context Guard 上下文守卫 — >90% 阻断写操作 | L3 | `.claude/hooks/context-guard.sh` | ✅ |

---

## Asset Types

- **Screenshots**: gate triggers, lx-status panels, audit logs, installation flow
- **Logs**: terminal output, error-dna records, flywheel events
- **Benchmark**: loading benchmark reports, token comparison tables
- **Dogfooding**: real task completion records with before/after
- **Test Results**: acceptance test reports, manual test logs
- **External**: user feedback, review quotes, community responses

---

## Redaction Checklist

Before publishing any evidence asset, check:
- [ ] Repo names removed or anonymized
- [ ] Usernames removed
- [ ] Secrets / tokens / keys removed
- [ ] Customer or client data absent
- [ ] Internal file paths removed
- [ ] No sensitive IP or proprietary code visible
