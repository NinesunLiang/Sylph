# Carror OS: Mechanism Analysis and Comprehensive Evaluation

> Compiled from: material-3.md, Carror-OS-mechanisms.md, conclusion-1.md, conclusion-7.md, aggregated-6.md, next-steps.md

---

## Part 1: 5 Guardrails That Actually Work

Many people believe AI errors can be solved with better prompts. But anyone who has actually used AI to write code, modify files, and run tasks knows: **a reminder is not a constraint.**

You can tell AI "do not fabricate," "verify before completing," "do not read sensitive files." It may agree. But by turn 20, under high context, near the end of a task, it will still forget, skip, and confidently do the wrong thing.

Carror OS does not bet on AI remembering. It does something different: **turns critical rules into guardrails that actually work.**

### Guardrail 1: Completion Gate — No More Empty "It Is Done"

AI's most common and most frustrating error is not inability. It is **not finishing, but claiming it is done.** The worst part is not the mistake. It is that AI says "I have completed it" in a tone that sounds entirely convincing. The subsequent checking, verification, and rework all fall on you.

Carror OS's first guardrail: **AI cannot declare completion with a single sentence. It must submit evidence.**

When AI tries to mark a task as completed, the system asks:
- Were the tests run?
- Does the output match expectations?
- Is there structured verification evidence?

If not, the system stops it.

The most important thing here is not the word "verification." It is that **the right to declare completion has been taken away.** Before, "completion" was declared by AI itself. Now, "completion" is granted by the system based on evidence.

### Guardrail 2: Rule Anchor — When AI Forgets, the System Remembers

AI "forgets" rules set early in long conversations — this is not a bug, it is a physical property of the attention mechanism. Turn 8 is fine. Turn 12 starts slipping. By turn 20, it writes as if it never heard those rules.

Carror OS places rules **before the action.** Before AI writes a file, the system re-injects the critical rules. The key point: **Carror OS does not rely on AI remembering by itself.** It places the rules in front of AI before the critical action happens. You do not need to manually re-explain at turn 20. The system does it for you.

### Guardrail 3: Privacy Gate — What It Should Not Read, It Simply Cannot Read

Many people's first real moment of AI security awareness does not come from the news. It comes from a specific moment. Like mentioning `.env` in a conversation, and suddenly feeling a chill.

Carror OS's approach to this problem is simple: **Sensitive files should not be left to AI's discretion. They should be directly forbidden.** If AI tries to read `.env`, key files, or sensitive configuration, the system intercepts it. The difference is fundamental. Before: "I hope AI understands what it should and should not read." Now: "Even if it wants to read, it cannot." Real security is putting some things where AI can never reach.

### Guardrail 4: Dangerous Action Gate — Dangerous Actions Cannot Be Executed Just Because AI Wants To

Another common AI problem is not misunderstanding, but **acting too quickly.** It finds a seemingly reasonable action path and just does it: git add, commit, delete files, run migrations, modify databases, execute production commands. The problem is that **high-risk actions should not happen just because AI thinks they are reasonable.** Because once they happen, the consequences are real. You bear them.

So Carror OS's fourth guardrail is clear: **Dangerous actions must return to human control.** AI can propose, prepare commands, explain why. But it cannot cross that last door itself.

### Guardrail 5: Project Memory — The Same Mistake Should Not Require a Fifth Explanation

The most draining thing about AI collaboration is not the big mistake. It is **the same mistake, over and over again.** You just explained that this type error was previously fixed, that this directory must not be touched, that this interface cannot have its signature changed due to historical reasons. AI understands in the moment. Next session, it is a brand new day. You re-explain. It re-apologizes. You re-consume.

Carror OS's fifth guardrail: **Move project lessons and error memory out of your brain and into the system as injectable knowledge.** Before each new session, the system automatically injects historical errors, unresolved issues, and frequently encountered pitfalls into AI. You no longer need to be the "memory relay station" every time. The project finally begins to have **accumulated collaborative memory.**

### The Fundamental Difference: Prompt vs Gate

| Dimension | Prompt | Gate |
|-----------|--------|------|
| Logic | I tell you what to do; please try your best | If conditions are not met, you cannot proceed |
| Nature | Suggestion | Permission to proceed |
| Dependency | Model stays stable at all times | System makes judgments at critical points |
| Risk | Can be forgotten, diluted, bypassed | As long as the rule exists, it takes effect |

