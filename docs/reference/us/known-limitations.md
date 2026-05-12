# Known Limitations

> Carror OS is built around evidence-before-done. The project applies the same principle to its own claims.
> This page documents current limitations so users can make informed decisions.

---

## Architecture

| Limitation | Impact | Status |
|-----------|--------|--------|
| Token-saving numbers are benchmark-dependent | Should not be treated as universal guarantees | ⏳ Benchmark pending (RPE-002) |
| Context monitor depends on local file tracking, not API-level token data | Token percentage is an approximation | ⏳ Being hardened (RPE-003) |
| Advanced workflows (RPE, Race) require manual invocation | Not suitable for passive users | ✅ By design — Base/Enhanced separation |

---

## Gates & Hooks

| Limitation | Impact | Status |
|-----------|--------|--------|
| Completion-gate relies on natural language trigger detection | May not catch all forms of false completion | ✅ Working — false positive preferred over miss |
| Context-guard 50% proactive handoff requires step completion detection | May not fire in all session patterns | ⏳ Being hardened (RPE-003) |
| Privacy-gate uses keyword + pattern matching for DLP | May not catch obfuscated or encoded secrets | ✅ By design — pattern set is extensible |
| Permission-gate uses regex pattern scanning | Non-standard destructive commands may not match default rules | ✅ By design — rules configurable in harness.yaml |

---

## Audit & Observability

| Limitation | Impact | Status |
|-----------|--------|--------|
| Audit trail is multi-source; some sources may show degraded status if unavailable | Dashboard may display partial data | ✅ Degraded-aware by design |
| Read-files log grows unbounded | Long sessions may produce large log files | ⏳ Rotation pending (RPE-003) |
| No graphical web dashboard | Audit review is CLI-only via lx-status | ✅ By design — CLI-native |

---

## Advanced Features

| Limitation | Impact | Status |
|-----------|--------|--------|
| Race Mode is an orchestration pattern, not deterministic parallel execution | Does not guarantee concurrent task completion | ✅ Documented as design choice |
| OMA lock lifecycle hardening is ongoing | Complex multi-step coordination may encounter stale locks | ⏳ Being hardened (RPE-014) |
| Error DNA cross-session memory depends on local JSONL files | No cloud sync or team-shared error database | ✅ By design — local-first |

---

## Platform Support

| Limitation | Impact | Status |
|-----------|--------|--------|
| Primary platform: Claude Code | Other CLI tools (Codex CLI, Gemini CLI) may have incomplete hook support | ✅ Documented as Claude Code first |
| Windows: WSL only | Native Windows shell support not available | ✅ By design |
| Performance: hook scripts add ~10-50ms per tool call | Negligible for most operations; may be noticeable during rapid tool sequences | ✅ Acceptable trade-off |

---

## Why We Publish Limitations

1. **Evidence-before-done** — We apply the same standard to Carror OS itself
2. **Trust** — Transparent limitations build more trust than over-promising
3. **Clarity** — Helps users decide if Carror OS fits their workflow
4. **Focus** — Limitations guide our development priorities

---

## How to Address a Limitation

- **Check current status**: Reviewed each RPE cycle; update this page with progress
- **File an issue**: If a limitation blocks your workflow, let us know
- **Contribute**: Carror OS is open source — PRs that resolve limitations are welcome
- **Workaround**: Most limitations have a documented workaround in the relevant feature doc

---

*Last updated: 2026-05-04 | This page is updated as features mature.*
