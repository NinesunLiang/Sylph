# Hook Configuration Guide

> Source-extracted from `.claude/hooks/` (37 scripts) + `.claude/harness.yaml` + `.claude/settings.json`.

## What Are Hooks?

Hooks are Carror OS's gate mechanism. Each hook triggers a script at a specific moment (before/after tool calls, on session stop, etc.) to inspect or constrain AI behavior.

**Analogy**: Git hooks (pre-commit / pre-push), but for AI tool calls.

## Hook Lifecycle

```
Event fires (e.g., AI prepares to Edit a file)
  → settings.json matches tool name + event type
    → Script executes
      → exit 0 (allow) or echo '{"continue": true}' + exit 2 (block + message)
```

## Configuration Files

| File | Purpose |
|------|---------|
| `.claude/harness.yaml` | Toggle switches (`hooks_enabled`) + threshold config |
| `.claude/settings.json` | Event registration (`hooks` array: event name, matcher, timeout) |
| `.claude/hooks/*.sh` | Actual script logic |

**All three must align**: disk script exists ↔ `settings.json` registered ↔ `harness.yaml` enabled `true`. Any missing piece = hook won't fire.

Verification command:
```bash
bash .claude/scripts/audit-hooks.sh
```

## hooks_enabled Reference

Every switch in `harness.yaml`'s `hooks_enabled`:

| Switch | Default | Purpose |
|--------|---------|---------|
| `completion_gate` | true | Requires evidence file before marking tasks complete |
| `context_guard` | true | Blocks write operations when context exceeds 90% |
| `subagent_guard` | true | Caps sub-agent usage to prevent billing surprises |
| `pretool_edit_scope` | true | Edit scope checking + auto-include related files |
| `edit_guard` | true | Enforces Read-before-Edit on source files |
| `lsp_suggest` | true | Suggests LSP tools when Grep-searching exported symbols |
| `posttool_read_cite` | false | Prompts citation format after reads |
| `posttool_bash_audit` | true | Audits permission context after Bash execution |
| `posttool_write_cite` | true | Validates lesson format when writing to claude-next.md |
| `permission_gate` | true | Checks permission format before dangerous commands |
| `auto_snapshot` | true | Saves session state snapshot on stop |
| `posttool_edit_quality` | true | Post-edit style/doc-sync self-check |
| `inject_project_knowledge` | true | Injects core knowledge into AI context |
| `plan_gate` | false | Checks for skipped planning before edits |
| `turn_counter` | true | Turn counting + fuzzy instruction detection |
| `read_tracker` | true | Tracks read files for edit-guard |
| `error_dna` | true | Error DNA capture + cross-session memory |
| `knowledge_condenser` | true | Auto-suggests sublimation for high-frequency lessons |
| `posttool_claim_audit` | true | Rule #1 enforcement — no fabricated code facts |
| `intent_tracker` | true | Tracks edit count + detects content reversion |
| `posttool_handoff_writer` | true | Writes handoff notes after each Task completion |
| `posttool_output_format` | true | Checks output format usability |
| `pretool_sensitive_edit` | true | CAPTCHA confirmation for governance file edits |
| `skill_flywheel` | true | Skill usage frequency tracking |
| `build_validator` | false | Deprecated (zero ROI) |
| `user_correction_detector` | true | Detects user correction signals, enforces recording |
| `rule_anchor` | true | Injects anchor rules at high turn counts |
| `proactive_handoff` | false | Proactive session handoff prompts |
| `ecosystem_probe` | true | Detects runtime platform and OMO installation status |

## Common Configuration Scenarios

### Disable a Gate

Edit `.claude/harness.yaml`, in `hooks_enabled`:
```yaml
hooks_enabled:
  completion_gate: false
```

### Adjust Context Guard Threshold

In `harness.yaml`:
```yaml
context_guard:
  max_percent: 85  # Default 90, lower = more conservative
```

### Add Custom Dangerous Command Patterns

In `harness.yaml` `bash_audit.dangerous_patterns`:
```yaml
bash_audit:
  dangerous_patterns: "git commit git push ... your_pattern"
```

### Customize Permission Gate Scope

```yaml
permission_gate:
  gh_write_regex: 'gh\s+(release|pr|issue|repo|secret)'
```

## What to Do When Blocked by a Gate

### completion-gate

```
⛔ COMPLETION BLOCKED — No verification evidence
```

**Action**: Run verification, write output to evidence file. AI handles the rest.

### permission-gate

```
🚫 PERMISSION REQUIRED — Dangerous command needs approval
```

**Action**: Type `! <command>` in the input box, or explicitly express approval.

### context-guard

```
⚠️ CONTEXT THRESHOLD — 90%+ context usage
```

**Action**: Use `/compact` to compress context, or close unnecessary conversation history.

### sensitive-edit (CAPTCHA)

```
🔒 SENSITIVE FILE EDIT — Governance file needs confirmation
```

**Action**: Follow the prompt to enter the confirmation command in the input box. This prevents AI from modifying governance files without authorization.

---

## Hook Event Types

| Event | When | Available Tool Matchers |
|-------|------|------------------------|
| `PreToolUse` | Before tool call | All tool names (Bash/Edit/Write/Read/Grep/Task, etc.) |
| `PostToolUse` | After successful tool call | Same as above |
| `PostToolUseFailure` | After failed tool call | Same as above |
| `Stop` | On session stop | — |
| `SessionStart` | On new session start | — |
| `PreCompact` | Before /compact | — |
| `Notification` | System notification | — |

---

## Troubleshooting

```bash
# Check three-way alignment
bash .claude/scripts/audit-hooks.sh

# Run full smoke tests
bash .claude/scripts/harness-smoke-test.sh

# Run hook production verification
bash .claude/scripts/hook-production-verify.sh
```
