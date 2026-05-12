# Carror OS: High-Value Mechanism Deep Dive

> Based on full source code reading of 32 hook scripts, 5 compact_inject files, kernel.md, anti-patterns.md, and harness.yaml.

***

## Mechanism 1: Completion Gate — Mechanical Termination of False Completion

**File**: `completion-gate.sh` (`PreToolUse:TaskUpdate`)

This is Carror OS's most sophisticated single mechanism.

### The Real Problem It Solves

AI's biggest deceptive behavior is not "saying something wrong," but **"saying it is done when it is not."** `completion-gate.sh` targets exactly this.

### Four-Layer Verification Chain

```bash
AI calls TodoWrite(status="completed")
         ↓
1. Evidence file existence check
   .omc/state/.completion-evidence-YYYYMMDD must exist
   → Does not exist: exit 2 hard block

2. 5-minute freshness check
   Evidence file must have been written within 5 minutes
   → Expired: exit 2 (prevents reuse of old evidence)

3. Atomic consumption (prevents concurrent reuse)
   mv evidence file → .consumed.PID
   → Second process mv fails: exit 2
   This is a UNIX atomic operation — even if two AI instances complete simultaneously, both cannot pass

4. Semantic verification (formal compliance ≠ content truth)
   Evidence must contain:
   - ≥20 characters of actual description (not a "VERIFIED" placeholder)
   - "VERIFIED" keyword
   - One of the structured formats: [Verified: file:line] / exit 0 / PASS / ✅
```

**The fourth layer is the most critical** (`completion-gate.sh:80-91`):

```bash
# R27: Semantic verification — formal gate pass ≠ assertion truth
if ! echo "$CONTENT" | grep -qE \
  '(\[Verified:|\[Tested:|✅|exit 0|PASS|is_danger.*false|status.*completed)'; then
    echo "⛔ COMPLETION BLOCKED: Evidence format too vague" >&2
    exit 2
fi
```

The comment reads `R27` — the product of the 27th fix. This means the previous 26 versions were bypassed here. AI can write an evidence file containing the word "VERIFIED," but the content might be "VERIFIED: The feature should be fine now" — the fourth layer specifically intercepts this kind of semantic cheating.

### Hidden A→B→A Automatic Trigger

`completion-gate.sh:96-146`: When evidence content contains words like "verification/benchmark/pass rate," the hook **automatically generates an A→B→A handoff file**:

```bash
HANDOFF_FILE="$PROJECT_ROOT/.omc/state/cross-verify-handoff.md"
# Scan documents modified within the last 10 minutes
RECENT_DOCS=$(find ... -mmin -10 ...)
cat > "$HANDOFF_FILE" <<HANDOFF
***** Copy all of the following to B terminal *****
[Adversarial verification prompt] Switch to a different model...
HANDOFF
```

This does not just remind the user "cross-verification is recommended" — it **directly writes the handoff file**, so after the B terminal starts, executing `cat` is all that is needed to begin verification. This reduces process friction to nearly zero.

***

## Mechanism 2: Error DNA — Cross-Session Error Memory

**File**: `error-dna.sh` (`PostToolUse:Bash`) + `stop-drain.sh` (`Stop`) + `inject-project-knowledge.sh` (`SessionStart`)

These three hooks form a complete error memory loop.

### Dual Error Signal Collection

```bash
Real-time layer (error-dna.sh):
  Every Bash exit_code ≠ 0 → immediately structured recording
  Fields: ts / signature / cmd / exit_code / error_type / message / session_id
  Credential sanitization: --password/--token/--secret → *** replacement

Fallback layer (stop-drain.sh):
  At session end, scan transcript.jsonl
  Capture tool_results where is_error=true (may be missed by real-time layer)
  Dedup key: session_id + signature + ts
```

**Why stop-drain is needed**: The real-time layer depends on the `PostToolUse` hook, but some tool failures (e.g., timeouts) may not trigger `PostToolUse` and instead trigger `PostToolUseFailure` directly — the fallback layer at session end scans the transcript to catch these. The two layers do not conflict.

