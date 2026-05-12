# OpenCode Hooks Migration Plan: Achieving Claude Code-Level Hook Capabilities via OMO

> Date: 2026-05-13 | Status: Draft | Goal: Carror OS obtains hook governance capabilities on OpenCode equivalent to Claude Code

---

## 1. Core Conclusion

**oh-my-openagent (OMO) already has a Claude Code hooks compatibility layer**, located at `src/hooks/claude-code-hooks/`, which can map Claude Code's `.claude/settings.json` hook configuration to OpenCode's Plugin hook points.

**Existing Compatibility Layer Capability Matrix:**

| Claude Code Event | OMO Compatibility Layer | Status |
|---|---|---|
| PreToolUse | `tool.execute.before` | Implemented |
| PostToolUse | `tool.execute.after` | Implemented |
| UserPromptSubmit | `chat.message` | Implemented |
| Stop | `event.session.idle` | Implemented (with `stopHookActive` reactivation mechanism) |
| PreCompact | `experimental.session.compacting` | Implemented |
| SessionStart | No direct mapping | Needs adaptation |
| PostToolUseFailure | OpenCode has no independent event | Needs adaptation |

---

## 2. Event Mapping Details

### 2.1 PreToolUse → `tool.execute.before`

OMO implementation (`pre-tool-use.ts`):
- Reads `.claude/settings.json` `hooks.PreToolUse` configuration
- Matches current tool name by `matcher`
- Calls `dispatchHook()` → shell subprocess executes hook script
- hook exit 2 → `throw new Error()` blocks tool invocation
- Supports `modifiedInput` to modify tool parameters

**Carror OS registers 10 matchers / 20 hook invocations on this event**, all of which should work directly.

**Differences to confirm:**
- OpenCode's `tool.execute.before` does not pass a `permission_mode` field. If Carror OS hook scripts depend on this field (e.g., permission-gate.sh), compatibility handling is needed.
- `toolUseId`/`callID` mapping: OMO passes `input.callID` as `tool_use_id`; field name differs from Claude Code.

### 2.2 PostToolUse → `tool.execute.after`

OMO implementation (`post-tool-use.ts`):
- Reads `hooks.PostToolUse` configuration, matches by matcher
- Calls `dispatchHook()` to execute shell script
- Extracts `tool_output` and other fields from `output`, writes to stdin

**Key difference:**

OpenCode's `tool.execute.after` fires regardless of **success or failure**. Claude Code, however, has separate `PostToolUse` (success) and `PostToolUseFailure` (failure).

This means Carror OS's 3 hooks registered under `PostToolUseFailure` (error-dna.sh, posttool-bash-audit.sh, build-validator.sh) would be covered together by `tool.execute.after` on OpenCode. No additional event mapping is needed.

### 2.3 UserPromptSubmit → `chat.message`

OMO implementation (`user-prompt-submit.ts`):
- Reads `hooks.UserPromptSubmit` configuration
- Parses `prompt` field, injects into hook stdin
- Supports `block: true` to block messages

**Note:** OMO skips UserPromptSubmit for `parentSessionId` (sub-sessions), only handling the main session. This differs slightly from Claude Code's behavior.

### 2.4 Stop → `event.session.idle`

OMO implementation (`stop.ts`):
- Fires when `event.type === "session.idle"`
- Supports `stopHookActive` state mechanism: Stop hook can reactivate the session
- Supports `injectPrompt` return value to inject subsequent messages

**Carror OS registers 5 hooks on the Stop event:**
- auto-snapshot.sh (session state snapshot)
- stop-drain.sh (transcript fallback scan)
- skill-flywheel.sh (flywheel log flush)
- error-dna-auto-fix.sh (error auto-fix)
- knowledge-condenser.sh (knowledge compression)

All of these should work directly. The `stopHookActive` mechanism ensures processing is not interrupted.

### 2.5 PreCompact → `experimental.session.compacting`

OMO implementation (`pre-compact.ts`):
- Maps to OpenCode's `experimental.session.compacting` event
- Reads `hooks.PreCompact` configuration

**Carror OS currently does not register a PreCompact hook.** compact-detect.sh is registered under UserPromptSubmit. If a pre-compact hook is needed, it can be added directly.

### 2.6 SessionStart → No Direct Mapping (Needs Adaptation)

**Problem:** OpenCode's Plugin API has no `session:start` event. OMO's `chat.message` handler's first invocation can serve as a SessionStart substitute.

**Carror OS registers 3 hooks on SessionStart:**
- inject-project-knowledge.sh (project knowledge injection)
- flywheel-report.sh (flywheel report)
- token_writer.sh --reset (token counter reset)

**Adaptation plan:**
- Detect if this is the first message in OMO's `createChatMessageHandler` (by session hook state)
- On first message, additionally execute SessionStart hook scripts
- Alternatively: register these scripts directly to `chat.message` matcher, triggering on first UserPromptSubmit

### 2.7 PostToolUseFailure → OpenCode Has No Independent Event

