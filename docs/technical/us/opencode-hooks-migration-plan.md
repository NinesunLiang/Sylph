[ARCHIVED v6.2.1 — Historical document. Referenced hooks/scripts/skills may no longer exist. See story-10.]

     1|# OpenCode Hooks Migration Plan: Achieving Claude Code-Level Hook Capabilities via OMO
     2|
     3|> Date: 2026-05-13 | Status: Draft | Goal: Carror OS obtains hook governance capabilities on OpenCode equivalent to Claude Code
     4|
     5|---
     6|
     7|## 1. Core Conclusion
     8|
     9|**oh-my-openagent (OMO) already has a Claude Code hooks compatibility layer**, located at `src/hooks/claude-code-hooks/`, which can map Claude Code's `.claude/settings.json` hook configuration to OpenCode's Plugin hook points.
    10|
    11|**Existing Compatibility Layer Capability Matrix:**
    12|
    13|| Claude Code Event | OMO Compatibility Layer | Status |
    14||---|---|---|
    15|| PreToolUse | `tool.execute.before` | Implemented |
    16|| PostToolUse | `tool.execute.after` | Implemented |
    17|| UserPromptSubmit | `chat.message` | Implemented |
    18|| Stop | `event.session.idle` | Implemented (with `stopHookActive` reactivation mechanism) |
    19|| PreCompact | `experimental.session.compacting` | Implemented |
    20|| SessionStart | No direct mapping | Needs adaptation |
    21|| PostToolUseFailure | OpenCode has no independent event | Needs adaptation |
    22|
    23|---
    24|
    25|## 2. Event Mapping Details
    26|
    27|### 2.1 PreToolUse → `tool.execute.before`
    28|
    29|OMO implementation (`pre-tool-use.ts`):
    30|- Reads `.claude/settings.json` `hooks.PreToolUse` configuration
    31|- Matches current tool name by `matcher`
    32|- Calls `dispatchHook()` → shell subprocess executes hook script
    33|- hook exit 2 → `throw new Error()` blocks tool invocation
    34|- Supports `modifiedInput` to modify tool parameters
    35|
    36|**Carror OS registers 10 matchers / 20 hook invocations on this event**, all of which should work directly.
    37|
    38|**Differences to confirm:**
    39|- OpenCode's `tool.execute.before` does not pass a `permission_mode` field. If Carror OS hook scripts depend on this field (e.g., permission-gate.sh), compatibility handling is needed.
    40|- `toolUseId`/`callID` mapping: OMO passes `input.callID` as `tool_use_id`; field name differs from Claude Code.
    41|
    42|### 2.2 PostToolUse → `tool.execute.after`
    43|
    44|OMO implementation (`post-tool-use.ts`):
    45|- Reads `hooks.PostToolUse` configuration, matches by matcher
    46|- Calls `dispatchHook()` to execute shell script
    47|- Extracts `tool_output` and other fields from `output`, writes to stdin
    48|
    49|**Key difference:**
    50|
    51|OpenCode's `tool.execute.after` fires regardless of **success or failure**. Claude Code, however, has separate `PostToolUse` (success) and `PostToolUseFailure` (failure).
    52|
    53|This means Carror OS's 3 hooks registered under `PostToolUseFailure` (error-dna.sh, posttool-bash-audit.sh, build-validator.sh) would be covered together by `tool.execute.after` on OpenCode. No additional event mapping is needed.
    54|
    55|### 2.3 UserPromptSubmit → `chat.message`
    56|
    57|OMO implementation (`user-prompt-submit.ts`):
    58|- Reads `hooks.UserPromptSubmit` configuration
    59|- Parses `prompt` field, injects into hook stdin
    60|- Supports `block: true` to block messages
    61|
    62|**Note:** OMO skips UserPromptSubmit for `parentSessionId` (sub-sessions), only handling the main session. This differs slightly from Claude Code's behavior.
    63|
    64|### 2.4 Stop → `event.session.idle`
    65|
    66|OMO implementation (`stop.ts`):
    67|- Fires when `event.type === "session.idle"`
    68|- Supports `stopHookActive` state mechanism: Stop hook can reactivate the session
    69|- Supports `injectPrompt` return value to inject subsequent messages
    70|
    71|**Carror OS registers 5 hooks on the Stop event:**
    72|- auto-snapshot.sh (session state snapshot)
    73|- stop-drain.sh (transcript fallback scan)
    74|- skill-flywheel.sh (flywheel log flush)
    75|- error-dna-auto-fix.sh (error auto-fix)
    76|- knowledge-condenser.sh (knowledge compression)
    77|
    78|All of these should work directly. The `stopHookActive` mechanism ensures processing is not interrupted.
    79|
    80|### 2.5 PreCompact → `experimental.session.compacting`
    81|
    82|OMO implementation (`pre-compact.ts`):
    83|- Maps to OpenCode's `experimental.session.compacting` event
    84|- Reads `hooks.PreCompact` configuration
    85|
    86|**Carror OS currently does not register a PreCompact hook.** compact-detect.sh is registered under UserPromptSubmit. If a pre-compact hook is needed, it can be added directly.
    87|
    88|### 2.6 SessionStart → No Direct Mapping (Needs Adaptation)
    89|
    90|**Problem:** OpenCode's Plugin API has no `session:start` event. OMO's `chat.message` handler's first invocation can serve as a SessionStart substitute.
    91|
    92|**Carror OS registers 3 hooks on SessionStart:**
    93|- inject-project-knowledge.sh (project knowledge injection)
    94|- flywheel-report.sh (flywheel report)
    95|- token_writer.sh --reset (token counter reset)
    96|
    97|**Adaptation plan:**
    98|- Detect if this is the first message in OMO's `createChatMessageHandler` (by session hook state)
    99|- On first message, additionally execute SessionStart hook scripts
   100|- Alternatively: register these scripts directly to `chat.message` matcher, triggering on first UserPromptSubmit
   101|
   102|### 2.7 PostToolUseFailure → OpenCode Has No Independent Event
   103|
   104|**Problem:** Claude Code has an independent `PostToolUseFailure` event (fires only on failure), but OpenCode's `tool.execute.after` fires for both success and failure.
   105|
   106|**This is actually simpler:**
   107|- `tool.execute.after` parameters include error information (`output.error` or similar fields)
   108|- When failure is detected, additionally call Carror OS hooks registered under `PostToolUseFailure`
   109|
   110|**Carror OS registers 3 hooks on PostToolUseFailure (all under Bash matcher):**
   111|- error-dna.sh
   112|- posttool-bash-audit.sh
   113|- build-validator.sh
   114|
   115|**Adaptation plan:**
   116|- Detect tool execution result in `createToolExecuteAfterHandler`
   117|- If failed, additionally call hooks corresponding to PostToolUseFailure
   118|- These hooks are already schema dual-track compatible (accept both success and failure stdin formats)
   119|
   120|---
   121|
   122|## 3. Gap Analysis
   123|
   124|### 3.1 Stdin Schema Differences
   125|
   126|Carror OS hook scripts read JSON input from stdin. Claude Code's fields differ from OpenCode's:
   127|
   128|| Claude Code Field | OpenCode (via OMO) | Impact |
   129||---|---|---|
   130|| `session_id` | `sessionID` | Minor field name difference, low impact |
   131|| `cwd` | `ctx.directory` | Already mapped |
   132|| `tool_name` | `input.tool` | Already mapped |
   133|| `tool_input` | `output.args` | Already mapped |
   134|| `tool_use_id` | `input.callID` | Different field name |
   135|| `permission_mode` | Not available | Some hooks (permission-gate) may depend on it |
   136|| `transcript_path` | Needs confirmation | stop-drain.sh depends on transcript path |
   137|| `hook_source` | `opencode-plugin` (fixed) | Differs from `claude-code-hook`; some detection scripts may need adaptation |
   138|
   139|### 3.2 Blocking Mechanism Differences
   140|
   141|| Behavior | Claude Code | OpenCode (via OMO) |
   142||---|---|---|
   143|| hook exit 2 blocks tool | Natively supported | Simulated via `throw new Error()` |
   144|| additionalContext output | Natively injected into AI context | Needs notification via `ctx.client.tui.showToast()` |
   145|| Modifying tool_input | Returns `modifiedInput` | `Object.assign(output.args, modifiedInput)` |
   146|| Timeout mechanism | `timeout` field | OMO supports timeout parameter |
   147|
   148|### 3.3 Stop Hook Reactivation Mechanism
   149|
   150|OMO's Stop hook implementation is more powerful than Claude Code's:
   151|- `stopHookActive` state tracking — Stop hook can reactivate the session
   152|- Supports `injectPrompt` return value to inject subsequent messages
   153|- Carror OS's 5 Stop hooks (auto-snapshot.sh, etc.) are directly compatible
   154|
   155|### 3.4 Exit Code Semantics
   156|
   157|Carror OS hook scripts use `exit 2` to indicate blocking. OMO's `executePreToolUseHooks` checks for `result.decision === "deny"` then `throw new Error()`. Need to confirm whether OMO's translation logic for hook script exit codes is consistent with Claude Code.
   158|
   159|---
   160|
   161|## 4. Implementation Plan
   162|
   163|### Phase 1: Compatibility Layer Adaptation (2-3 days)
   164|
   165|```
   166|Target: OMO claude-code-hooks compatibility layer
   167|Priority: P0 (Core)
   168|```
   169|
   170|#### 4.1 Add SessionStart Support
   171|
   172|Add first-session detection mechanism before `session.idle` handling in `session-event-handler.ts`:
   173|
   174|```typescript
   175|// In session-event-handler.ts
   176|if (event.type === "session.created" || detect first chat.message) {
   177|  const sessionStartHooks = findMatchingHooks(config, "SessionStart")
   178|  for (const hook of sessionStartHooks) {
   179|    await dispatchHook(hook, sessionStartStdin, cwd)
   180|  }
   181|}
   182|```
   183|
   184|Or more simply: execute SessionStart hooks on first call in `createChatMessageHandler`.
   185|
   186|#### 4.2 Add PostToolUseFailure Support
   187|
   188|Detect failure in `tool-execute-after-handler.ts`:
   189|
   190|```typescript
   191|// Detect tool execution failure
   192|const isFailure = output?.error !== undefined || hasErrorExitCode(output)
   193|if (isFailure) {
   194|  const failureHooks = findMatchingHooks(config, "PostToolUseFailure", input.tool)
   195|  for (const hook of failureHooks) {
   196|    await dispatchHook(hook, failureStdin, cwd)
   197|  }
   198|}
   199|```
   200|
   201|#### 4.3 Supplement Missing Stdin Fields
   202|
   203|Add missing field completion for OpenCode environment in OMO's claude-code-hooks configuration:
   204|
   205|```typescript
   206|// stdinData supplement in pre-tool-use.ts
   207|const stdinData = {
   208|  ...baseStdinData,
   209|  permission_mode: "bypassPermissions",  // Fixed value, OpenCode lacks this field
   210|  hook_source: "opencode-plugin",
   211|}
   212|```
   213|
   214|#### 4.4 Confirm Exit Code Translation
   215|
   216|Verify whether OMO's `executeHookCommand` correctly translates shell exit 2 into `{ decision: "deny" }`. If inconsistent, modify `dispatch-hook.ts`:
   217|
   218|```typescript
   219|// In executeHookCommand result handling
   220|if (result.exitCode === 2) {
   221|  return { decision: "deny", reason: result.stderr || "Hook blocked" }
   222|}
   223|```
   224|
   225|### Phase 2: Carror OS Side Adaptation (1-2 days)
   226|
   227|```
   228|Target: Carror OS hook scripts
   229|Priority: P1 (Basic compatibility)
   230|```
   231|
   232|#### 2.1 Check hook_source Dependencies
   233|
   234|Search all Carror OS hook scripts for `hook_source` field detection:
   235|
   236|```bash
   237|grep -r "hook_source" .claude/hooks/*.sh
   238|```
   239|
   240|If present, add `opencode-plugin` as a valid value.
   241|
   242|#### 2.2 Check permission_mode Dependencies
   243|
   244|Search all hook scripts for references to `permission_mode`:
   245|
   246|```bash
   247|grep -r "permission_mode" .claude/hooks/*.sh
   248|```
   249|
   250|If present, add OpenCode degradation handling (default pass or fixed value).
   251|
   252|#### 2.3 Check transcript_path Dependency
   253|
   254|Confirm the transcript-reading logic in scripts like `stop-drain.sh`. OpenCode's transcript file path may differ from Claude Code's and needs adaptation.
   255|
   256|#### 2.4 settings.json Compatibility Verification
   257|
   258|Confirm OMO's config-loader can correctly parse Carror OS's `.claude/settings.json` format, especially the `|` separator syntax used by matchers (e.g., `"Edit|Write"`).
   259|
   260|### Phase 3: Testing and Verification (1-2 days)
   261|
   262|```
   263|Priority: P0 (No deploy without verification)
   264|```
   265|
   266|#### 3.1 Hook Trigger Verification Checklist
   267|
   268|Verify each Carror OS hook triggers correctly on OpenCode + OMO:
   269|
   270|| Event | Matcher | Hook | Verification Method |
   271||-------|---------|------|-------------------|
   272|| PreToolUse | Edit | edit-guard.sh | Try editing an unread file → expect block |
   273|| PreToolUse | Bash | permission-gate.sh | Execute git push → expect block |
   274|| PreToolUse | Bash\|Read\|Grep | privacy-gate.sh | Read .env → expect block |
   275|| PreToolUse | Edit\|Write | context-guard.sh | Write file at 95% context → expect block |
   276|| PostToolUse | TaskUpdate | completion-gate.sh | Update task → expect evidence reminder injection |
   277|| Stop | - | auto-snapshot.sh | End session → expect snapshot generated |
   278|| UserPromptSubmit | - | turn-counter.sh | Submit message → expect turn info injection |
   279|
   280|#### 3.2 Regression Testing
   281|
   282|Run Carror OS's `harness-smoke-test.sh` on OMO's claude-code-hooks compatibility layer:
   283|
   284|```bash
   285|bash .claude/scripts/harness-smoke-test.sh
   286|```
   287|
   288|#### 3.3 End-to-End Verification
   289|
   290|```bash
   291|# 1. Privacy gate
   292|echo "API_KEY=*** > .env && cat .env
   293|→ Expected: blocked by privacy-gate
   294|
   295|# 2. Permission gate
   296|git push origin main
   297|→ Expected: blocked by permission-gate
   298|
   299|# 3. Context gate
   300|# Trigger 95% context then write file
   301|→ Expected: blocked by context-guard
   302|
   303|# 4. Stop hook
   304|# Check after session ends
   305|ls .omc/state/session-snapshot.json
   306|→ Expected: file exists
   307|```
   308|
   309|### Phase 4: Operations and Monitoring
   310|
   311|```
   312|Priority: P2 (Complete before launch)
   313|```
   314|
   315|#### 4.1 Error DNA Fallback on OpenCode
   316|
   317|OpenCode's `tool.execute.after` covers all tool results. Carror OS's `error-dna.sh` and `build-validator.sh` originally depend on `PostToolUseFailure` to capture failures. On OpenCode, need to confirm whether `tool.execute.after` parameters contain sufficient information to determine failure.
   318|
   319|**Recommendation:** If `tool.execute.after` parameters are insufficient to determine failure, fall back to scanning `transcript.jsonl` (similar to stop-drain.sh's fallback method).
   320|
   321|#### 4.2 Triple Consistency Audit
   322|
   323|Modify `audit-hooks.sh` to support OpenCode + OMO environments. Add OpenCode platform identifier, check whether OMO has registered all necessary hook events.
   324|
   325|---
   326|
   327|## 5. Risks and Limitations
   328|
   329|| Risk | Impact | Mitigation |
   330||------|--------|-----------|
   331|| OpenCode Plugin API stability | API changes may break hooks | Lock OMO version, run regression on upstream changes |
   332|| Missing stdin fields | Abnormal hook behavior | Phase 2: supplement missing fields |
   333|| exit 2 block translation | Blocking logic fails | Phase 1.4: verify |
   334|| SessionStart has no direct mapping | Project knowledge not injected | Phase 1.1: adapt |
   335|| transcript_path path differences | stop-drain cannot read transcript | Phase 2.3: adapt |
   336|| OMO version updates | Compatibility layer code changes | PR review: monitor claude-code-hooks directory changes |
   337|
   338|---
   339|
   340|## 6. Out of Scope
   341|
   342|- Will not modify OMO core architecture (only claude-code-hooks compatibility layer)
   343|- Will not refactor Carror OS hook script logic (only compatibility adjustments)
   344|- Does not involve OMO's 70+ TypeScript hooks system
   345|- Does not cover features exclusive to OpenCode (e.g., model routing)
   346|
   347|---
   348|
   349|## 7. Acceptance Criteria
   350|
   351|```
   352|[ ] Phase 1 — OMO compatibility layer adaptation
   353|  [ ] SessionStart hook triggers on first chat.message
   354|  [ ] PostToolUseFailure hook triggers when tool.execute.after detects failure
   355|  [ ] Missing stdin fields supplemented
   356|  [ ] exit 2 blocking logic verified
   357|
   358|[ ] Phase 2 — Carror OS side adaptation
   359|  [ ] hook_source compatibility
   360|  [ ] permission_mode compatibility
   361|  [ ] transcript_path compatibility
   362|  [ ] settings.json format compatibility
   363|
   364|[ ] Phase 3 — Testing verification
   365|  [ ] All PreToolUse hooks trigger correctly
   366|  [ ] All PostToolUse hooks trigger correctly
   367|  [ ] All Stop hooks trigger correctly
   368|  [ ] All UserPromptSubmit hooks trigger correctly
   369|  [ ] harness-smoke-test.sh all green
   370|  [ ] 5 end-to-end acceptance items passed
   371|
   372|[ ] Phase 4 — Operations
   373|  [ ] Error DNA captures correctly on OpenCode
   374|  [ ] audit-hooks.sh supports OpenCode + OMO
   375|```
   376|