### Error DNA-ification

Each error generates a `signature` (MD5 of first 16 characters of cmd). The same error across different sessions and turns is automatically aggregated:

```json
{
  "error_signatures": {
    "a3f2b91c...": {
      "count": 7,
      "fix_count": 3,
      "status": "reopened",
      "last_seen": 1746700000,
      "message": "tsc: error TS2345 ...",
      "fix_context": ["src/types/ecosystem.ts"]
    }
  }
}
```

`status: "reopened"` = was fixed but has reappeared. This is the **highest priority error** — reappearance means the root cause was not truly resolved.

### Automatic Error Memory Injection into New Sessions

`inject-project-knowledge.sh:172-216` — at the start of every new session, the first thing AI sees is:

```
[Error Memory]
Repeated errors:
 - [7 times, fixed 3 times] tsc: error TS2345 Argument of type...
   Last fix related files: src/types/ecosystem.ts
Unresolved errors:
 - [3 times] npm run build failed: chunk size exceeds limit
```

This breaks the fate of AI losing memory every session — **error history no longer disappears just because a session ends.**

***

## Mechanism 3: Context Guard — Tiered Response to Context Crises

**File**: `context-guard.sh` (`PreToolUse:.*`)

### Precise Read/Write Separation Blocking

This is a deliberate design choice (`context-guard.sh:29-52`):

```bash
# Only hard-block write tools (Edit/Write), preserve Read/Grep/Bash diagnostic channels
case "$TOOL_NAME" in
    Edit|Write) BLOCK_WRITES=true ;;
    *)          BLOCK_WRITES=false ;;
esac
```

**Logic**: "Reading is diagnosis, writing is destruction."

When context reaches 80%:

*   `Edit` / `Write` → hard block (exit 2), preventing hallucination-driven code writes
*   `Read` / `Grep` / `Bash` → warn only, preserving diagnostic capability

This solves a real problem: when context is full, AI still needs to Read files to diagnose why things are wrong. Completely blocking all tools would make self-rescue impossible.

### Escape Hatch Design

```bash
OVERRIDE_FILE="$STATE_DIR/context-force-override"
if [ -f "$OVERRIDE_FILE" ]; then
    rm -f "$OVERRIDE_FILE"   # One-time consumption
    exit 0
fi
```

Users can manually `touch .omc/state/context-force-override` to bypass the block, **but only once**. It auto-deletes after use. This prevents "user permanently disabling the block for convenience."

***

## Mechanism 4: Rule Anchor — Active Injection to Prevent Long-Conversation Drift

**File**: `pretool-rule-anchor.sh` (`PreToolUse:Write`)

### The Core Problem It Solves

AI "forgets" rules set early in long conversations — this is not a bug, it is a physical property of the attention mechanism: older content gets lower weight.

### Dual Trigger Mechanism

```bash
# Turn threshold: triggers every 5 turns after turn 15
ANCHOR_THRESHOLD=15
ANCHOR_INTERVAL=5

# Drift word detection: additional trigger
for word in "while you're at it" "also" "additionally" "incidentally"; do
    if grep -qF "$word" "$LAST_PROMPT"; then
        DRIFT_DETECTED=true
```

**Regular trigger**: At turns 15, 20, 25..., inject before AI writes files:

> `[Turn 20 - Rule Anchor] 1. No fabrication (needs file:line) 2. VERIFIED evidence required before completion...`

**Drift word trigger**: Immediately responds when user says "fix this while you are at it":

> `[Turn 18 - Drift Warning] Scope expansion word detected. Scope freeze rule...`

This turns "rule decay" from a passive problem into active management. Instead of waiting for AI to drift and then correcting, it preventively injects at the critical nodes where drift **is about to happen.**

***

## Mechanism 5: Flywheel — Closed Loop from Error to System Improvement

