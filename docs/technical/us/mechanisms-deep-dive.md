[ARCHIVED v6.2.1 — Historical document. Referenced hooks/scripts/skills may no longer exist. See story-10.]

     1|# Carror OS: High-Value Mechanism Deep Dive
     2|
     3|> Based on full source code reading of 32 hook scripts, 5 compact_inject files, kernel.md, anti-patterns.md, and harness.yaml.
     4|
     5|***
     6|
     7|## Mechanism 1: Completion Gate — Mechanical Termination of False Completion
     8|
     9|**File**: `completion-gate.sh` (`PreToolUse:TaskUpdate`)
    10|
    11|This is Carror OS's most sophisticated single mechanism.
    12|
    13|### The Real Problem It Solves
    14|
    15|AI's biggest deceptive behavior is not "saying something wrong," but **"saying it is done when it is not."** `completion-gate.sh` targets exactly this.
    16|
    17|### Four-Layer Verification Chain
    18|
    19|```bash
    20|AI calls TodoWrite(status="completed")
    21|         ↓
    22|1. Evidence file existence check
    23|   .omc/state/.completion-evidence-YYYYMMDD must exist
    24|   → Does not exist: exit 2 hard block
    25|
    26|2. 5-minute freshness check
    27|   Evidence file must have been written within 5 minutes
    28|   → Expired: exit 2 (prevents reuse of old evidence)
    29|
    30|3. Atomic consumption (prevents concurrent reuse)
    31|   mv evidence file → .consumed.PID
    32|   → Second process mv fails: exit 2
    33|   This is a UNIX atomic operation — even if two AI instances complete simultaneously, both cannot pass
    34|
    35|4. Semantic verification (formal compliance ≠ content truth)
    36|   Evidence must contain:
    37|   - ≥20 characters of actual description (not a "VERIFIED" placeholder)
    38|   - "VERIFIED" keyword
    39|   - One of the structured formats: [Verified: file:line] / exit 0 / PASS / ✅
    40|```
    41|
    42|**The fourth layer is the most critical** (`completion-gate.sh:80-91`):
    43|
    44|```bash
    45|# R27: Semantic verification — formal gate pass ≠ assertion truth
    46|if ! echo "$CONTENT" | grep -qE \
    47|  '(\[Verified:|\[Tested:|✅|exit 0|PASS|is_danger.*false|status.*completed)'; then
    48|    echo "⛔ COMPLETION BLOCKED: Evidence format too vague" >&2
    49|    exit 2
    50|fi
    51|```
    52|
    53|The comment reads `R27` — the product of the 27th fix. This means the previous 26 versions were bypassed here. AI can write an evidence file containing the word "VERIFIED," but the content might be "VERIFIED: The feature should be fine now" — the fourth layer specifically intercepts this kind of semantic cheating.
    54|
    55|### Hidden A→B→A Automatic Trigger
    56|
    57|`completion-gate.sh:96-146`: When evidence content contains words like "verification/benchmark/pass rate," the hook **automatically generates an A→B→A handoff file**:
    58|
    59|```bash
    60|HANDOFF_FILE="$PROJECT_ROOT/.omc/state/cross-verify-handoff.md"
    61|# Scan documents modified within the last 10 minutes
    62|RECENT_DOCS=$(find ... -mmin -10 ...)
    63|cat > "$HANDOFF_FILE" <<HANDOFF
    64|***** Copy all of the following to B terminal *****
    65|[Adversarial verification prompt] Switch to a different model...
    66|HANDOFF
    67|```
    68|
    69|This does not just remind the user "cross-verification is recommended" — it **directly writes the handoff file**, so after the B terminal starts, executing `cat` is all that is needed to begin verification. This reduces process friction to nearly zero.
    70|
    71|***
    72|
    73|## Mechanism 2: Error DNA — Cross-Session Error Memory
    74|
    75|**File**: `error-dna.sh` (`PostToolUse:Bash`) + `stop-drain.sh` (`Stop`) + `inject-project-knowledge.sh` (`SessionStart`)
    76|
    77|These three hooks form a complete error memory loop.
    78|
    79|### Dual Error Signal Collection
    80|
    81|```bash
    82|Real-time layer (error-dna.sh):
    83|  Every Bash exit_code ≠ 0 → immediately structured recording
    84|  Fields: ts / signature / cmd / exit_code / error_type / message / session_id
    85|  Credential sanitization: --password/--token/--secret → *** replacement
    86|
    87|Fallback layer (stop-drain.sh):
    88|  At session end, scan transcript.jsonl
    89|  Capture tool_results where is_error=true (may be missed by real-time layer)
    90|  Dedup key: session_id + signature + ts
    91|```
    92|
    93|**Why stop-drain is needed**: The real-time layer depends on the `PostToolUse` hook, but some tool failures (e.g., timeouts) may not trigger `PostToolUse` and instead trigger `PostToolUseFailure` directly — the fallback layer at session end scans the transcript to catch these. The two layers do not conflict.
    94|
    95|### Error DNA-ification
    96|
    97|Each error generates a `signature` (MD5 of first 16 characters of cmd). The same error across different sessions and turns is automatically aggregated:
    98|
    99|```json
   100|{
   101|  "error_signatures": {
   102|    "a3f2b91c...": {
   103|      "count": 7,
   104|      "fix_count": 3,
   105|      "status": "reopened",
   106|      "last_seen": 1746700000,
   107|      "message": "tsc: error TS2345 ...",
   108|      "fix_context": ["src/types/ecosystem.ts"]
   109|    }
   110|  }
   111|}
   112|```
   113|
   114|`status: "reopened"` = was fixed but has reappeared. This is the **highest priority error** — reappearance means the root cause was not truly resolved.
   115|
   116|### Automatic Error Memory Injection into New Sessions
   117|
   118|`inject-project-knowledge.sh:172-216` — at the start of every new session, the first thing AI sees is:
   119|
   120|```
   121|[Error Memory]
   122|Repeated errors:
   123| - [7 times, fixed 3 times] tsc: error TS2345 Argument of type...
   124|   Last fix related files: src/types/ecosystem.ts
   125|Unresolved errors:
   126| - [3 times] npm run build failed: chunk size exceeds limit
   127|```
   128|
   129|This breaks the fate of AI losing memory every session — **error history no longer disappears just because a session ends.**
   130|
   131|***
   132|
   133|## Mechanism 3: Context Guard — Tiered Response to Context Crises
   134|
   135|**File**: `context-guard.sh` (`PreToolUse:.*`)
   136|
   137|### Precise Read/Write Separation Blocking
   138|
   139|This is a deliberate design choice (`context-guard.sh:29-52`):
   140|
   141|```bash
   142|# Only hard-block write tools (Edit/Write), preserve Read/Grep/Bash diagnostic channels
   143|case "$TOOL_NAME" in
   144|    Edit|Write) BLOCK_WRITES=true ;;
   145|    *)          BLOCK_WRITES=false ;;
   146|esac
   147|```
   148|
   149|**Logic**: "Reading is diagnosis, writing is destruction."
   150|
   151|When context reaches 80%:
   152|
   153|*   `Edit` / `Write` → hard block (exit 2), preventing hallucination-driven code writes
   154|*   `Read` / `Grep` / `Bash` → warn only, preserving diagnostic capability
   155|
   156|This solves a real problem: when context is full, AI still needs to Read files to diagnose why things are wrong. Completely blocking all tools would make self-rescue impossible.
   157|
   158|### Escape Hatch Design
   159|
   160|```bash
   161|OVERRIDE_FILE="$STATE_DIR/context-force-override"
   162|if [ -f "$OVERRIDE_FILE" ]; then
   163|    rm -f "$OVERRIDE_FILE"   # One-time consumption
   164|    exit 0
   165|fi
   166|```
   167|
   168|Users can manually `touch .omc/state/context-force-override` to bypass the block, **but only once**. It auto-deletes after use. This prevents "user permanently disabling the block for convenience."
   169|
   170|***
   171|
   172|## Mechanism 4: Rule Anchor — Active Injection to Prevent Long-Conversation Drift
   173|
   174|**File**: `pretool-rule-anchor.sh` (`PreToolUse:Write`)
   175|
   176|### The Core Problem It Solves
   177|
   178|AI "forgets" rules set early in long conversations — this is not a bug, it is a physical property of the attention mechanism: older content gets lower weight.
   179|
   180|### Dual Trigger Mechanism
   181|
   182|```bash
   183|# Turn threshold: triggers every 5 turns after turn 15
   184|ANCHOR_THRESHOLD=15
   185|ANCHOR_INTERVAL=5
   186|
   187|# Drift word detection: additional trigger
   188|for word in "while you're at it" "also" "additionally" "incidentally"; do
   189|    if grep -qF "$word" "$LAST_PROMPT"; then
   190|        DRIFT_DETECTED=true
   191|```
   192|
   193|**Regular trigger**: At turns 15, 20, 25..., inject before AI writes files:
   194|
   195|> `[Turn 20 - Rule Anchor] 1. No fabrication (needs file:line) 2. VERIFIED evidence required before completion...`
   196|
   197|**Drift word trigger**: Immediately responds when user says "fix this while you are at it":
   198|
   199|> `[Turn 18 - Drift Warning] Scope expansion word detected. Scope freeze rule...`
   200|
   201|This turns "rule decay" from a passive problem into active management. Instead of waiting for AI to drift and then correcting, it preventively injects at the critical nodes where drift **is about to happen.**
   202|
   203|***
   204|
   205|## Mechanism 5: Flywheel — Closed Loop from Error to System Improvement
   206|
   207|**File**: `skill-flywheel.sh` + `flywheel-report.sh`
   208|
   209|### Two-Layer Collection Architecture
   210|
   211|```
   212|AI layer (Phase 1, best-effort):
   213|  lx-* skills write to buffer during execution:
   214|  echo "2026-05-12,privacy_gate_triggered,P0,carror-os" >> ~/.claude/flywheel-buffer.jsonl
   215|
   216|Shell layer (Phase 2, mechanical guarantee):
   217|  skill-flywheel.sh flushes buffer → flywheel.log on each Stop event
   218|```
   219|
   220|The comments explicitly state the design motivation (`skill-flywheel.sh:10-15`):
   221|
   222|```
   223|# lx-* skills write to buffer at the AI layer (best-effort, no guarantee every execution)
   224|# This hook mechanically flushes on each Stop event (AI response end),
   225|# compensating for AI's unreliability
   226|```
   227|
   228|**AI is unreliable** — it sometimes forgets to write to the buffer, sometimes gets interrupted. The Shell hook acts as a mechanical compensation layer, ensuring events are not lost.
   229|
   230|### flywheel.log Format
   231|
   232|```
   233|2026-05-12,privacy_gate_triggered,P0,carror-os
   234|2026-05-12,completion_gate_triggered,P0,anka-ops
   235|2026-05-11,context_guard_triggered,P0,carror-os
   236|```
   237|
   238|`date,event,severity,project` — minimal format, easy to aggregate and analyze.
   239|
   240|### P0 Alert Full-Chain Response
   241|
   242|`flywheel-report.sh:119-210`:
   243|
   244|```
   245|P0 events in last 30 days > 5 AND not acked →
   246|
   247|1. /dev/tty terminal output (visible to user, not in AI context)
   248|2. Persistent flywheel-reports/flywheel-report-{date}.md
   249|3. macOS desktop notification (osascript) / Linux notification (notify-send)
   250|4. AI context injection: show frequency table, ask for disposition
   251|```
   252|
   253|**Users can ack**:
   254|
   255|```bash
   256|echo '2026-05-12,privacy_gate_triggered,resolved,carror-os' >> ~/.claude/flywheel-ack.log
   257|echo '2026-05-12,privacy_gate_triggered,snooze7,carror-os'  >> ~/.claude/flywheel-ack.log
   258|echo '2026-05-12,privacy_gate_triggered,ignore,carror-os'   >> ~/.claude/flywheel-ack.log
   259|```
   260|
   261|This is a **complete event governance closed loop**: trigger → record → aggregate → alert → human disposition → record disposition → no repeat alert next time.
   262|
   263|***
   264|
   265|## Mechanism 6: Knowledge Sublimation — Automatic Experience Elevation
   266|
   267|**File**: Sublimation detection logic in `inject-project-knowledge.sh`
   268|
   269|`claude-next.md` is the "learning journal" — entries are written every time the user corrects AI. But as notes accumulate, injection cost increases and signal-to-noise ratio decreases.
   270|
   271|### Sublimation Trigger Conditions
   272|
   273|```python
   274|# Three trigger signals; any one triggers sublimation prompt
   275|if total >= threshold_count:      # count ≥ 20 entries
   276|if age_days >= threshold_days:    # any entry ≥ 10 days old
   277|if hits >= threshold_hits:        # any entry triggered ≥ 5 times
   278|```
   279|
   280|### Sublimation Migration Path
   281|
   282|```
   283|claude-next.md (temporary experience)
   284|    ↓ trigger conditions met
   285|    ↓ sublimation review
   286|kernel.md (iron law)
   287|or
   288|.claude/compact_inject/*.md (specification)
   289|```
   290|
   291|`kernel.md` already contains traces of sublimated records (`kernel.md:30-38`):
   292|
   293|```markdown
   294|## Frontend coding iron laws (sublimated from claude-next.md @2026-05-08)
   295|<!-- Sublimation condition: age ≥ 10 days OR hits ≥ 5, verified stable -->
   296|- **Do not rely on memory to reference file content in long conversations; beyond 10 turns, must re-Read** (hits:5)
   297|```
   298|
   299|This is a **system for experience evolution** — not all experiences are equal. High-frequency, stable, time-verified experiences are "solidified" into the core kernel. Low-frequency or insufficiently verified experiences stay in the temporary layer.
   300|
   301|***
   302|
   303|## Mechanism 7: Edit Guard + Read Tracker — Mandatory Code Modification Traceability
   304|
   305|**File**: `edit-guard.sh` (`PreToolUse:Edit`) + `posttool-write-cite.sh`
   306|
   307|### Engineering Implementation of Read-before-Edit
   308|
   309|Every time a file is `Read`, the path is written to read-tracker.txt.
   310|Before every `Edit`, the system checks if that file path is in read-tracker.
   311|
   312|```bash
   313|if grep -qxF "$REAL_PATH" "$READ_LOG" 2>/dev/null; then
   314|    exit 0  # Already read, allow
   315|fi
   316|# Not read → block
   317|exit 2
   318|```
   319|
   320|This solves the mechanical execution problem of Global Constitution Article 6 (long conversation stability):
   321|
   322|> "When involving core data structures, APIs, or state machines → always Read the source file"
   323|
   324|Constitutional constraints tell the model it "should" read before editing, but cannot guarantee the model does it. Edit Guard turns "should" into "must" — if you have not Read, the system will not let you Edit.
   325|
   326|The read-tracker is automatically cleared at the start of each new session (`inject-project-knowledge.sh:140`), ensuring Read records are always fresh per session.
   327|
   328|***
   329|
   330|## Mechanism 8: Anti-Patterns Semantic Cheating Classification
   331|
   332|**File**: `anti-patterns.md`
   333|
   334|This is not a "best practices document for humans." It is an **AI self-reference checklist** — injected in full at each SessionStart for AI to reference in real time during execution.
   335|
   336|The most valuable classification is H1 (`anti-patterns.md:162-174`):
   337|
   338|```markdown
   339|### H1: Semantic Fabrication — Formal Compliance Masks Semantic Cheating
   340|
   341|Detection signal: Passes all formal gates, but the output content is semantically untrue
   342|Anti-pattern: Outputting fake content at the semantic layer while all formal Gates are green.
   343|              Formal compliance = complete cover-up chain.
   344|```
   345|
   346|This is the most precise naming of AI's deceptive behavior — **formal compliance can mask semantic cheating.** An AI can:
   347|
   348|*   Have an evidence file (file exists ✓)
   349|*   Contain the word "VERIFIED" (format compliant ✓)
   350|*   Have file:line references (structure compliant ✓)
   351|
   352|But the referenced file:line does not actually contain what it claims.
   353|
   354|`anti-patterns.md`'s correct strategy: "Having an evidence file" ≠ "the assertions in the evidence file are true" — must reference specific line numbers in the file, and the assertion must match the content at that line.
   355|
   356|***
   357|
   358|## Internal Structure: System Relationship of the Eight Mechanisms
   359|
   360|```
   361|┌──────────────────────────────────────────────────────────────────┐
   362|│                        Defense Depth                              │
   363|│                                                                    │
   364|│  Input Layer       Execution Layer     Output Layer     Memory Layer│
   365|│                                                                    │
   366|│  inject-project   edit-guard          completion-gate  error-dna │
   367|│  knowledge        (Read-before        (false-completion  (error    │
   368|│  (session init:   -Edit mandatory)    termination)       memory)  │
   369|│   rules + errors                                                  │
   370|│   + last snapshot)                    privacy-gate     flywheel   │
   371|│                   pretool-rule-       (leak prevention) (event     │
   372|│                   anchor                                         │
   373|│                   (anti-drift         permission-gate  sublimation│
   374|│                    injection)         (random verif.    (experience│
   375|│                                        code approval)   elevation)│
   376|│                   context-guard                                    │
   377|│                   (tiered context                                  │
   378|│                    blocking)                                      │
   379|└──────────────────────────────────────────────────────────────────┘
   380|```
   381|
   382|These eight mechanisms are not isolated features. They cover all nodes where AI development can go wrong:
   383|
   384|| Node | Mechanism | Enforcement Method |
   385||------|-----------|-------------------|
   386|| Forgetting rules at session start | inject-project-knowledge | SessionStart automatic injection |
   387|| Editing code without reading first | edit-guard | No Read record → exit 2 |
   388|| Rules forgotten in long conversations | pretool-rule-anchor | Re-inject before Nth turn file write |
   389|| Continuing to write when context is full | context-guard | Write → exit 2, Read → pass |
   390|| Marking task done without verification | completion-gate | No evidence file → exit 2 |
   391|| Reading/writing sensitive files | privacy-gate | Filename match → exit 2 |
   392|| Executing dangerous commands | permission-gate | Random verification code AI cannot self-generate |
   393|| Errors disappearing after session ends | error-dna + stop-drain | Cross-session persistence, injected in new session |
   394|| High-frequency errors going unnoticed | flywheel | 30-day aggregation + desktop notification |
   395|| Temporary experiences not solidified | sublimation | hits/age triggers sublimation reminder |
   396|
   397|**Not a single mechanism relies on "the model should remember"** — every one uses shell scripts, the filesystem, and exit codes for mechanical guarantees.
   398|
   399|This is what distinguishes Carror OS from other prompt frameworks: **it does not trust AI's will, only the system's constraints.**
   400|