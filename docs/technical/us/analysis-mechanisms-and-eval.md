[ARCHIVED v6.2.1 — Historical document. Referenced hooks/scripts/skills may no longer exist. See story-10.]

     1|# Carror OS: Mechanism Analysis and Comprehensive Evaluation
     2|
     3|> Compiled from: material-3.md, Carror-OS-mechanisms.md, conclusion-1.md, conclusion-7.md, aggregated-6.md, next-steps.md
     4|
     5|---
     6|
     7|## Part 1: 5 Guardrails That Actually Work
     8|
     9|Many people believe AI errors can be solved with better prompts. But anyone who has actually used AI to write code, modify files, and run tasks knows: **a reminder is not a constraint.**
    10|
    11|You can tell AI "do not fabricate," "verify before completing," "do not read sensitive files." It may agree. But by turn 20, under high context, near the end of a task, it will still forget, skip, and confidently do the wrong thing.
    12|
    13|Carror OS does not bet on AI remembering. It does something different: **turns critical rules into guardrails that actually work.**
    14|
    15|### Guardrail 1: Completion Gate — No More Empty "It Is Done"
    16|
    17|AI's most common and most frustrating error is not inability. It is **not finishing, but claiming it is done.** The worst part is not the mistake. It is that AI says "I have completed it" in a tone that sounds entirely convincing. The subsequent checking, verification, and rework all fall on you.
    18|
    19|Carror OS's first guardrail: **AI cannot declare completion with a single sentence. It must submit evidence.**
    20|
    21|When AI tries to mark a task as completed, the system asks:
    22|- Were the tests run?
    23|- Does the output match expectations?
    24|- Is there structured verification evidence?
    25|
    26|If not, the system stops it.
    27|
    28|The most important thing here is not the word "verification." It is that **the right to declare completion has been taken away.** Before, "completion" was declared by AI itself. Now, "completion" is granted by the system based on evidence.
    29|
    30|### Guardrail 2: Rule Anchor — When AI Forgets, the System Remembers
    31|
    32|AI "forgets" rules set early in long conversations — this is not a bug, it is a physical property of the attention mechanism. Turn 8 is fine. Turn 12 starts slipping. By turn 20, it writes as if it never heard those rules.
    33|
    34|Carror OS places rules **before the action.** Before AI writes a file, the system re-injects the critical rules. The key point: **Carror OS does not rely on AI remembering by itself.** It places the rules in front of AI before the critical action happens. You do not need to manually re-explain at turn 20. The system does it for you.
    35|
    36|### Guardrail 3: Privacy Gate — What It Should Not Read, It Simply Cannot Read
    37|
    38|Many people's first real moment of AI security awareness does not come from the news. It comes from a specific moment. Like mentioning `.env` in a conversation, and suddenly feeling a chill.
    39|
    40|Carror OS's approach to this problem is simple: **Sensitive files should not be left to AI's discretion. They should be directly forbidden.** If AI tries to read `.env`, key files, or sensitive configuration, the system intercepts it. The difference is fundamental. Before: "I hope AI understands what it should and should not read." Now: "Even if it wants to read, it cannot." Real security is putting some things where AI can never reach.
    41|
    42|### Guardrail 4: Dangerous Action Gate — Dangerous Actions Cannot Be Executed Just Because AI Wants To
    43|
    44|Another common AI problem is not misunderstanding, but **acting too quickly.** It finds a seemingly reasonable action path and just does it: git add, commit, delete files, run migrations, modify databases, execute production commands. The problem is that **high-risk actions should not happen just because AI thinks they are reasonable.** Because once they happen, the consequences are real. You bear them.
    45|
    46|So Carror OS's fourth guardrail is clear: **Dangerous actions must return to human control.** AI can propose, prepare commands, explain why. But it cannot cross that last door itself.
    47|
    48|### Guardrail 5: Project Memory — The Same Mistake Should Not Require a Fifth Explanation
    49|
    50|The most draining thing about AI collaboration is not the big mistake. It is **the same mistake, over and over again.** You just explained that this type error was previously fixed, that this directory must not be touched, that this interface cannot have its signature changed due to historical reasons. AI understands in the moment. Next session, it is a brand new day. You re-explain. It re-apologizes. You re-consume.
    51|
    52|Carror OS's fifth guardrail: **Move project lessons and error memory out of your brain and into the system as injectable knowledge.** Before each new session, the system automatically injects historical errors, unresolved issues, and frequently encountered pitfalls into AI. You no longer need to be the "memory relay station" every time. The project finally begins to have **accumulated collaborative memory.**
    53|
    54|### The Fundamental Difference: Prompt vs Gate
    55|
    56|| Dimension | Prompt | Gate |
    57||-----------|--------|------|
    58|| Logic | I tell you what to do; please try your best | If conditions are not met, you cannot proceed |
    59|| Nature | Suggestion | Permission to proceed |
    60|| Dependency | Model stays stable at all times | System makes judgments at critical points |
    61|| Risk | Can be forgotten, diluted, bypassed | As long as the rule exists, it takes effect |
    62|
    63|**A Prompt is a reminder. A Gate is permission control. Carror OS does not remind AI to do things correctly — it decides whether AI can proceed before it does something wrong.**
    64|
    65|---
    66|
    67|## Part 2: Eight High-Value Mechanism Deep Dives
    68|
    69|Based on full source code reading of 32 hook scripts, 5 compact_inject files, kernel.md, anti-patterns.md, and harness.yaml.
    70|
    71|### Mechanism 1: Completion Gate — Mechanical Termination of False Completion
    72|
    73|**File**: `completion-gate.sh` (PreToolUse:TaskUpdate)
    74|
    75|Four-layer verification chain:
    76|1. **Evidence file existence check**: `.omc/state/.completion-evidence-YYYYMMDD` must exist. Missing → exit 2 hard block
    77|2. **5-minute freshness check**: Evidence file must have been written within 5 minutes. Expired → exit 2 (prevents reuse of old evidence)
    78|3. **Atomic consumption (prevents concurrent reuse)**: `mv` evidence file → `.consumed.PID`. Second process mv fails → exit 2. This is a UNIX atomic operation — even if two AI instances complete simultaneously, both cannot pass
    79|4. **Semantic verification (formal compliance ≠ content truth)**: Evidence must contain ≥20 characters of actual description, the "VERIFIED" keyword, and one of the structured formats
    80|
    81|**The fourth layer is the most critical**: The comment reads `R27` — the product of the 27th fix. AI can write an evidence file containing the word "VERIFIED," but the content might be "VERIFIED: The feature should be fine now" — the fourth layer specifically intercepts this kind of semantic cheating.
    82|
    83|Hidden A→B→A automatic trigger: When evidence content contains words like "verification/benchmark/pass rate," the hook **automatically generates an A→B→A handoff file**, writing the handoff content so that after the B terminal starts, executing `cat` can begin verification immediately.
    84|
    85|### Mechanism 2: Error DNA — Cross-Session Error Memory
    86|
    87|**File**: `error-dna.sh` (PostToolUse:Bash) + `stop-drain.sh` (Stop) + `inject-project-knowledge.sh` (SessionStart)
    88|
    89|Three hooks form a complete error memory loop:
    90|- **Real-time layer**: Every Bash exit_code ≠ 0 → immediately structured recording. Fields: ts/signature/cmd/exit_code/error_type/message/session_id. Credential sanitization: --password/--token/--secret → *** replacement
    91|- **Fallback layer**: At session end, scan transcript.jsonl to capture tool_results where is_error=true
    92|- **Injection layer**: At each new session start, AI sees error memory as its first input
    93|
    94|Each error generates a signature (MD5 of first 16 characters of cmd). Same errors aggregate across sessions. `status: "reopened"` = was fixed but reappeared.
    95|
    96|### Mechanism 3: Context Guard — Tiered Response to Context Crises
    97|
    98|**File**: `context-guard.sh` (PreToolUse:Edit|Write)
    99|
   100|Precise read/write separation: Only hard-blocks write tools (Edit/Write), preserves Read/Grep/Bash diagnostic channels. The logic is "reading is diagnosis, writing is destruction." At 80% context, Edit/Write → hard block (exit 2) to prevent hallucination-driven code writes; Read/Grep/Bash → warn only, preserving diagnostic capability.
   101|
   102|Escape hatch: Users can `touch .omc/state/context-force-override` to bypass the block, but only once. It auto-deletes after use.
   103|
   104|### Mechanism 4: Rule Anchor — Active Injection to Prevent Long-Conversation Drift
   105|
   106|**File**: `pretool-rule-anchor.sh` (PreToolUse:Write)
   107|
   108|Dual trigger mechanism:
   109|- **Regular trigger**: At turns 15, 20, 25..., inject rule anchors before AI writes files
   110|- **Drift-word trigger**: Immediately responds when user says "fix this while you are at it" — prompts the scope freeze rule
   111|
   112|### Mechanism 5: Flywheel — Closed Loop from Error to System Improvement
   113|
   114|**File**: `skill-flywheel.sh` + `flywheel-report.sh`
   115|
   116|Two-layer collection architecture:
   117|- AI layer (Phase 1, best-effort): lx-* skills write to buffer during execution
   118|- Shell layer (Phase 2, mechanical guarantee): skill-flywheel.sh flushes buffer → flywheel.log on each Stop event
   119|
   120|P0 alert full-chain response: P0 events > 5 within 30 days and not ack'ed → terminal output + persistent report + desktop notification + AI context injection.
   121|
   122|### Mechanism 6: Knowledge Sublimation — Automatic Experience Elevation
   123|
   124|**File**: `inject-project-knowledge.sh`
   125|
   126|claude-next.md (temporary experience) → three trigger signals (count ≥20 items / any item ≥10 days old / any item triggered ≥5 times) → sublimation review → kernel.md (iron law) or `.claude/compact_inject/*.md` (specification)
   127|
   128|### Mechanism 7: Edit Guard + Read Tracker — Mandatory Code Modification Traceability
   129|
   130|**File**: `edit-guard.sh` (PreToolUse:Edit) + `posttool-write-cite.sh`
   131|
   132|Every time a file is Read, the path is written to read-tracker.txt. Before every Edit, the system checks if that file path is in read-tracker. No Read → exit 2. Constitutional constraints tell the model it "should" read before editing, but cannot guarantee the model does it. Edit Guard turns "should" into "must."
   133|
   134|### Mechanism 8: Anti-Patterns Semantic Cheating Classification
   135|
   136|**File**: `anti-patterns.md`
   137|
   138|The most valuable classification is H1: Semantic fabrication — formal compliance masks semantic cheating. AI can have an evidence file (file exists ✓), contain the word "VERIFIED" (format compliant ✓), have file:line references (structure compliant ✓), but the referenced file:line does not actually contain what it claims.
   139|
   140|### System Relationship of the Eight Mechanisms
   141|
   142|```
   143|                    Defense Depth
   144|   Input Layer      Execution Layer      Output Layer        Memory Layer
   145|  inject-project    edit-guard           completion-gate     error-dna
   146|  knowledge         (Read-before         (false-completion   (error memory)
   147|  (session init:    -Edit mandatory)     termination)
   148|   rules + errors                                                   flywheel
   149|   + last snapshot)                     privacy-gate         (event closed loop)
   150|                    pretool-rule-        (leak prevention)
   151|                    anchor                                       sublimation
   152|                    (anti-drift          permission-gate      (experience
   153|                     injection)          (random verification  elevation)
   154|                                          code approval)
   155|                    context-guard
   156|                    (tiered context
   157|                     blocking)
   158|```
   159|
   160|| Node | Mechanism | Enforcement Method |
   161||------|-----------|-------------------|
   162|| Forgetting rules at session start | inject-project-knowledge | SessionStart automatic injection |
   163|| Editing code without reading first | edit-guard | No Read record → exit 2 |
   164|| Rules forgotten in long conversations | pretool-rule-anchor | Re-inject before Nth turn file write |
   165|| Continuing to write when context is full | context-guard | Write → exit 2, Read → pass |
   166|| Marking task done without verification | completion-gate | No evidence file → exit 2 |
   167|| Reading/writing sensitive files | privacy-gate | Filename match → exit 2 |
   168|| Executing dangerous commands | permission-gate | Random verification code AI cannot self-generate |
   169|| Errors disappearing after session ends | error-dna + stop-drain | Cross-session persistence, injected in new session |
   170|| High-frequency errors going unnoticed | flywheel | 30-day aggregation + desktop notification |
   171|| Temporary experiences not solidified | sublimation | hits/age triggers sublimation reminder |
   172|
   173|**Not a single mechanism relies on "the model should remember"** — every one uses shell scripts, the filesystem, and exit codes for mechanical guarantees. This is what distinguishes Carror OS from other prompt frameworks: **it does not trust AI's will, only the system's constraints.**
   174|
   175|---
   176|
   177|## Part 3: Comprehensive Evaluation
   178|
   179|### What It Is
   180|
   181|**An AI-native developer operating system.** Not a collection of prompt templates. Not an enhanced .cursorrules. Not AI workflow scripts. It is a **complete operating system** with a kernel, protection layers, memory systems, and governance mechanisms that can run on multiple AI platforms — except it does not run traditional programs; it runs AI development behavior.
   182|
   183|### What Real Problem It Solves
   184|
   185|The core points of failure in AI-assisted development are three:
   186|- **AI cannot be trusted**: Says it is done but is not. References non-existent code. Gets by with "it should be fine"
   187|- **AI forgets**: Forgets rules in new sessions. Rules decay in long conversations. Makes the same mistake eight times
   188|- **AI leaks secrets**: Reads .env. Passes plaintext tokens in command line. Keys end up in code repositories
   189|
   190|Carror OS's solution to these three problems is not "write stricter prompts" but **building mechanical defenses at the system layer**:
   191|- AI cannot be trusted → completion-gate four-layer verification, exit 2 cannot be bypassed
   192|- AI forgets → error-dna cross-session memory, pretool-rule-anchor periodic re-injection
   193|- AI leaks secrets → privacy-gate + permission-gate random verification code, shell-layer interception
   194|
   195|### Technical Nature: Dual-Track Architecture
   196|
   197|- **Upper track (prompt layer)**: AGENTS.md specifications / iron law system / anti-pattern checklist / compact_inject layered injection. Function: tells AI what it should do
   198|- **Lower track (shell mechanical layer)**: 32 hooks / harness.yaml unified configuration / .omc/state/ persistent state. Function: regardless of what AI wants, forces it to comply
   199|
   200|The upper track handles "quality under normal conditions." The lower track handles "safety under extreme conditions." Most frameworks only have the upper track. Carror OS has both, and the lower track is genuine mechanical execution — 32 shell scripts that do not pass through the model's will.
   201|
   202|### Originality
   203|
   204|1. **Atomic evidence consumption**: completion-gate uses `mv` atomic operation to consume evidence files — the same evidence can only be consumed once by one process. Solves "AI passing with old evidence repeatedly"
   205|2. **Random verification code approval**: permission-gate generates random hex codes that only appear on the user's terminal. AI cannot predict them. Fundamentally solves "AI approving itself"
   206|3. **Error DNA**: Structures every bash failure, aggregates across sessions using MD5 signatures. Fundamentally solves AI's "amnesia" problem
   207|4. **Systematized soft-language ban**: "It should be fine / basically done / theoretically feasible" are systematically identified, named, and linked to mechanical blocking
   208|5. **Knowledge sublimation path**: claude-next.md → hits/age triggers sublimation detection → human review → kernel.md. A knowledge evolution system
   209|
   210|### Engineering Maturity
   211|
   212|```
   213|Research Prototype    Engineering Prototype    Usable Product    Phenomenal Product
   214|   │                       │                       │                   │
   215|   │                       │                    Carror OS               │
   216|   │                       │              (One month production use)    │
   217|```
   218|
   219|Has passed the "engineering prototype" stage. Evidence: Running in production for one month on a real project; 32 hooks through multiple fix rounds (R16, R18, R24, R27...); error-dna has multi-generational archive logic; flywheel.log has real data accumulation; OMA has concurrent lock management, interface version locking, and degradation strategies.
   220|
   221|### Real Boundaries
   222|
   223|**Limitation 1: Mechanical protection layer is bound to Claude Code**. The most important protections among the 32 hooks depend on Claude Code's PreToolUse/PostToolUse hook mechanism. On OpenCode/Cursor/Codex, these hooks do not trigger. Protection degrades to prompt-layer constraints only.
   224|
   225|**Limitation 2: Quantitative verification data is still internal**. Flywheel logs are accumulating, but there is no public "with/without Carror OS" controlled experiment data yet.
   226|
   227|### Final Characterization
   228|
   229|**Carror OS is currently the most engineering-complete dual-track (prompt layer + mechanical layer) AI governance system built by an individual.**
   230|
   231|Its value is not in the ideas — many people are working on AI governance at the conceptual level. Its value is in **implementation density**: one person, three months, turned the complete chain from "iron law constraints" through "mechanical protection" through "cross-session memory" through "knowledge evolution" through "concurrent development orchestration" into actually running code.
   232|
   233|Among prompt-layer solutions, it is the ceiling. In the entire AI governance field, it is a **personal work with a unique technical perspective**, several of whose mechanisms (atomic evidence consumption, random verification code approval, Error DNA) possess genuine originality.
   234|
   235|What it lacks now is not technical depth, but **conditions for wider adoption**: user guidance documentation, independent verification data, and community.
   236|
   237|**When these three conditions are met, it deserves to be taken seriously.**
   238|
   239|### Its Real Position Among Alternatives
   240|
   241|| Solution | Type | Limitation |
   242||-----------|------|-----------|
   243|| .cursorrules templates | Static rules | No mechanical execution, no memory, no governance |
   244|| Various prompt frameworks | Prompt-layer constraints | Depends on model compliance |
   245|| NeMo Guardrails | Code-layer interception | System is strong but not designed for individual developers |
   246|| Constitutional AI | Training layer | Users cannot self-deploy |
   247|| **Carror OS** | **Prompt layer + mechanical hook layer dual-track** | **Designed for individual developers, cross-session memory, concurrent orchestration, knowledge evolution** |
   248|
   249|In the niche of "AI governance for individual developers": **Carror OS currently has no rivals.** Not because it is perfect, but because **no one has seriously pursued this direction.** Everyone is working on making AI stronger. No one is working on **making the people who use AI safer.**
   250|
   251|### Real Value Density
   252|
   253|Value is not evenly distributed across all features. The highest value belongs to these three groups:
   254|1. **completion-gate**: Solves "false completion" — the most frequent loss-of-control scenario in AI usage. This one mechanism is worth half the installation cost of the entire framework
   255|2. **privacy-gate + permission-gate**: Solves "leaks" and "dangerous commands" — the consequences are most severe. The random verification code is a truly original design
   256|3. **error-dna + inject-project-knowledge**: Solves "AI amnesia" — the most mentally draining persistent problem. Cross-session memory makes "stepping in the same hole five times" a thing of the past
   257|
   258|The remaining mechanisms are enhancements. These three groups are the **bottom line.**
   259|
   260|### What It Can and Cannot Deliver
   261|
   262|**What it delivers:**
   263|- Real reduction in mental burden (85% of mechanisms run silently)
   264|- Institutional trust replacing personal trust (system has mechanical defenses at critical points)
   265|- Cross-session memory of mistakes (error-dna remembers the pitfalls)
   266|- Amplified individual productivity (OMA system)
   267|
   268|**What it cannot deliver:**
   269|- Cannot make AI trustworthy (defenses are built on the assumption that AI is untrustworthy)
   270|- Cannot replace judgment (the system replaces monitoring cost, not thinking cost)
   271|- Protection degrades on OpenCode
   272|- Still growing (one month in production; documentation is still written for the author)
   273|
   274|### One Final Honest Sentence
   275|
   276|> **After reading its full source code, my assessment changed. Not because it convinced me, but because code does not lie.**
   277|
   278|### Future Engineering Directions
   279|
   280|The system is not too complex — the packaging work is still in progress. The three-tier design (Basic/Advanced/Mechanism Toggles) is correct. Remaining engineering tasks:
   281|1. Default value calibration (which mechanisms are on by default in Basic mode)
   282|2. Advanced documentation information architecture (guidance path from zero to understanding)
   283|3. False-positive rate tuning (user experience when triggers fire but the user does not understand)
   284|