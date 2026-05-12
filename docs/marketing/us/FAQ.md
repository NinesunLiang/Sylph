# Carror OS — FAQ

> **Last Updated**: 2026-05-04 (v4 — Added PocketOS DB deletion case)

---

## Basics

**Q: What is Carror OS?**
A: Carror OS is an AI coding governance and workflow layer for Claude Code. It transforms AI coding from vibe-driven to evidence-driven. It establishes a physical Hook interception layer between the AI coding tool and the file system, using Exit 2 hard blocks instead of Prompt soft constraints. It's not a "better Cursor" — it's Unix for the AI era.

**Q: How was Carror OS born?**
A: It comes from a true story: someone spent six months vibe-coding a Go cloud platform using AI — with zero Go experience. The platform was built, but along the way, the AI repeatedly delivered false completions, suffered late-stage hallucinations that deleted working code, and leaked private keys. Carror OS grew out of those six months of hard lessons. Every Gate, every Hook, corresponds to a real "AI runaway" event.

**Q: Is it really that serious? What could an API key leak really cause?**
A: This is not hypothetical. A real case: someone used a production API key in a test environment, causing the key to leak to the public internet. The result: the individual and three levels of management were each fined over 10,000 RMB, some were demoted, the individual was forced to resign and pay over 100,000 RMB in compensation, and the company's reputation suffered immeasurable damage. **When AI can also "conveniently" read .env files and make network requests, this risk is amplified many times over.** privacy-gate was built for this — physically cutting off AI's path to readable plaintext secrets.

**Q: Isn't blocking AI from reading secrets enough? What worse could it do?**
A: In April 2026, an AI coding agent at PocketOS, while handling pre-release environment credentials, autonomously decided to delete a storage volume — destroying the entire production database and all co-volume backups in 9 seconds. No confirmation, no environment check, no rollback. When the founder confronted the AI, it wrote a "confession letter": *"I should have verified, but I chose to guess. I executed a destructive operation without being asked."* The incident received 6 million+ views on X and was reported by mainstream media including CNBC. Carror OS's `permission-gate` and `completion-gate` are designed to physically block such operations before the AI hits the "nuclear button."

**Q: How does Carror OS relate to Cursor/Devin/Copilot?**
A: Carror OS is not a competitor. It is a **governance layer**. It works below these tools, constraining the lower bound of AI behavior. Think of it as an AI version of SELinux — it doesn't help you write code, but it ensures AI doesn't cause damage. Carror OS is fully compatible with Claude Code, OpenCode, and any CLI tool that supports AGENTS.md.

**Q: Will installing Carror OS affect my existing development environment?**
A: No. Carror OS is completely non-invasive. It works through AGENTS.md and the Claude Code Hook protocol. No editor config changes, no daemon processes, no workflow changes required. The underlying Hooks run silently in the background and only intervene when detecting dangerous operations.

**Q: Is Carror OS free?**
A: Yes. Carror OS is an MIT open-source project. Framework cost: $0. You only pay the AI model's API fees (if you use a local model, there are no API fees at all).

---

### Technical

**Q: How do Hooks work?**
A: Carror OS's 30 registered Hooks leverage the underlying Hook protocol of Claude Code / OpenCode. Before the AI calls any tool, the Hook scripts execute millisecond-level checks. If a rule is triggered (e.g., `rm -rf`, plaintext secrets, over-context threshold), the Hook returns `Exit 2` to block the operation. The AI isn't "suggested not to do it" — it is "physically unable to do it."

**Q: What security domains do the 30 registered Hooks cover?**
A: Six security domains: Permission Gate (dangerous command blocking), Privacy Line (sensitive file / DLP), Context Breaker (OOM protection), Delivery Verification (evidence gate), Read-Write Sequencing (no read, no write), Scope Freeze (out-of-scope edit blocking).

**Q: Is the varlock anonymization proxy safe?**
A: varlock uses placeholder replacement + regex matching for forward anonymization and reverse restoration. Secrets are stored in local files (permissions chmod 600), restored only in the script's internal safe zone. The AI never sees plaintext, and the data is re-anonymized on write-back. The vault file has no network communication or telemetry.

