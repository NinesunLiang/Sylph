[ARCHIVED v6.2.1 — Historical record. Referenced scripts/hooks may no longer exist.]

     1|# Evidence Bank
     2|
     3|> **Purpose**: Central repository for all product evidence — screenshots, logs, benchmark data, dogfooding results, and external validation.
     4|> **Status**: Active
     5|> **Last Updated**: 2026-05-09
     6|
     7|---
     8|
     9|## Guidelines
    10|
    11|1. Each evidence entry must include capture date, context, and file path.
    12|2. Screenshots should be placed in `docs/internal/assets/` or linked to external hosting.
    13|3. Redact sensitive information (repo names, usernames, secrets, internal paths) before storing.
    14|4. Tag each entry with evidence level (L1-L4 per AGENTS.md for internal gates, or C1-C5 for external audience).
    15|
    16|---
    17|
    18|## Evidence Entries
    19|
    20|| # | Type | Date | Description | Evidence Level | File/Link | Status |
    21||---|------|------|-------------|---------------|-----------|--------|
    22|| 1 | Document | 2026-05-09 | Hermes 三维度质量审计报告 rev2 — 综合评分 72/100 | L3 | `docs/internal/audit-v6.1.8-rev2.md` | ✅ |
    23|| 2 | Document | 2026-05-07 | 架构审查报告 — 诚实评分 ~81/100 | L3 | `docs/technical/architecture-review.md` | ✅ |
    24|| 3 | Document | 2026-05-09 | Oracle 仲裁提交 — Hermes 4 争议点及双方立场 | L3 | `.omc/state/oracle-submission-hermes.md` | ✅ |
    25|| 4 | Document | 2026-05-04 | 手动验收测试报告 — 66 项验收测试 | L3 | `docs/tests/manual-acceptance-test.md` | ✅ |
    26|| 5 | Script | 2026-05-09 | Harness Smoke Test 脚本 — 66 项回归测试 | L3 | `.claude/scripts/harness-smoke-test.sh` | ✅ |
    27|| 6 | Hook | 2026-05-09 | Completion Gate 证据门禁 — 阻断无证据完成声明 | L3 | `.claude/hooks/completion-gate.sh` | ✅ |
    28|| 7 | Hook | 2026-05-09 | Context Guard 上下文守卫 — >90% 阻断写操作 | L3 | `.claude/hooks/context-guard.sh` | ✅ |
    29|
    30|---
    31|
    32|## Asset Types
    33|
    34|- **Screenshots**: gate triggers, lx-status panels, audit logs, installation flow
    35|- **Logs**: terminal output, error-dna records, flywheel events
    36|- **Benchmark**: loading benchmark reports, token comparison tables
    37|- **Dogfooding**: real task completion records with before/after
    38|- **Test Results**: acceptance test reports, manual test logs
    39|- **External**: user feedback, review quotes, community responses
    40|
    41|---
    42|
    43|## Redaction Checklist
    44|
    45|Before publishing any evidence asset, check:
    46|- [ ] Repo names removed or anonymized
    47|- [ ] Usernames removed
    48|- [ ] Secrets / tokens / keys removed
    49|- [ ] Customer or client data absent
    50|- [ ] Internal file paths removed
    51|- [ ] No sensitive IP or proprietary code visible
    52|