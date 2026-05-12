# External Review Invitation Template

> **Purpose**: Standardized templates for inviting external experts and security researchers to review Carror OS.
> **Status**: Active
> **Last Updated**: 2026-05-13

---

## Template Usage

This template is used to invite external experts/security researchers to review Carror OS. Customize fields in `[brackets]` before sending.

---

## Invitation Letter Template

**Subject**: Invitation to Review Carror OS — AI Native Developer Operating System

Dear [Expert Name],

We are developing Carror OS, an AI behavior governance framework (AI Native Developer Operating System) that provides physical-level security defense for AI coding assistants.

We noted your expertise in [domain/specialty] and sincerely invite you to review our project from the perspective of [security architecture / open-source governance / AI safety].

**Project Overview**:
- Positioning: AI behavior governance infrastructure (NOT an AI coding tool)
- Core capability: 32 Hooks implementing physical-level tool-call blocking (Exit 2), not prompt-level soft constraints
- License: MIT
- Repository: [URL]
- Governance version: v6.1.9

**Suggested Review Focus Areas**:

1. **Architecture Security** — Are there bypass risks in the Hook blocking mechanism? Can an AI agent circumvent Exit 2?
2. **Privacy Compliance** — Does the DLP transparent proxy meet enterprise compliance requirements for credential protection?
3. **Audit Integrity** — Are the audit logs and evidence gates verifiable and tamper-resistant across sessions?
4. [Custom focus area]

**Review Materials**:
- [Quick Start Guide](../docs/guides/quickstart.md)
- [Gate Defense System Documentation](../docs/concepts/gates.md)
- [Feature Catalog](../docs/governance/features.md)
- [Industry Benchmark Whitepaper](../docs/marketing/industry-benchmark.md)

**Timeline**: We expect to receive review feedback by [date]. Estimated review time: 2-4 hours.

Thank you for your time and professional insight.

Best regards,

[Your Name]
[Contact Information]

---

## Review Feedback Template

### Basic Information
- Reviewer: [Name / Organization]
- Review Date: [Date]
- Scope: [Selected modules]

### Findings Summary
| # | Severity | Description | Suggestion |
|---|----------|-------------|------------|
| 1 | [Critical / Major / Minor] | [Issue description] | [Fix suggestion] |
| 2 | ... | ... | ... |

### Overall Assessment

[Reviewer's overall feedback and evaluation]

---

## FAQ for Reviewers

**Q: Is Carror OS an AI coding tool like Cursor or Copilot?**
A: No. Carror OS is a governance framework that sits **between** the AI and your codebase. It intercepts tool calls at the OS level — think of it as an immune system, not another assistant.

**Q: Does Carror OS send data to any cloud service?**
A: No. Carror OS is entirely local. All hooks, scripts, and logs run on your machine. There is no telemetry, no cloud dependency, no subscription.

**Q: How is this different from Cursor Rules or Claude Code Hooks?**
A: Cursor Rules and standard hooks operate at the **prompt layer** — they ask the AI to behave. Carror OS operates at the **process layer** — it uses `Exit 2` to physically terminate disallowed tool calls. An AI cannot override an Exit 2.

**Q: Can I use Carror OS alongside Cursor / Claude Code / OpenCode?**
A: Yes. Carror OS is platform-agnostic. It injects via `AGENTS.md` and `.claude/` hooks, which are read by Claude Code, OpenCode, and any AGENTS.md-compatible IDE.

**Q: What is the license?**
A: MIT. Free to use, modify, and distribute.