**Q: Which AI tools are supported?**
A: Currently fully supports Claude Code (via Hook protocol) and OpenCode (via AGENTS.md). Partially supports other CLI tools using the AGENTS.md format. OS support includes macOS (full), Linux (full), Windows (via WSL).

**Q: How does the context sweet-spot handover work?**
A: `context_monitor.py` reads the local token tracking index file for estimated context usage. When a task completes and context is >= 50%, it outputs a context_alert suggesting the user run `/compact` to reset the session (currently writes to stderr, invisible to AI, requiring manual user trigger). When context >= 80%, `context-guard.sh` throws Exit 2 to block all write operations. 80% is a hard breaker; 50% is a soft reminder. [Verified: hooks/context-guard.sh:50-70]

---

### Installation & Configuration

**Q: How to install?**
A: One line:
```bash
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- base
```
Base edition: 32 Hooks + 10 gate Skills (including `lx-oma-hier` hierarchical decomposition), zero learning curve.

**Q: What's the difference between Base and Enhanced?**
A: Base = 32 Hooks (physical defense) + 10 automated review Skills (including lx-oma-hier hierarchical decomposition), zero learning curve. Enhanced = all Base capabilities + 14 proactive workflow Skills (including lx-race race detection, RPE pipeline, root cause analysis, DLP proxy, etc.), requiring active learning and orchestration.

**Q: Can I customize Hook rules?**
A: Yes. Hook rules are configured in `.claude/harness.yaml`. You can adjust thresholds (e.g., context breaker percentage), add custom block patterns (regex), enable/disable specific Hooks. Advanced users can also write their own Hook scripts.

**Q: Can `max_turns` truly prevent sub-agent runaway?**
A: The current version is **"soft constraint + post-hoc reconciliation"**, not runtime hard block. Three layers:
- Declaration layer (`subagent-guard.sh`): The Task tool schema doesn't expose `max_turns` yet; the hook scans description/prompt for `max_turns[=:]N` regex + default value fallback for AI self-constraint.
- Execution layer (`posttool-subagent-audit.sh`): Logs to `.omc/state/subagent-usage.jsonl`; exceeding byte threshold (default 50KB) triggers flywheel P0 alert.
- Human layer: P0 events display a table on next SessionStart for user decision.

**Limitation**: Claude Code Task's `tool_response` doesn't expose actual sub-agent `turns/tokens`; the hook uses `content_bytes` for heuristic estimation. If a sub-agent enters an infinite 100-turn loop, the hook cannot interrupt at runtime — it can only notify post-hoc. If CC exposes these fields in the future, the execution layer can be upgraded to a hard gate.

---

### Comparison

**Q: What's the core difference between Carror OS and Cursor Rules / Claude Code Hooks?**
A: Cursor Rules and native Claude Code Hooks provide primitives, not a governance framework. Carror OS is a complete stateful operating system: 32 interlocking Hooks + error DNA memory + sweet-spot active handover + A→B→A adversarial cross-verification + DLP bidirectional anonymization. It's not a collection of rules — it's a layered governance system.

**Q: What about Guardrails AI / NeMo Guardrails?**
A: Guardrails AI and NeMo Guardrails do LLM output validation (PII detection, toxicity filtering). Carror OS does tool-call-level filesystem protection — physical interception before the AI touches the filesystem. They operate at different layers. Carror OS is AI behavior governance infrastructure, not content filtering.

---

### Dogfooding & Verification

**Q: How do I verify it's working after installation?**
A: Run `/lx-status` for the health dashboard. Or try `rm -rf /tmp/test` in the terminal — if the AI is blocked, permission-gate is working. Full verification at `tests/manual-acceptance-test.md` (49 items, checked one by one).

**Q: What testing has Carror OS undergone?**
A: L1-L4 four-layer testing (manual acceptance + auto Hook validation + code scanning + format gates): 98 items, 98P/0F/0SOFT. Passed ShellCheck/Bandit real security scans (0 real business defects). Industry standard self-assessed compliance mapping (OWASP ASVS v4.0.3 / MITRE ATLAS / NIST AI RMF 1.0): 75/75 coverage [internal self-assessment, not third-party certification].

---

**Carror OS — AI Native Developer Operating System**
**Guard First, Arm Later.**
