# Evidence Bank

> **Purpose**: Central repository for all product evidence — screenshots, logs, benchmark data, dogfooding results, and external validation.
> **Status**: Active
> **Last Updated**: 2026-05-04

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
|   |      |      |             |               |           |        |

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