**A Prompt is a reminder. A Gate is permission control. Carror OS does not remind AI to do things correctly — it decides whether AI can proceed before it does something wrong.**

---

## Part 2: Eight High-Value Mechanism Deep Dives

Based on full source code reading of 32 hook scripts, 5 compact_inject files, kernel.md, anti-patterns.md, and harness.yaml.

### Mechanism 1: Completion Gate — Mechanical Termination of False Completion

**File**: `completion-gate.sh` (PreToolUse:TaskUpdate)

Four-layer verification chain:
1. **Evidence file existence check**: `.omc/state/.completion-evidence-YYYYMMDD` must exist. Missing → exit 2 hard block
2. **5-minute freshness check**: Evidence file must have been written within 5 minutes. Expired → exit 2 (prevents reuse of old evidence)
3. **Atomic consumption (prevents concurrent reuse)**: `mv` evidence file → `.consumed.PID`. Second process mv fails → exit 2. This is a UNIX atomic operation — even if two AI instances complete simultaneously, both cannot pass
4. **Semantic verification (formal compliance ≠ content truth)**: Evidence must contain ≥20 characters of actual description, the "VERIFIED" keyword, and one of the structured formats

**The fourth layer is the most critical**: The comment reads `R27` — the product of the 27th fix. AI can write an evidence file containing the word "VERIFIED," but the content might be "VERIFIED: The feature should be fine now" — the fourth layer specifically intercepts this kind of semantic cheating.

Hidden A→B→A automatic trigger: When evidence content contains words like "verification/benchmark/pass rate," the hook **automatically generates an A→B→A handoff file**, writing the handoff content so that after the B terminal starts, executing `cat` can begin verification immediately.

### Mechanism 2: Error DNA — Cross-Session Error Memory

**File**: `error-dna.sh` (PostToolUse:Bash) + `stop-drain.sh` (Stop) + `inject-project-knowledge.sh` (SessionStart)

Three hooks form a complete error memory loop:
- **Real-time layer**: Every Bash exit_code ≠ 0 → immediately structured recording. Fields: ts/signature/cmd/exit_code/error_type/message/session_id. Credential sanitization: --password/--token/--secret → *** replacement
- **Fallback layer**: At session end, scan transcript.jsonl to capture tool_results where is_error=true
- **Injection layer**: At each new session start, AI sees error memory as its first input

Each error generates a signature (MD5 of first 16 characters of cmd). Same errors aggregate across sessions. `status: "reopened"` = was fixed but reappeared.

### Mechanism 3: Context Guard — Tiered Response to Context Crises

**File**: `context-guard.sh` (PreToolUse:Edit|Write)

Precise read/write separation: Only hard-blocks write tools (Edit/Write), preserves Read/Grep/Bash diagnostic channels. The logic is "reading is diagnosis, writing is destruction." At 80% context, Edit/Write → hard block (exit 2) to prevent hallucination-driven code writes; Read/Grep/Bash → warn only, preserving diagnostic capability.

Escape hatch: Users can `touch .omc/state/context-force-override` to bypass the block, but only once. It auto-deletes after use.

### Mechanism 4: Rule Anchor — Active Injection to Prevent Long-Conversation Drift

**File**: `pretool-rule-anchor.sh` (PreToolUse:Write)

Dual trigger mechanism:
- **Regular trigger**: At turns 15, 20, 25..., inject rule anchors before AI writes files
- **Drift-word trigger**: Immediately responds when user says "fix this while you are at it" — prompts the scope freeze rule

### Mechanism 5: Flywheel — Closed Loop from Error to System Improvement

**File**: `skill-flywheel.sh` + `flywheel-report.sh`

Two-layer collection architecture:
- AI layer (Phase 1, best-effort): lx-* skills write to buffer during execution
- Shell layer (Phase 2, mechanical guarantee): skill-flywheel.sh flushes buffer → flywheel.log on each Stop event

P0 alert full-chain response: P0 events > 5 within 30 days and not ack'ed → terminal output + persistent report + desktop notification + AI context injection.

### Mechanism 6: Knowledge Sublimation — Automatic Experience Elevation

**File**: `inject-project-knowledge.sh`

claude-next.md (temporary experience) → three trigger signals (count ≥20 items / any item ≥10 days old / any item triggered ≥5 times) → sublimation review → kernel.md (iron law) or `.claude/compact_inject/*.md` (specification)