**File**: `skill-flywheel.sh` + `flywheel-report.sh`

### Two-Layer Collection Architecture

```
AI layer (Phase 1, best-effort):
  lx-* skills write to buffer during execution:
  echo "2026-05-12,privacy_gate_triggered,P0,carror-os" >> ~/.claude/flywheel-buffer.jsonl

Shell layer (Phase 2, mechanical guarantee):
  skill-flywheel.sh flushes buffer → flywheel.log on each Stop event
```

The comments explicitly state the design motivation (`skill-flywheel.sh:10-15`):

```
# lx-* skills write to buffer at the AI layer (best-effort, no guarantee every execution)
# This hook mechanically flushes on each Stop event (AI response end),
# compensating for AI's unreliability
```

**AI is unreliable** — it sometimes forgets to write to the buffer, sometimes gets interrupted. The Shell hook acts as a mechanical compensation layer, ensuring events are not lost.

### flywheel.log Format

```
2026-05-12,privacy_gate_triggered,P0,carror-os
2026-05-12,completion_gate_triggered,P0,anka-ops
2026-05-11,context_guard_triggered,P0,carror-os
```

`date,event,severity,project` — minimal format, easy to aggregate and analyze.

### P0 Alert Full-Chain Response

`flywheel-report.sh:119-210`:

```
P0 events in last 30 days > 5 AND not acked →

1. /dev/tty terminal output (visible to user, not in AI context)
2. Persistent flywheel-reports/flywheel-report-{date}.md
3. macOS desktop notification (osascript) / Linux notification (notify-send)
4. AI context injection: show frequency table, ask for disposition
```

**Users can ack**:

```bash
echo '2026-05-12,privacy_gate_triggered,resolved,carror-os' >> ~/.claude/flywheel-ack.log
echo '2026-05-12,privacy_gate_triggered,snooze7,carror-os'  >> ~/.claude/flywheel-ack.log
echo '2026-05-12,privacy_gate_triggered,ignore,carror-os'   >> ~/.claude/flywheel-ack.log
```

This is a **complete event governance closed loop**: trigger → record → aggregate → alert → human disposition → record disposition → no repeat alert next time.

***

## Mechanism 6: Knowledge Sublimation — Automatic Experience Elevation

**File**: Sublimation detection logic in `inject-project-knowledge.sh`

`claude-next.md` is the "learning journal" — entries are written every time the user corrects AI. But as notes accumulate, injection cost increases and signal-to-noise ratio decreases.

### Sublimation Trigger Conditions

```python
# Three trigger signals; any one triggers sublimation prompt
if total >= threshold_count:      # count ≥ 20 entries
if age_days >= threshold_days:    # any entry ≥ 10 days old
if hits >= threshold_hits:        # any entry triggered ≥ 5 times
```

### Sublimation Migration Path

```
claude-next.md (temporary experience)
    ↓ trigger conditions met
    ↓ sublimation review
kernel.md (iron law)
or
.claude/compact_inject/*.md (specification)
```

`kernel.md` already contains traces of sublimated records (`kernel.md:30-38`):

```markdown
## Frontend coding iron laws (sublimated from claude-next.md @2026-05-08)
<!-- Sublimation condition: age ≥ 10 days OR hits ≥ 5, verified stable -->
- **Do not rely on memory to reference file content in long conversations; beyond 10 turns, must re-Read** (hits:5)
```

This is a **system for experience evolution** — not all experiences are equal. High-frequency, stable, time-verified experiences are "solidified" into the core kernel. Low-frequency or insufficiently verified experiences stay in the temporary layer.

***

## Mechanism 7: Edit Guard + Read Tracker — Mandatory Code Modification Traceability

**File**: `edit-guard.sh` (`PreToolUse:Edit`) + `posttool-write-cite.sh`

### Engineering Implementation of Read-before-Edit

Every time a file is `Read`, the path is written to read-tracker.txt.
Before every `Edit`, the system checks if that file path is in read-tracker.