**Problem:** Claude Code has an independent `PostToolUseFailure` event (fires only on failure), but OpenCode's `tool.execute.after` fires for both success and failure.

**This is actually simpler:**
- `tool.execute.after` parameters include error information (`output.error` or similar fields)
- When failure is detected, additionally call Carror OS hooks registered under `PostToolUseFailure`

**Carror OS registers 3 hooks on PostToolUseFailure (all under Bash matcher):**
- error-dna.sh
- posttool-bash-audit.sh
- build-validator.sh

**Adaptation plan:**
- Detect tool execution result in `createToolExecuteAfterHandler`
- If failed, additionally call hooks corresponding to PostToolUseFailure
- These hooks are already schema dual-track compatible (accept both success and failure stdin formats)

---

## 3. Gap Analysis

### 3.1 Stdin Schema Differences

Carror OS hook scripts read JSON input from stdin. Claude Code's fields differ from OpenCode's:

| Claude Code Field | OpenCode (via OMO) | Impact |
|---|---|---|
| `session_id` | `sessionID` | Minor field name difference, low impact |
| `cwd` | `ctx.directory` | Already mapped |
| `tool_name` | `input.tool` | Already mapped |
| `tool_input` | `output.args` | Already mapped |
| `tool_use_id` | `input.callID` | Different field name |
| `permission_mode` | Not available | Some hooks (permission-gate) may depend on it |
| `transcript_path` | Needs confirmation | stop-drain.sh depends on transcript path |
| `hook_source` | `opencode-plugin` (fixed) | Differs from `claude-code-hook`; some detection scripts may need adaptation |

### 3.2 Blocking Mechanism Differences

| Behavior | Claude Code | OpenCode (via OMO) |
|---|---|---|
| hook exit 2 blocks tool | Natively supported | Simulated via `throw new Error()` |
| additionalContext output | Natively injected into AI context | Needs notification via `ctx.client.tui.showToast()` |
| Modifying tool_input | Returns `modifiedInput` | `Object.assign(output.args, modifiedInput)` |
| Timeout mechanism | `timeout` field | OMO supports timeout parameter |

### 3.3 Stop Hook Reactivation Mechanism

OMO's Stop hook implementation is more powerful than Claude Code's:
- `stopHookActive` state tracking — Stop hook can reactivate the session
- Supports `injectPrompt` return value to inject subsequent messages
- Carror OS's 5 Stop hooks (auto-snapshot.sh, etc.) are directly compatible

### 3.4 Exit Code Semantics

Carror OS hook scripts use `exit 2` to indicate blocking. OMO's `executePreToolUseHooks` checks for `result.decision === "deny"` then `throw new Error()`. Need to confirm whether OMO's translation logic for hook script exit codes is consistent with Claude Code.

---

## 4. Implementation Plan

### Phase 1: Compatibility Layer Adaptation (2-3 days)

```
Target: OMO claude-code-hooks compatibility layer
Priority: P0 (Core)
```

#### 4.1 Add SessionStart Support

Add first-session detection mechanism before `session.idle` handling in `session-event-handler.ts`:

```typescript
// In session-event-handler.ts
if (event.type === "session.created" || detect first chat.message) {
  const sessionStartHooks = findMatchingHooks(config, "SessionStart")
  for (const hook of sessionStartHooks) {
    await dispatchHook(hook, sessionStartStdin, cwd)
  }
}
```

Or more simply: execute SessionStart hooks on first call in `createChatMessageHandler`.

#### 4.2 Add PostToolUseFailure Support

Detect failure in `tool-execute-after-handler.ts`:

```typescript
// Detect tool execution failure
const isFailure = output?.error !== undefined || hasErrorExitCode(output)
if (isFailure) {
  const failureHooks = findMatchingHooks(config, "PostToolUseFailure", input.tool)
  for (const hook of failureHooks) {
    await dispatchHook(hook, failureStdin, cwd)
  }
}
```

#### 4.3 Supplement Missing Stdin Fields

Add missing field completion for OpenCode environment in OMO's claude-code-hooks configuration:

```typescript
// stdinData supplement in pre-tool-use.ts
const stdinData = {
  ...baseStdinData,
  permission_mode: "bypassPermissions",  // Fixed value, OpenCode lacks this field
  hook_source: "opencode-plugin",
}
```

#### 4.4 Confirm Exit Code Translation

Verify whether OMO's `executeHookCommand` correctly translates shell exit 2 into `{ decision: "deny" }`. If inconsistent, modify `dispatch-hook.ts`:

```typescript
// In executeHookCommand result handling
if (result.exitCode === 2) {
  return { decision: "deny", reason: result.stderr || "Hook blocked" }
}
```

### Phase 2: Carror OS Side Adaptation (1-2 days)

```
Target: Carror OS hook scripts
Priority: P1 (Basic compatibility)
```

#### 2.1 Check hook_source Dependencies

Search all Carror OS hook scripts for `hook_source` field detection:

```bash
grep -r "hook_source" .claude/hooks/*.sh
```

If present, add `opencode-plugin` as a valid value.

#### 2.2 Check permission_mode Dependencies