### Mechanism 7: Edit Guard + Read Tracker — Mandatory Code Modification Traceability

**File**: `edit-guard.sh` (PreToolUse:Edit) + `posttool-write-cite.sh`

Every time a file is Read, the path is written to read-tracker.txt. Before every Edit, the system checks if that file path is in read-tracker. No Read → exit 2. Constitutional constraints tell the model it "should" read before editing, but cannot guarantee the model does it. Edit Guard turns "should" into "must."

### Mechanism 8: Anti-Patterns Semantic Cheating Classification

**File**: `anti-patterns.md`

The most valuable classification is H1: Semantic fabrication — formal compliance masks semantic cheating. AI can have an evidence file (file exists ✓), contain the word "VERIFIED" (format compliant ✓), have file:line references (structure compliant ✓), but the referenced file:line does not actually contain what it claims.

### System Relationship of the Eight Mechanisms

```
                    Defense Depth
   Input Layer      Execution Layer      Output Layer        Memory Layer
  inject-project    edit-guard           completion-gate     error-dna
  knowledge         (Read-before         (false-completion   (error memory)
  (session init:    -Edit mandatory)     termination)
   rules + errors                                                   flywheel
   + last snapshot)                     privacy-gate         (event closed loop)
                    pretool-rule-        (leak prevention)
                    anchor                                       sublimation
                    (anti-drift          permission-gate      (experience
                     injection)          (random verification  elevation)
                                          code approval)
                    context-guard
                    (tiered context
                     blocking)
```

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

**Not a single mechanism relies on "the model should remember"** — every one uses shell scripts, the filesystem, and exit codes for mechanical guarantees. This is what distinguishes Carror OS from other prompt frameworks: **it does not trust AI's will, only the system's constraints.**

---

## Part 3: Comprehensive Evaluation

### What It Is

**An AI-native developer operating system.** Not a collection of prompt templates. Not an enhanced .cursorrules. Not AI workflow scripts. It is a **complete operating system** with a kernel, protection layers, memory systems, and governance mechanisms that can run on multiple AI platforms — except it does not run traditional programs; it runs AI development behavior.

### What Real Problem It Solves

The core points of failure in AI-assisted development are three:
- **AI cannot be trusted**: Says it is done but is not. References non-existent code. Gets by with "it should be fine"
- **AI forgets**: Forgets rules in new sessions. Rules decay in long conversations. Makes the same mistake eight times
- **AI leaks secrets**: Reads .env. Passes plaintext tokens in command line. Keys end up in code repositories

Carror OS's solution to these three problems is not "write stricter prompts" but **building mechanical defenses at the system layer**:
- AI cannot be trusted → completion-gate four-layer verification, exit 2 cannot be bypassed
- AI forgets → error-dna cross-session memory, pretool-rule-anchor periodic re-injection
- AI leaks secrets → privacy-gate + permission-gate random verification code, shell-layer interception

### Technical Nature: Dual-Track Architecture

- **Upper track (prompt layer)**: AGENTS.md specifications / iron law system / anti-pattern checklist / compact_inject layered injection. Function: tells AI what it should do
- **Lower track (shell mechanical layer)**: 32 hooks / harness.yaml unified configuration / .omc/state/ persistent state. Function: regardless of what AI wants, forces it to comply

The upper track handles "quality under normal conditions." The lower track handles "safety under extreme conditions." Most frameworks only have the upper track. Carror OS has both, and the lower track is genuine mechanical execution — 32 shell scripts that do not pass through the model's will.

### Originality

1. **Atomic evidence consumption**: completion-gate uses `mv` atomic operation to consume evidence files — the same evidence can only be consumed once by one process. Solves "AI passing with old evidence repeatedly"
2. **Random verification code approval**: permission-gate generates random hex codes that only appear on the user's terminal. AI cannot predict them. Fundamentally solves "AI approving itself"
3. **Error DNA**: Structures every bash failure, aggregates across sessions using MD5 signatures. Fundamentally solves AI's "amnesia" problem
4. **Systematized soft-language ban**: "It should be fine / basically done / theoretically feasible" are systematically identified, named, and linked to mechanical blocking
5. **Knowledge sublimation path**: claude-next.md → hits/age triggers sublimation detection → human review → kernel.md. A knowledge evolution system