```bash
if grep -qxF "$REAL_PATH" "$READ_LOG" 2>/dev/null; then
    exit 0  # Already read, allow
fi
# Not read → block
exit 2
```

This solves the mechanical execution problem of Global Constitution Article 6 (long conversation stability):

> "When involving core data structures, APIs, or state machines → always Read the source file"

Constitutional constraints tell the model it "should" read before editing, but cannot guarantee the model does it. Edit Guard turns "should" into "must" — if you have not Read, the system will not let you Edit.

The read-tracker is automatically cleared at the start of each new session (`inject-project-knowledge.sh:140`), ensuring Read records are always fresh per session.

***

## Mechanism 8: Anti-Patterns Semantic Cheating Classification

**File**: `anti-patterns.md`

This is not a "best practices document for humans." It is an **AI self-reference checklist** — injected in full at each SessionStart for AI to reference in real time during execution.

The most valuable classification is H1 (`anti-patterns.md:162-174`):

```markdown
### H1: Semantic Fabrication — Formal Compliance Masks Semantic Cheating

Detection signal: Passes all formal gates, but the output content is semantically untrue
Anti-pattern: Outputting fake content at the semantic layer while all formal Gates are green.
              Formal compliance = complete cover-up chain.
```

This is the most precise naming of AI's deceptive behavior — **formal compliance can mask semantic cheating.** An AI can:

*   Have an evidence file (file exists ✓)
*   Contain the word "VERIFIED" (format compliant ✓)
*   Have file:line references (structure compliant ✓)

But the referenced file:line does not actually contain what it claims.

`anti-patterns.md`'s correct strategy: "Having an evidence file" ≠ "the assertions in the evidence file are true" — must reference specific line numbers in the file, and the assertion must match the content at that line.

***

## Internal Structure: System Relationship of the Eight Mechanisms

```
┌──────────────────────────────────────────────────────────────────┐
│                        Defense Depth                              │
│                                                                    │
│  Input Layer       Execution Layer     Output Layer     Memory Layer│
│                                                                    │
│  inject-project   edit-guard          completion-gate  error-dna │
│  knowledge        (Read-before        (false-completion  (error    │
│  (session init:   -Edit mandatory)    termination)       memory)  │
│   rules + errors                                                  │
│   + last snapshot)                    privacy-gate     flywheel   │
│                   pretool-rule-       (leak prevention) (event     │
│                   anchor                                         │
│                   (anti-drift         permission-gate  sublimation│
│                    injection)         (random verif.    (experience│
│                                        code approval)   elevation)│
│                   context-guard                                    │
│                   (tiered context                                  │
│                    blocking)                                      │
└──────────────────────────────────────────────────────────────────┘
```

These eight mechanisms are not isolated features. They cover all nodes where AI development can go wrong:

| Node | Mechanism | Enforcement Method |
|------|-----------|-------------------|
| Forgetting rules at session start | inject-project-knowledge | SessionStart automatic injection |
| Editing code without reading first | edit-guard | No Read record → exit 2 |
| Rules forgotten in long conversations | pretool-rule-anchor | Re-inject before Nth turn file write |
| Continuing to write when context is full | context-guard | Write → exit 2, Read → pass |
| Marking task done without verification | completion-gate | No evidence file → exit 2 |
| Reading/writing sensitive files | privacy-gate | Filename match → exit 2 |
| Executing dangerous commands | permission-gate | Random verification code AI cannot self-generate |
| Errors disappearing after session ends | error-dna + stop-drain | Cross-session persistence, injected in new session |
| High-frequency errors going unnoticed | flywheel | 30-day aggregation + desktop notification |
| Temporary experiences not solidified | sublimation | hits/age triggers sublimation reminder |

**Not a single mechanism relies on "the model should remember"** — every one uses shell scripts, the filesystem, and exit codes for mechanical guarantees.

This is what distinguishes Carror OS from other prompt frameworks: **it does not trust AI's will, only the system's constraints.**