Search all hook scripts for references to `permission_mode`:

```bash
grep -r "permission_mode" .claude/hooks/*.sh
```

If present, add OpenCode degradation handling (default pass or fixed value).

#### 2.3 Check transcript_path Dependency

Confirm the transcript-reading logic in scripts like `stop-drain.sh`. OpenCode's transcript file path may differ from Claude Code's and needs adaptation.

#### 2.4 settings.json Compatibility Verification

Confirm OMO's config-loader can correctly parse Carror OS's `.claude/settings.json` format, especially the `|` separator syntax used by matchers (e.g., `"Edit|Write"`).

### Phase 3: Testing and Verification (1-2 days)

```
Priority: P0 (No deploy without verification)
```

#### 3.1 Hook Trigger Verification Checklist

Verify each Carror OS hook triggers correctly on OpenCode + OMO:

| Event | Matcher | Hook | Verification Method |
|-------|---------|------|-------------------|
| PreToolUse | Edit | edit-guard.sh | Try editing an unread file → expect block |
| PreToolUse | Bash | permission-gate.sh | Execute git push → expect block |
| PreToolUse | Bash\|Read\|Grep | privacy-gate.sh | Read .env → expect block |
| PreToolUse | Edit\|Write | context-guard.sh | Write file at 95% context → expect block |
| PostToolUse | TaskUpdate | completion-gate.sh | Update task → expect evidence reminder injection |
| Stop | - | auto-snapshot.sh | End session → expect snapshot generated |
| UserPromptSubmit | - | turn-counter.sh | Submit message → expect turn info injection |

#### 3.2 Regression Testing

Run Carror OS's `harness-smoke-test.sh` on OMO's claude-code-hooks compatibility layer:

```bash
bash .claude/scripts/harness-smoke-test.sh
```

#### 3.3 End-to-End Verification

```bash
# 1. Privacy gate
echo "API_KEY=sk-xxx" > .env && cat .env
→ Expected: blocked by privacy-gate

# 2. Permission gate
git push origin main
→ Expected: blocked by permission-gate

# 3. Context gate
# Trigger 95% context then write file
→ Expected: blocked by context-guard

# 4. Stop hook
# Check after session ends
ls .omc/state/session-snapshot.json
→ Expected: file exists
```

### Phase 4: Operations and Monitoring

```
Priority: P2 (Complete before launch)
```

#### 4.1 Error DNA Fallback on OpenCode

OpenCode's `tool.execute.after` covers all tool results. Carror OS's `error-dna.sh` and `build-validator.sh` originally depend on `PostToolUseFailure` to capture failures. On OpenCode, need to confirm whether `tool.execute.after` parameters contain sufficient information to determine failure.

**Recommendation:** If `tool.execute.after` parameters are insufficient to determine failure, fall back to scanning `transcript.jsonl` (similar to stop-drain.sh's fallback method).

#### 4.2 Triple Consistency Audit

Modify `audit-hooks.sh` to support OpenCode + OMO environments. Add OpenCode platform identifier, check whether OMO has registered all necessary hook events.

---

## 5. Risks and Limitations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| OpenCode Plugin API stability | API changes may break hooks | Lock OMO version, run regression on upstream changes |
| Missing stdin fields | Abnormal hook behavior | Phase 2: supplement missing fields |
| exit 2 block translation | Blocking logic fails | Phase 1.4: verify |
| SessionStart has no direct mapping | Project knowledge not injected | Phase 1.1: adapt |
| transcript_path path differences | stop-drain cannot read transcript | Phase 2.3: adapt |
| OMO version updates | Compatibility layer code changes | PR review: monitor claude-code-hooks directory changes |

---

## 6. Out of Scope

- Will not modify OMO core architecture (only claude-code-hooks compatibility layer)
- Will not refactor Carror OS hook script logic (only compatibility adjustments)
- Does not involve OMO's 70+ TypeScript hooks system
- Does not cover features exclusive to OpenCode (e.g., model routing)

---

## 7. Acceptance Criteria

```
[ ] Phase 1 — OMO compatibility layer adaptation
  [ ] SessionStart hook triggers on first chat.message
  [ ] PostToolUseFailure hook triggers when tool.execute.after detects failure
  [ ] Missing stdin fields supplemented
  [ ] exit 2 blocking logic verified

[ ] Phase 2 — Carror OS side adaptation
  [ ] hook_source compatibility
  [ ] permission_mode compatibility
  [ ] transcript_path compatibility
  [ ] settings.json format compatibility

[ ] Phase 3 — Testing verification
  [ ] All PreToolUse hooks trigger correctly
  [ ] All PostToolUse hooks trigger correctly
  [ ] All Stop hooks trigger correctly
  [ ] All UserPromptSubmit hooks trigger correctly
  [ ] harness-smoke-test.sh all green
  [ ] 5 end-to-end acceptance items passed

[ ] Phase 4 — Operations
  [ ] Error DNA captures correctly on OpenCode
  [ ] audit-hooks.sh supports OpenCode + OMO
```