### Engineering Maturity

```
Research Prototype    Engineering Prototype    Usable Product    Phenomenal Product
   │                       │                       │                   │
   │                       │                    Carror OS               │
   │                       │              (One month production use)    │
```

Has passed the "engineering prototype" stage. Evidence: Running in production for one month on a real project; 32 hooks through multiple fix rounds (R16, R18, R24, R27...); error-dna has multi-generational archive logic; flywheel.log has real data accumulation; OMA has concurrent lock management, interface version locking, and degradation strategies.

### Real Boundaries

**Limitation 1: Mechanical protection layer is bound to Claude Code**. The most important protections among the 32 hooks depend on Claude Code's PreToolUse/PostToolUse hook mechanism. On OpenCode/Cursor/Codex, these hooks do not trigger. Protection degrades to prompt-layer constraints only.

**Limitation 2: Quantitative verification data is still internal**. Flywheel logs are accumulating, but there is no public "with/without Carror OS" controlled experiment data yet.

### Final Characterization

**Carror OS is currently the most engineering-complete dual-track (prompt layer + mechanical layer) AI governance system built by an individual.**

Its value is not in the ideas — many people are working on AI governance at the conceptual level. Its value is in **implementation density**: one person, three months, turned the complete chain from "iron law constraints" through "mechanical protection" through "cross-session memory" through "knowledge evolution" through "concurrent development orchestration" into actually running code.

Among prompt-layer solutions, it is the ceiling. In the entire AI governance field, it is a **personal work with a unique technical perspective**, several of whose mechanisms (atomic evidence consumption, random verification code approval, Error DNA) possess genuine originality.

What it lacks now is not technical depth, but **conditions for wider adoption**: user guidance documentation, independent verification data, and community.

**When these three conditions are met, it deserves to be taken seriously.**

### Its Real Position Among Alternatives

| Solution | Type | Limitation |
|-----------|------|-----------|
| .cursorrules templates | Static rules | No mechanical execution, no memory, no governance |
| Various prompt frameworks | Prompt-layer constraints | Depends on model compliance |
| NeMo Guardrails | Code-layer interception | System is strong but not designed for individual developers |
| Constitutional AI | Training layer | Users cannot self-deploy |
| **Carror OS** | **Prompt layer + mechanical hook layer dual-track** | **Designed for individual developers, cross-session memory, concurrent orchestration, knowledge evolution** |

In the niche of "AI governance for individual developers": **Carror OS currently has no rivals.** Not because it is perfect, but because **no one has seriously pursued this direction.** Everyone is working on making AI stronger. No one is working on **making the people who use AI safer.**

### Real Value Density

Value is not evenly distributed across all features. The highest value belongs to these three groups:
1. **completion-gate**: Solves "false completion" — the most frequent loss-of-control scenario in AI usage. This one mechanism is worth half the installation cost of the entire framework
2. **privacy-gate + permission-gate**: Solves "leaks" and "dangerous commands" — the consequences are most severe. The random verification code is a truly original design
3. **error-dna + inject-project-knowledge**: Solves "AI amnesia" — the most mentally draining persistent problem. Cross-session memory makes "stepping in the same hole five times" a thing of the past

The remaining mechanisms are enhancements. These three groups are the **bottom line.**

### What It Can and Cannot Deliver

**What it delivers:**
- Real reduction in mental burden (85% of mechanisms run silently)
- Institutional trust replacing personal trust (system has mechanical defenses at critical points)
- Cross-session memory of mistakes (error-dna remembers the pitfalls)
- Amplified individual productivity (OMA system)

**What it cannot deliver:**
- Cannot make AI trustworthy (defenses are built on the assumption that AI is untrustworthy)
- Cannot replace judgment (the system replaces monitoring cost, not thinking cost)
- Protection degrades on OpenCode
- Still growing (one month in production; documentation is still written for the author)

### One Final Honest Sentence

> **After reading its full source code, my assessment changed. Not because it convinced me, but because code does not lie.**

### Future Engineering Directions

The system is not too complex — the packaging work is still in progress. The three-tier design (Basic/Advanced/Mechanism Toggles) is correct. Remaining engineering tasks:
1. Default value calibration (which mechanisms are on by default in Basic mode)
2. Advanced documentation information architecture (guidance path from zero to understanding)
3. False-positive rate tuning (user experience when triggers fire but the user does not understand)
