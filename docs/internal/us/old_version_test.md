# Carror OS v6.1.7-stable Feature Audit Report

**Audit Date**: 2026-05-06
**Audit Scope**: All feature claims in architecture-review.md, cross-referenced against actual source code in `source/` directory
**Audit Method**: Read each source file, count lines/files, compare feature claims against code implementation
**Evidence Levels**: L1=End-to-end verification / L2=Code verification / L3=File existence / L4=Documentation claim only

---

## Overview

| Category | Count | Description |
|---:|---:|---|
| ✅ | 7 | Feature claims consistent with implementation (true) |
| ⚠️ | 4 | Partially true but exaggerated |
| ❌ | 3 | False (claims significantly deviate from implementation) |
| 🔁 | 2 | Redundant (actual value double-counted or insufficient gain) |

---

## I. ❌ False Items (Claims Significantly Deviate from Implementation)

### V-1: Hook Count Claimed "24," Actual 25 Files, ~20 Effective Hooks

**Document Claim** (architecture-review.md:29):
> "24 Bash Hooks totaling less than 1000 lines of code"

**Actual Situation** [Verified: `ls hooks/ | wc -l -> 26`, `wc -l hooks/*.sh -> 2768 lines`]:
- Hook directory contains **26** `.sh` files, of which `harness_config.sh` is a shared configuration library (sourced by all hooks), not an independent hook
- Effective hooks: approximately **25** (excluding config), not 24
- Total lines: **2768** lines, not "less than 1000" -- nearly 3x the claimed amount

**Severity**: Medium. Small count deviation, but line count exaggerated 3x, making the core selling point of "extremely lightweight" clearly inaccurate. Additionally, `hooks_enabled` in harness.yaml has multiple hooks defaulting to `false` (e.g., `plan_gate: false`, `posttool_read_cite: false`), meaning even fewer hooks are actually loaded at runtime.

---

### V-2: context_monitor.py Claimed to "Read Token Data from System Level" -- Actually Depends on External JSON File

**Document Claim** (architecture-review.md:172):
> "context-guard.sh (the 24th hook) reads token-tracking data directly from the system level"
> "When ctx% >= 80%, throws Exit 2 and locks the system"

**Actual Situation** [Verified: context_monitor.py:15-26]:
```python
state_file = root / ".omc" / "state" / "token-tracking-index.json"
usage = 0
limit = 200000
if state_file.exists():
    data = json.load(f)
    usage = data.get("usage", 0)
```
- The script does **not** read token counts from any system level, only reads `.omc/state/token-tracking-index.json`
- This file **must** be written by an external mechanism -- the source code contains no code that writes to this file
- If this file does not exist, `usage` defaults to 0, `ratio = 0/200000 = 0`, and Context Guard **never triggers**
- The "physical block" claim relies on a state file that is never created

**Severity**: High. This is the core supporting feature for the [H] Hallucination Prevention score of 9.5 and [T] Task Continuity score of 9.8, yet the feature is silently non-functional in default installation state.

---

### V-3: lx-mirror "Preliminary Dehydration Pipeline" -- Actually Regex Extraction, Not AST Analysis

**Document Claim** (architecture-review.md:50):
> "Uses mirror_scan.py to forcibly dehydrate and compress the codebase into an AST skeleton map (Reality Map)"

**Actual Situation** [Verified: mirror_scan.py:29-76]:
```python
LANG_PATTERNS = {
    "go": (r"\.go$", r"^func\s+(\w+)\s*\(([^)]*)\)\s*(.*?)\{", ...),
    ...
}
for m in re.finditer(func_pattern, content, re.MULTILINE):
```
- Implementation is entirely based on **regex matching**, with no AST parsing libraries (no `ast`, `tree-sitter`, `go/parser`, etc.)
- Regex matching will inevitably produce false positives/false negatives in scenarios with nested functions, generics, decorators, etc.
- Describing this as "AST skeleton map" is a misleading representation of the implementation technology -- regex extraction != AST analysis
- SKILL.md itself describes this more accurately (as "scanning"), but architecture-review.md upgrades the technical specification with marketing language

**Severity**: Medium-High. Misleads user expectations about tool accuracy, especially for large projects or dynamic languages (JS/TS) where reliability is far below what "AST analysis" implies.

---

## II. ⚠️ Partially True but Exaggerated

### P-1: lx-varlock's "Bidirectional Transparent Masking" Description Is Accurate, But privacy-gate.sh's "Native Read Physical Cutoff" Can Be Bypassed

**Document Claim**:
> "Not only is native reading physically cut off... achieving military-grade data protection standards"

**Actual Situation** [Verified: privacy-gate.sh:29-34]:
```bash
if echo "$CHECK_PATH" | grep -iE '\.env|\.pem|\.key|id_rsa|credentials\.json|secret\.ya?ml|auth\.json' > /dev/null
```
- Matching is based on **filename patterns**; if sensitive files are named `config.json`, `settings.yaml`, `.env.production` (without `.env` in the name), etc., they pass through directly
- `varlock.py` itself is implemented completely and correctly [Verified: varlock.py:35-48], the bidirectional mask/restore mechanism is reliable
- However, "military-grade" description is a clear gap from the simple grep-based filename filter implementation

**Actual Rating**: L3-level protection (filename blacklist), not the 10.0/10 level implied in the architecture score

---

### P-2: subagent_reviewer.py's "A/B Terminal Blind Review" Description Overstated -- Actually Constructs a Prompt for the Main AI to Call the Task Tool

**Document Claim** (architecture-review.md:53):
> "Introducing subagent_reviewer, forcibly launching a clean-context sub-agent"

**Actual Situation** [Verified: subagent_reviewer.py:30-39]:
```python
instruction = {
    "status": "requires_subagent_blind_review",
    "action": "Please immediately use the `Task` tool to start blind review",
    "subagent_type": "general",
    "prompt": system_prompt,
}
print(json.dumps(instruction, ensure_ascii=False, indent=2))
```
- The script does **not** directly launch any sub-agent; it only prints a JSON instruction for the main AI to see
- Whether a "clean-context sub-agent" is actually launched depends entirely on whether the main AI follows the `action` instruction in that JSON
- If the main AI's context is already polluted, its behavior when calling the `Task` tool may also be polluted
- The strong description of "physically stripping self-review authority" has a fundamental gap from the implementation of "printing a JSON hoping the AI complies"

**Actual Rating**: Soft constraint, not physical enforcement. Works when main AI context quality is normal; reliability decreases in late-stage long conversations (precisely when blind review is most needed).

---

### P-3: oma_lock_manager.py's "Write Safety" Is Effective, But lx-oma SKILL.md's Promise of "5 Terminal Concurrency" Lacks Mechanical Support

**Document Claim** (architecture-review.md:51):
> "With the kernel-level OMA concurrency lock, you can launch 5 terminals simultaneously... each developing in clean contexts with zero token pollution"

**Actual Situation** [Verified: oma_lock_manager.py:23-50, lx-oma SKILL.md:full text]:
- `oma_lock_manager.py`'s file lock mechanism is correctly implemented, with atomic lock + exponential backoff + automatic timeout release [L2 verified]
- However, **the lx-oma Skill itself does not call oma_lock_manager.py** -- the Skill only generates `rpe/feat-X/` directory structure and prints "OMA file lock ready"
- There is **no code-level integration** between the lock mechanism and the actual Skill workflow: lx-oma/SKILL.md contains no instructions for calling the lock
- The "5 terminals with zero token pollution" claim is true for directory isolation; but the claimed "automatic concurrency lock queuing" actually requires each terminal's AI to proactively call the lock -- a soft convention

**Actual Rating**: Directory isolation is real and effective; automatic lock queuing requires manual cooperation; the "automatic" description is exaggerated.

---

### P-4: [M] Migration Dimension Counted Twice in Scoring Table

**Document Claim** (architecture-review.md:98-113, scoring table rows 5 and 10):
| Dimension | v6.1.7 | v6.1.3 |
|---|---:|---:|
| [M] Migration (Migration Capability) | 10.0 | 10.0 |
| [M] Migration (Migration Capability) | 9.6 | 10.0 |

- The **[M] dimension appears twice** in the table, describing different content (hot-update vs. cross-platform operation)
- This means the total score of 136.7/140 across 14 dimensions is actually based on **2 M dimensions**, not 14 independent dimensions
- If deduplicated to 13 dimensions, the conversion logic breaks, and the high score basis of 126.9/130 needs recalculation
- Two **[Z] UX Intelligence dimensions also appear twice** (rows 6 and 13)

**Actual Rating**: Structural error in the scoring system; total score credibility is questionable.

---

## III. 🔁 Redundant Items (Insufficient Actual Gain)

### R-1: lx-status Dashboard Script Depends on State Files; Initial State Has No Data, Low Presence

**Claimed Value**:
> "/lx-status dashboard and various [Context Guard trigger] proactive interceptions greatly enhance the system's interactive feel" ([Z] dimension score 9.3)

**Actual Situation** [Verified: lx-status/SKILL.md:34-43]:
- `lx-status` calls `carror_dashboard.py`
- `carror_dashboard.py` reads state files under `.omc/state/`
- In a new installation, these files do **not** exist, and the degradation message reads: "System is in initial state, no execution records yet"
- Usage frequency is limited: only valuable after long-term high-intensity use when state files accumulate
- The functionality itself is fine, but occupying an entire scoring dimension at 9.3 lacks justification

**Suggestion**: Remove from independent scoring dimension; merge into the overall [Z] UX Intelligence description.

---

### R-2: "Three-Stage Rocket" Installation Concept Disconnected from Actual Install Process; Cognitive Load Not "Reduced to Zero"

**Claimed Value**:
> "Three-Stage Rocket installation model... reducing new user cognitive load to zero" ([S] Simplicity 9.7)

**Actual Situation** [Verified: file structure]:
- There are **three** install scripts: `harness-kit-install.sh`, `install.sh`, `package.sh`
- The `lx-skills` directory also contains `.claude/profiles/merge-profile.sh`, multiple language harness.yaml files
- Users face 3 install scripts + 4 language profiles + Base/Enhanced choice; cognitive load is **not** "zero"
- "Three-Stage Rocket" is a reasonable layered design, but "reduced to zero" is an exaggerated claim that doesn't match reality

**Suggestion**: Change to "significantly reduces initial configuration cost," avoid absolute expressions.

---

## IV. ✅ Core Features Consistent with Implementation (For Record)

| Feature | Evidence Source | Rating |
|---|---|---|
| context-guard.sh Exit 2 blocking logic | context-guard.sh:33-38 | [L2] Code real, but trigger precondition invalid (see V-2) |
| privacy-gate.sh filename blacklist blocking | privacy-gate.sh:30-34 | [L2] Real, but limited protection scope |
| varlock.py bidirectional mask/restore | varlock.py:36-48 | [L2] Real, implementation complete |
| oma_lock_manager.py atomic file lock | oma_lock_manager.py:30 `os.O_CREAT \| os.O_EXCL` | [L2] Real, mechanism reliable |
| lx-oma MECE requirement decomposition + directory scaffolding | lx-oma/SKILL.md:23-56 | [L2] Real, directory isolation effective |
| mirror_scan.py regex scanning + report generation | mirror_scan.py:full | [L2] Real, precision limited (see V-3) |
| subagent_reviewer.py prompt construction | subagent_reviewer.py:21-39 | [L2] Real, enforceability limited (see P-2) |

---

## V. Comprehensive Recommendations

### Immediate Corrections Needed (Architecture Document)

1. **Hook line count**: Change "less than 1000 lines" to "approximately 2768 lines (including configuration library)"
2. **Context Guard trigger precondition**: Add explanation "requires OMC state write mechanism cooperation; silently inactive in default installation; needs verification that token-tracking-index.json is properly maintained"
3. **mirror_scan.py technical description**: Change "AST skeleton map" to "regex scanning skeleton map" to avoid misleading AST parsing implications
4. **Scoring dimension duplication**: Fix scoring table, remove duplicate [M] Migration and [Z] UX Intelligence dimensions, recalculate total score

### Technical Debt for Future Iteration

1. **context_monitor.py data source**: Implement actual token tracking write mechanism (currently token-tracking-index.json has no writer), or clearly document "depends on external agent framework to write state files"
2. **subagent_reviewer.py**: Consider using hook mechanism to force Task invocation, rather than just printing JSON and expecting AI to comply
3. **privacy-gate.sh**: Expand filename blacklist to path content scanning, or increase coverage for common naming patterns like `config.*`, `settings.*`

---

**Audit Conclusion**: The defense mechanisms of harness-kit are fully implemented at the code level with rigorous logic; the core architecture design is credible. Main issues center on documentation exaggeration (line counts, technical precision descriptions) and critical feature chain breaks (Context Guard trigger depends on unimplemented state writes). The lx-skills layer is overall a real and usable engineering methodology package; the lx-mirror AST description is the most misleading statement needing correction.

---

## Second Round Deep Audit Supplement

**New Scan Scope**: Full code of all 25 hooks, harness-kit.ts OpenCode plugin, error-dna.sh, completion-gate.sh, permission-gate.sh, pretool-edit-scope.sh, etc.

---

## VI. ❌ Supplementary False Items

### V-4: error-dna.sh Implementation Incomplete, References Undefined Variable, Cannot Actually Run

**Document Claim** (harness.yaml:103-104, architecture-review.md's "independent memory management"):
> `harness.yaml` has `error_dna: enabled: true`, claiming to record and track error DNA

**Actual Situation** [Verified: error-dna.sh:8]:
```bash
echo "{\"ts\":$(date +%s),\"error_code\":$EXIT_CODE}" >> "$DNA_FILE"
```
- Line 8 uses the `$DNA_FILE` variable, but the entire script has **no code defining or assigning this variable**
- `$DNA_FILE` is an empty string; `>> ""` in bash writes to a file named by empty string in the current directory, with undefined behavior
- `inject-project-knowledge.sh` reads `error-dna.json`, while `harness-kit.ts` writes `error-dna.jsonl` (inconsistent extensions)
- Three pieces of code (error-dna.sh, harness-kit.ts, inject-project-knowledge.sh) use **3 different paths/formats**, data never forms a闭环

**Severity**: High. This hook is completely non-functional in the Claude Code environment. The `error_dna: true` declaration in harness.yaml is a dead configuration.

---

### V-5: permission-gate.sh's "User Approval" Mechanism Has Fundamental Design Flaw -- Marker File Written by AI Itself

**Document Claim** (architecture-review.md:29):
> "Transparent permission application... prohibits popping up permission requests without context"

**Actual Situation** [Verified: permission-gate.sh:77-101, harness-kit.ts:104-139]:
```bash
PERMISSION_MARKER="$STATE_DIR/permission-approved"
# Check if marker file exists...
if [ -f "$PERMISSION_MARKER" ]; then
    # Valid authorization, consume marker file
    rm -f "$PERMISSION_MARKER"
    exit 0
fi
# Block prompt:
echo "Write a one-line reason to proceed:"
echo "  echo 'reason' > $PERMISSION_MARKER"
```
- The release condition is existence of the `permission-approved` file
- But this file is **written by the AI itself** (the block prompt explicitly tells AI to `echo 'reason' > permission-approved`)
- The OpenCode plugin version (harness-kit.ts:104-139) is more aggressive -- directly `throw new Error()` for complete blocking, with no marker file mechanism, behavior inconsistent with the Claude Code version
- This means in the Claude Code version: AI gets "blocked" -> AI writes marker file -> AI unblocks itself. **User never intervenes**
- The documented "user sovereignty" is effectively bypassed by this mechanism

**Severity**: Medium-High. Constitutional Rule #2 "User Sovereignty" is completely circumvented here through AI self-writing marker files.

---

### V-6: completion-gate.sh's Evidence File Also Written by AI, and /tmp Path May Conflict Between Different Terminals

**Document Claim** (AGENTS.md "Evidence Gate" iron rule):
> "Without evidence, forbids saying 'completed/verified'"

**Actual Situation** [Verified: completion-gate.sh:32,80, harness-kit.ts:41-47]:
```bash
EVIDENCE_FILE="/tmp/.completion-evidence-$(date +%Y%m%d)"
# Block prompt tells AI:
echo "2. Execute: echo 'VERIFIED: [specific verification result description]' > $EVIDENCE_FILE"
```
- Release mechanism: AI writes content containing "VERIFIED" to `/tmp/.completion-evidence-YYYYMMDD`
- This is still **AI self-writing evidence files to self-unblock**
- The `/tmp/` path is globally shared; in lx-oma multi-terminal concurrency scenarios, evidence written by Terminal A can pass the check for Terminal B's task
- The 5-minute reuse prevention (writing `CONSUMED`) has race conditions: if two terminals consume concurrently, the second terminal may read a valid file before the first writes `CONSUMED`

**Severity**: Medium. The evidence gate mechanism is correct in principle (force write file + keyword + time window), but AI self-Writing = soft constraint, not hard constraint; concurrent scenarios have race conditions.

---

## VII. ⚠️ Supplementary Exaggerated Items

### P-5: OpenCode Plugin Claims "22 Hook Coverage," Actual Behavior Has Multiple Inconsistencies with Claude Code Version

**Document Claim** (harness-kit.ts:7-10):
> "OpenCode equivalent implementation covering 22 Claude Code hooks: 19 fully aligned through tool.execute.before/after, 3 adapted through message.updated / tui.prompt.append"

**Actual Inconsistencies** [Verified: harness-kit.ts full text compared against source hooks]:

| Feature | Claude Code Hook | OpenCode Plugin Difference |
|---|---|---|
| permission-gate | Checks permission-approved marker file, can be released by writing file | Direct `throw Error` hard block, no release mechanism | Behavior inconsistent |
| lsp-suggest | `exit 2` first block, writes marker to not block again | Not implemented in plugin | Feature missing |
| flywheel-report | Reads `~/.claude/flywheel.log` to inject flywheel report | Only updates timestamp, no report generation | Empty shell |
| auto-snapshot | 318 lines, generates complete session handoff + error memory + ADR | Only writes Todo status, ~20 lines | Severely reduced |
| turn-counter | Injects into AI context (stdout hook) | Writes `console.warn` (debug log, invisible to user) | Visibility lost |
| read-tracker | Records to read-files.log for edit-guard consumption | Records to read-tracker.txt, different path, edit-guard reads wrong file | Chain broken |

**Actual Rating**: OpenCode plugin is a partial alignment implementation; "fully aligned" description is inaccurate, with at least 6 locations having functional degradation or chain breaks.

---

### P-6: posttool-bash-audit.sh Output Format Error -- hookSpecificOutput Field Name Correct but Nesting Level Contentious

**Actual Situation** [Verified: posttool-bash-audit.sh:125]:
```bash
printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$COMBINED_MSG"
```
Same format as posttool-edit-quality.sh:119.
- Claude Code Hook official documentation requires PostToolUse output field to be `hookSpecificOutput.additionalContext`
- The code includes the `"hookEventName": "PostToolUse"` field -- this is redundant, not required by the official schema
- More critically: posttool-bash-audit.sh's MSG contains `|` pipe characters, unescaped in `printf`, special characters may break JSON integrity
- For example: when `ANTI_PATTERN_MSG` contains quotes, the entire JSON may fail to parse, silently ignored by Claude Code

**Severity**: Low. Only affects visibility of audit prompts, not security mechanisms.

---

## VIII. 🔁 Supplementary Redundant/Low-Gain Items

### R-3: lsp-suggest.sh's "First Block Per Session" Strategy Has Poor User Experience

**Actual Situation** [Verified: lsp-suggest.sh:59-76]:
- First Grep of exported symbol -> exit 2 block -> AI must re-issue the exact same Grep
- Block only occurs once (writes `$SUGGESTED_FILE` marker), subsequent calls pass through
- Issue: this hook triggers even outside Go projects (Python, TypeScript, etc.), where LSP suggestions may not apply
- `EXAMPLE_FILE` is hardcoded to `model/tasks_mongo.go` (Go-specific filename), producing confusing example recommendations in non-Go projects

**Suggestion**: Change to only warn without blocking (exit 0 + additionalContext injection), reducing unnecessary interference.

---

### R-4: pretool-edit-scope.sh's Scope Freeze Depends on current-scope.txt but No Mechanism Auto-Writes This File

**Actual Situation** [Verified: pretool-edit-scope.sh:41,97, global search for current-scope]:
```bash
SCOPE_FILE="$PROJECT_ROOT/.omc/state/current-scope.txt"
# No scope file -> output coupling reminder then allow
if [ ! -f "$SCOPE_FILE" ]; then
    exit 0
fi
```
- If `current-scope.txt` does not exist, the hook directly passes through (fail-open design)
- `harness-kit.ts` reads this file but also does not write it
- **No code** in the entire source base auto-writes `current-scope.txt` -- this file can only be created manually by the user
- This means the scope freeze feature is silently disabled in **99% of real usage scenarios**

**Actual Gain**: Only effective when user manually maintains `current-scope.txt`; a "designed but never implemented" feature. Including it in the defense capability matrix in architecture documents is misleading.

---

### Updated Overview (After Round 2)

| Category | Round 1 | Round 2 | Total |
|---:|---:|---:|---:|
| ❌ False | 3 | 3 | **6** |
| ⚠️ Exaggerated | 4 | 2 | **6** |
| 🔁 Redundant/Low Gain | 2 | 2 | **4** |
| ✅ Consistent | 7 | -- | **7** |

---

### Comprehensive Severity Ranking

| Priority | Issue | Type | Impact |
|---:|---|---|---|
| P0 | V-2: Context Guard trigger depends on unwritten state file, silently inactive | False | Core hallucination prevention mechanism fails |
| P0 | V-4: error-dna.sh references undefined $DNA_FILE, completely non-functional | False | Error memory system silently fails |
| P1 | V-5: permission-gate marker file written by AI, user sovereignty bypassed | False | Security constraint can be self-bypassed by AI |
| P1 | P-5: OpenCode plugin has 6+ behavioral inconsistencies with Claude Code | Exaggerated | Cross-platform reliability questionable |
| P2 | V-1: Hook lines 2768, claimed "less than 1000" | False | Documentation credibility loss |
| P2 | V-3: mirror_scan.py uses regex not AST, technical spec inflated | False | User precision expectation deviation |
| P2 | R-4: current-scope.txt has no auto-write mechanism, scope freeze silently disabled | Redundant | Claimed protection capability actually absent |
| P3 | V-6: completion-gate evidence written by AI, concurrent race condition | False | Soft constraint, not hard constraint |
| P3 | P-1: privacy-gate only filename grep, claimed "military-grade" | Exaggerated | Actual protection scope limited |
| P4 | R-3: lsp-suggest blocking poor UX, triggers regardless of language | Redundant | Minor user experience issue |

---

**Summary**: The design direction of harness-kit is correct and valuable -- zero-trust defense, evidence gate, DLP proxy, concurrency locks -- these directions are all worthwhile. However, the actual delivered implementation of v6.1.7-stable has a systematic gap between implementation and claims, primarily manifesting in: multiple critical defense chains depend on "externally written" state files (Context Guard, Error DNA), but the entire system has no code writing these files; AI self-unblocking design (permission-approved, completion-evidence both written by AI); cross-platform (OpenCode plugin) implementation quality significantly below Claude Code version; documentation uses strong terminology like "military-grade," "physical determinism," "AST" that exaggerates compared to actual grep/regex/filename matching implementation.

**Audit Conclusion (Updated)**: The defense mechanisms of harness-kit are fully implemented at the code level with rigorous logic; the core architecture design is credible. Main issues center on documentation exaggeration and critical feature chain breaks.

---

## Third Round Scan Supplement

**New Scan Scope**: Full correspondence between all hooks and harness.yaml, harness_config.sh's hc_enabled mechanism, index.md hook count declarations, actual lx-skills version and count, architecture document "Syscall level" and other core qualitative descriptions.

---

## IX. ❌ Supplementary False Items

### V-7: context-guard and privacy-gate Not Controlled by harness.yaml's hooks_enabled -- Undocumented Configuration Blind Spot

**Document Claim** (architecture-review.md:28-30, full text core defense features):
The two most core defense hooks -- context-guard (OOM physical fuse) and privacy-gate (DLP defense) -- are key capabilities repeatedly referenced and scored throughout the document.

**Actual Situation** [Verified: Cross-verify harness.yaml against all .sh files]:

Hooks present in `.sh` but not in `hooks_enabled` config (7 total):
```
context-guard        -> hc_enabled "context_guard"  -> not in config block, default true
flywheel-report      -> hc_enabled "skill_flywheel"  -> uses different key, possible misread
posttool-write-lock  -> no hc_enabled call, unconditionally enabled
pretool-rule-anchor  -> hc_enabled "rule_anchor"    -> not in config block, default true
pretool-user-correction -> hc_enabled "user_correction_detector" -> not in config block
pretool-write-lock   -> no hc_enabled call, unconditionally enabled
privacy-gate         -> hc_enabled "privacy_gate"    -> not in config block, default true
```

- `hc_enabled` function defaults to returning `true` (harness_config.sh:198: `val=$(hc_get "hooks_enabled.${hook_name}" "true")`)
- Therefore these 7 hooks logically run, but **users cannot disable them by editing harness.yaml** -- they are outside the `hooks_enabled` control scope
- This is inconsistent with the other 20 configurable hooks, breaking config system integrity
- Notably, **context-guard and privacy-gate**, as the most core defense mechanisms, cannot be disabled on demand for special scenarios (e.g., CI environment)

**Severity**: Medium. Minimal impact for ordinary users (two core hooks still run), but for advanced users and enterprise users needing custom configuration, this is a governance blind spot between documentation and implementation.

---

### V-8: "Syscall Level Interception" Is a Seriously Misleading Technical Description

**Document Claim** (architecture-review.md:28, core selling point):
> "While all similar products are still competing on 'system prompts,' it achieves system call (Syscall) level interception. LLM wants to read .env? Direct Exit 2 headshot."

**Actual Situation** [Verified: No Syscall-related code in entire source]:
```
grep -rn "Syscall|syscall|system call|OS.*intercept" source/ -> No matches
```
- All interception is achieved through **Claude Code's Hook mechanism** -- this is a high-level API provided by Claude Code, not operating system system calls
- Claude Code Hook implementation principle: Before/after AI tool calls, Claude Code framework calls registered Shell scripts; script `exit 2` results in tool call interception
- This is **application-level interception** (Application-level hook), with no relation to OS syscall interception (such as ptrace, seccomp, eBPF)
- True Syscall-level interception can block any process system call (including direct `open()` etc.), while Claude Code Hooks only intercept AI tool calls -- if AI finds a way around the tool layer, Hooks are ineffective

**Severity**: Medium-High. "Syscall level" is a precise technical term; using it to describe Shell script hooks is misleading to users and creates a false sense of security.

---

## X. ⚠️ Supplementary Exaggerated Items

### P-7: index.md Claims "20 Hooks," Actual 25 Effective Hooks, Severely Underreported

**Document Claim** (index.md:63):
> "## Hooks Quick Reference (20 total)"

**Actual Situation** [Verified: `ls hooks/*.sh | grep -v harness_config | wc -l -> 25`]:
- Hooks directory actually has **25** effective hooks (excluding shared config library harness_config.sh)
- index.md's number "20" matches the harness.yaml hooks_enabled entry count, but ignores the 7 hooks not in configuration control
- architecture-review.md separately claims "24 hooks" -- three documents give three different numbers (20, 24, 25), none accurate

Evidence:
```
index.md:63                 -> "20 total"
architecture-review.md:29   -> "24 Bash Hooks"
Actual file count           -> 25 (excluding harness_config.sh)
harness.yaml                -> 20 hooks_enabled entries (7 hooks not in this config)
```

---

### P-8: "lx-skills-v5" Naming Doesn't Match Actual Version; Version Numbers Repeatedly Referenced in Documentation Are Inconsistent

**Document Claim** (architecture-review.md:12,38):
> "harness-kit (kernel layer) and lx-skills-v5 (capability layer)"

**Actual Situation** [Verified: source/lx-skills/.claude/skills/VERSION -> 5.2.3]:
- VERSION file shows current version is 5.2.3, not "v5" (though a major version shorthand could be semantically acceptable)
- However, CHANGELOG.md marks the overall version as v6.1.7-stable (outer package version), while lx-skills internal version is 5.2.3, creating a dual-version system that confuses users
- "lx-skills-v5" in documentation is a fixed name rather than a current version reference, which will require renaming when upgrading from 5.2.x to 6.x, creating naming debt

---

## XI. 🔁 Supplementary Redundant Items

### R-5: posttool-write-lock.sh and pretool-write-lock.sh Use grep to Parse JSON Instead of jq/python3, Fail When Paths Contain Special Characters

**Actual Situation** [Verified: pretool-write-lock.sh:16-19]:
```bash
FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"filePath"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [[ -z "$FILE_PATH" ]]; then
    FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | cut -d'"' -f4)
fi
```
- Other hooks all prioritize using `jq` or `python3` for JSON parsing (dual fallback mechanism)
- These two OMA lock hooks use only `grep` for parsing; if file paths contain spaces, quotes, or Unicode characters, `grep -o` matching fails, locks are not acquired, concurrent protection silently fails
- Inconsistent with the claimed robustness of "atomic lock engine"

**Suggestion**: Unify to use `jq || python3` dual fallback mechanism for JSON parsing, consistent with other hooks.

---

### Final Overview (Full Three Rounds)

| Category | Round 1 | Round 2 | Round 3 | Total |
|---:|---:|---:|---:|---:|
| ❌ False | 3 | 3 | 2 | **8** |
| ⚠️ Exaggerated | 4 | 2 | 2 | **8** |
| 🔁 Redundant/Disabled | 2 | 2 | 1 | **5** |
| ✅ Consistent | 7 | -- | -- | **7** |

---

### Final Priority Ranking (By Actual Impact)

| Priority | Issue # | Issue Summary | Category | Actual Impact |
|---:|---|---|---|---|
| P0 | V-2 | Context Guard trigger chain broken (state file has no writer) | False | Core hallucination prevention silently fails |
| P0 | V-4 | error-dna.sh references undefined $DNA_FILE | False | Error memory system completely invalid |
| P0 | V-8 | "Syscall level interception" severely misleading | False | Users have false sense of security |
| P1 | V-5 | permission-gate marker file written by AI, user sovereignty bypassed | False | Security constraint self-bypassable |
| P1 | P-5 | OpenCode plugin 6 behavioral inconsistencies with Claude Code | Exaggerated | Cross-platform reliability questionable |
| P2 | V-1 | Hook lines 2768, docs claim "less than 1000" | False | Documentation credibility loss |
| P2 | V-3 | mirror_scan.py regex != AST, technical spec inflated | False | User precision expectation deviation |
| P2 | V-7 | context-guard/privacy-gate not in config control scope | False | Core hooks cannot be disabled on demand |
| P2 | R-4 | current-scope.txt no auto-write, scope freeze silently disabled | Redundant | Claimed protection capability absent |
| P2 | P-7 | Hook count differs across 3 docs (20/24/25) | Exaggerated | Documentation inconsistency |
| P3 | V-6 | completion-gate evidence written by AI, concurrent race condition | False | Soft constraint, not hard |
| P3 | P-1 | privacy-gate only filename grep, claimed "military-grade" | Exaggerated | Limited protection scope |
| P3 | R-5 | OMA lock hooks use grep for JSON parsing, special paths fail | Redundant | Concurrency protection fails in edge cases |
| P4 | P-4 | Scoring dimension double-counted ([M]/[Z] each twice) | Exaggerated | Total score structural credibility issue |
| P4 | R-3 | lsp-suggest poor UX for non-Go projects | Redundant | Minor interference |

---

## Fourth Round Full Scan Supplement (Final Round)

**Scan Scope**: Remaining lx-skills (lx-pre-commit/lx-pre-push/lx-tdd-spec etc.), install script mechanism (Safe In-Place/Three-Stage Rocket/non-destructive hot-update), competitor comparison data sources, all key numeric claims (scores/hook counts/skill counts/thresholds), OWASP/BDD claims, 50% sweet spot mechanism details.

---

## XII. ❌ Supplementary False Items

### V-9: Scoring Table "14 Dimensions Total 136.7/140" Mathematically Invalid -- Table Only Has 13 Rows, Sum Is 125.8

**Document Claim** (architecture-review.md:114-115):
> Current 14-dimension total: 136.7 / 140
> Converted to original 130 scale: 126.9 / 130

**Actual Situation** [Verified: Row-by-row summation]:
```python
rows = [9.5, 9.8, 10.0, 9.7, 10.0, 9.8, 9.5, 9.8, 9.0, 9.6, 9.8, 10.0, 9.3]
# 13 rows, sum = 125.8
```
- Table has **13** rows, document claims 14 dimensions, missing the 14th row
- Actual sum of 13 rows = **125.8**, document claims 136.7, difference of **10.9 points**
- This means there is either a phantom dimension or a calculation error in the document
- Conversion formula `136.7/140x130 = 126.9` is mathematically valid, but the numerator 136.7 itself is wrong
- Three total scores (126.5 at end of Chapter 1, 127.2 at Chapter 2 title, 126.9 in scoring table conversion) are all inconsistent

**Severity**: Medium-High. The scoring system is a core argument of the document; systematic errors in numbers make the entire scoring conclusion lose credibility.

---

### V-10: Base Installation Mode Claims "6 Silent Gate Skills," Actually Retains 10

**Document Claim** (install.sh:87):
> `log_info "Streamlined to 6 silent gate Skills."`

**Actual Situation** [Verified: Python set difference calculation]:
```
Total Skills: 23
Base mode removed: 13
Actually retained: 10
Retained 10: lx-code-review lx-mirror lx-oma lx-perf-analysis lx-pre-commit lx-pre-push lx-react-review lx-security-review lx-style-guide lx-web-perf
```
- Code and actual deletion logic show 10 retained, but install.sh:87 outputs "6" to the user
- Consequently, architecture-review.md:103 also claims "19 Skills," actual source directory count is 23 (excluding TEMPLATE.md and VERSION)

**Severity**: Medium. Count error affects user expectations of feature scope, but does not affect functionality itself.

---

### V-11: Safe In-Place Upgrade "100% Zero Risk" -- Backup Is Auto-Deleted by trap EXIT When Script Fails Midway

**Document Claim** (architecture-review.md:104):
> Safe In-Place Upgrade non-destructive hot-update. Installation script-level memory sandbox automatically isolates and restores user configuration assets and memory DNA. Upgrade 100% zero risk.

**Actual Situation** [Verified: install.sh:34-35]:
```bash
BACKUP_DIR=$(mktemp -d)
trap "rm -rf $BACKUP_DIR" EXIT   # <- Any exit triggers deletion
```
- `trap "rm -rf $BACKUP_DIR" EXIT` means the backup directory is deleted whether the script succeeds **or fails**
- If `extract_tar` decompression fails (exit 1), the backup is deleted before being restored, causing permanent loss of user's original `claude-next.md` and other files
- Backup scope is limited to 4 files (harness.yaml/claude-next.md/anti-patterns.md/kernel.md); `.omc/state/` (containing todo-queue.md, error-dna.json, and other user accumulated data) is **completely out of backup scope**
- "100% zero risk" is a false claim for mid-failure scenarios

**Severity**: High. This is a design flaw that can actually cause data loss, packaged as a "100% zero risk" feature.

---

### V-12: "50% Sweet Spot Proactive Handoff, Forcing AI to Execute /compact" -- Actually stderr Output, Not Injected into AI Context, No Enforcing Power

**Document Claim** (architecture-review.md:172, scoring table [T] Task Continuity 9.8):
> "When ctx% >= 50% and at a task transition point, it automatically inserts a strong warning, forcing AI to execute /compact or start a new branch."

**Actual Situation** [Verified: context_monitor.py:32-34]:
```python
if ratio >= 0.5 and ratio < 0.8:
    print(f"[context_alert]: ...", file=sys.stderr)   # <- Writes to stderr
    print("Please immediately interrupt the current long context conversation!...", file=sys.stderr)
```
- 50% warning writes to `sys.stderr`, which is output visible to the human terminal
- context-guard.sh performs **no action at 50%** (exit 0); AI tool calls are completely unaffected
- The description of "forcing AI" and "automatically inserting" is completely inaccurate -- this is just a terminal print, the AI does not perceive it
- Only at 80% does `exit 2` hard block occur; at 50% there is only an stderr soft prompt for human viewing
- The documented "50% sweet spot proactive handoff" behaviorally exists (via prompt constraints/AGENTS.md), but it is **not implemented through code** -- it relies on AI self-discipline

**Severity**: High. The core supporting feature for [T] Task Continuity's 9.8 score has **no code-level enforcement**.

---

### V-13: manifesto.md Claims "OWASP LLM Vulnerability Interception Standard" and "100% BDD Behavior-Driven Testing" -- Completely Absent from Source Code

**Document Claim** (manifesto.md:86):
> "Carror OS includes 100% route-coverage BDD behavior-driven testing, and locally automates verification of 29 code-level probes, passing the strict testing of OWASP LLM vulnerability interception standards."

**Actual Situation** [Verified: Global file search]:
```
find source/ -name "*.feature" -> 0 results
find source/ -name "*bdd*"     -> 0 results
find source/ -name "*owasp*"   -> 0 results
```
- The entire `source/` directory contains **no BDD test files** (no `.feature`, no `behave`, no `pytest-bdd`)
- **"OWASP LLM vulnerability interception standard"** tests have no corresponding test code or report files
- The number "29 code-level probes" has multiple versions across the documentation system (24/25/29/49), with no unified口径
- What actually exists is `manual-acceptance-test.md` (manual acceptance testing) and `final-exam.md` (manual judgment checklist), not automated tests

**Severity**: High. This is a false compliance claim in external marketing materials. Claims at the OWASP certification level, without actual test support, are seriously misleading for enterprise users.

---

## XIII. ⚠️ Supplementary Exaggerated Items

### P-9: Two Inconsistent Thresholds (85% vs 80%) for Same Feature in architecture-review.md:28

**Document Claim** (same paragraph):
- architecture-review.md:28: "Want to continue writing code at 85% context? Physical power-off."
- architecture-review.md:172: "When ctx% >= 80%, it throws Exit 2 locking the system"

**Actual Situation** [Verified: context_monitor.py:41]:
```python
"is_danger": ratio >= 0.8   # Actual threshold 80%
```
The same document gives two different numbers for the same feature: 85% and 80%. Actual code implements 80%. 85% is a typo.

---

### P-10: Competitive Product Scoring Chart (Devin 7.0/Cursor 6.0/SWE-agent 8.0) Has No Data Source

**Document Claim** (architecture-review.md:129-157): Competitive product scoring chart gives Devin/Cursor/SWE-agent specific scores across 6 dimensions, precise to one decimal place.

**Actual Situation** [Verified: Global search finds no data source]:
- The entire source code/documentation contains **no competitive product evaluation reports, references, or third-party data**
- CHANGELOG.md:776 has a different set of competitive scores ("Cursor 48 / Aider 65"), completely different from the chart's number system
- These competitor scores are the author's subjective estimates, but presented as precise numerical charts, creating an impression of objective data

---

## XIV. 🔁 Supplementary Redundant Items

### R-6: lx-rpe "9-Step Pipeline" Claim Is Real, but Tying It to "Fighting LLM Entropy" Is Exaggerated

**Actual Situation** [Verified: lx-rpe/SKILL.md:50-52]:
lx-rpe's 9-step state machine (Read Task -> Design -> Code+Pre-commit -> Security -> Sync -> Wait Acceptance -> Judge -> Commit -> Summary) does exist and is fully implemented. However, architecture-review.md:52's description "translating AI's 'ephemeral memory' into a 'persistent state machine' on physical disk" is exaggerated -- the actual behavior is AI following the Skill's 9-step prompts to progressively write Markdown documents; this is AI executing Skill instructions, not an OS-level state persistence.

**Suggestion**: Keep lx-rpe as a real feature, correct the descriptive措辞.

---

### Final Complete Overview (Four Rounds)

| Category | Round 1 | Round 2 | Round 3 | Round 4 | Final Total |
|---:|---:|---:|---:|---:|---:|
| ❌ False | 3 | 3 | 2 | 5 | **13** |
| ⚠️ Exaggerated | 4 | 2 | 2 | 2 | **10** |
| 🔁 Redundant/Disabled | 2 | 2 | 1 | 1 | **6** |
| ✅ Consistent | 7 | -- | -- | -- | **7** |

---

### Complete Priority Table (Final Version)

| Priority | Issue # | Issue Summary | Category | Actual Impact |
|---:|---|---|---|---|
| P0 | V-2 | Context Guard trigger depends on unwritten state file, silently inactive | False | Core hallucination prevention fails |
| P0 | V-4 | error-dna.sh references undefined $DNA_FILE, completely non-functional | False | Error memory system silently fails |
| P0 | V-8 | "Syscall level interception" severely misleading | False | Users have false sense of security |
| P0 | V-11 | trap EXIT deletes backup; mid-failure causes data loss; "100% zero risk" false | False | Data security risk |
| P0 | V-13 | OWASP/BDD/100% coverage claims completely absent from source code | False | False compliance claims, misleading enterprise users |
| P1 | V-5 | permission-gate marker file written by AI | False | User sovereignty bypassed |
| P1 | V-12 | 50% sweet spot "forcing AI" is only stderr output, no enforcement power | False | [T] dimension 9.8 foundation absent |
| P1 | P-5 | OpenCode plugin 6 behavioral inconsistencies with Claude Code | Exaggerated | Cross-platform reliability questionable |
| P2 | V-1 | Hook lines 2768, docs claim "less than 1000" | False | Documentation credibility loss |
| P2 | V-3 | mirror_scan.py regex != AST, technical spec inflated | False | Precision expectation deviation |
| P2 | V-7 | context-guard/privacy-gate not in config control scope | False | Cannot be disabled on demand |
| P2 | V-9 | Scoring table 13 rows sum 125.8, claims 136.7; 3 total scores inconsistent | False | Scoring system fundamental error |
| P2 | V-10 | Base mode retains 10 Skills, claims "6"; Enhanced has 23, claims "19" | False | Skill counts all wrong |
| P2 | R-4 | current-scope.txt no auto-write, scope freeze silently disabled | Redundant | Claimed capability absent |
| P2 | P-7 | Hook count: index.md/review.md/install.sh say 20/24/22, actual 25 | Exaggerated | All four numbers different |
| P2 | P-9 | Same feature, same doc: 85% and 80% two thresholds | Exaggerated | Internal consistency poor |
| P3 | V-6 | completion-gate evidence written by AI, concurrent race condition | False | Soft constraint, not hard |
| P3 | P-1 | privacy-gate filename grep, claimed "military-grade" | Exaggerated | Limited protection scope |
| P3 | P-10 | Competitor score chart has no data source, subjective estimates presented as precise charts | Exaggerated | Misleading competitor comparison |
| P3 | R-5 | OMA lock hooks use grep for JSON parsing, special paths fail | Redundant | Edge case failure |
| P4 | P-4 | Scoring dimensions double-counted ([M]/[Z] each twice) | Exaggerated | Total score structural issue |
| P4 | P-8 | lx-skills-v5 naming vs VERSION 5.2.3 and outer v6.1.7 create triple-version confusion | Exaggerated | Version confusion |
| P4 | R-3 | lsp-suggest triggers on non-Go projects offering Go examples | Redundant | Minor interference |
| P4 | R-6 | lx-rpe 9-step pipeline real, "state machine" description exaggerated | Redundant | Precision issue |

---

### Verified Effective Core Features (After All Four Rounds)

| Feature | Verification Conclusion | Evidence |
|---|---|---|
| context-guard.sh exit 2 block at 80% | ✅ Code real but depends on unwritten state file (V-2) | |
| privacy-gate.sh filename blacklist block | ✅ Real, limited protection scope (P-1) | |
| varlock.py bidirectional mask/restore | ✅ Real and complete | varlock.py:36-48 |
| oma_lock_manager.py atomic file lock | ✅ Real | os.O_CREAT\|os.O_EXCL |
| lx-oma MECE requirement decomposition + directory scaffolding | ✅ Real | lx-oma/SKILL.md |
| lx-rpe 9-step dev closed loop | ✅ Real | lx-rpe/SKILL.md:50 |
| Install script backup/restore mechanism | ⚠️ Partially real, limited scope, risk on mid-failure (V-11) | |
| build-validator.sh build failure analysis | ✅ Real, complete implementation | |
| turn-counter.sh turn counting + iron rule injection | ✅ Real, reliable mechanism | |
| completion-gate.sh evidence gate | ⚠️ Partially real, AI self-written evidence bypassable (V-6) | |
| subagent_reviewer.py A/B blind review | ⚠️ Partially real, soft constraint not hard enforcement (P-2) | |
| pretool-edit-scope scope freeze | ⚠️ Partially real, depends on manually maintained state file (R-4) | |
| inject-project-knowledge.sh knowledge injection | ✅ Real, complete implementation | |
| auto-snapshot.sh session snapshot | ✅ Real, 318 lines, rich implementation | |
| permission-gate.sh dangerous command interception | ⚠️ Partially real, AI can self-write marker to bypass (V-5) | |

---

### Final Audit Conclusion

**Truly working**: Concurrency locks, DLP proxy, lx-oma decomposition, lx-rpe 9-step pipeline, session snapshots, knowledge injection, build failure analysis -- these features have complete code and reliable logic.

**Correct design but broken implementation chain**: Context Guard (state file has no writer), Error DNA (undefined variable), scope freeze (no auto-write mechanism), 50% sweet spot (only stderr output).

**False documentation claims**: OWASP/BDD testing (absent from source code), Syscall level interception (application-level hook), 100% zero risk hot-update (trap EXIT has data loss risk), scoring math error (136.7 vs actual 125.8).

**Core recommendation**: P0 issues (V-2/V-4/V-11/V-13) need fixing before next release, otherwise affecting system security and credibility.

---

### Corrected Scores (Based on Four-Round Audit Actual Code Evidence)

**Scoring Method**: Using 12 independent dimensions from the original text (removing one duplicate [M] and one duplicate [Z]), with new [E] Documentation Integrity dimension. Total 120 points.

**Basis**: Each score has corresponding source code evidence, see above audit details for each round.

#### Revised Scores by Dimension

| Dimension | Original Score | Revised Score | Core Deduction Basis |
|---|---|---|---|
| [H] Hallucination Prevention | 9.5 | 5.5 | Context Guard state file has no writer, silently inactive (V-2). 50% sweet spot only stderr output, AI unaware (V-12). 80% block logic real but trigger chain broken. |
| [A] Autonomous Control | 9.8 | 6.5 | subagent_reviewer.py prints JSON expecting AI to comply, not hard enforcement (P-2). Design direction correct but "physically stripping self-review authority" exaggerated. |
| [S] Safety | 10.0 | 7.0 | varlock.py bidirectional masking real and complete. privacy-gate is filename grep blacklist, config.json/.env.production directly bypassable (P-1). "Military-grade" claim unfounded. |
| [S] Simplicity | 9.7 | 7.5 | Three-stage install design reasonable. But Base claims "6 Skills" actually 10, Enhanced claims "19" actually 23 (V-10). Hook lines 2768 vs claimed "less than 1000" (V-1). |
| [M] Migration/Hot-Update | 10.0 | 6.0 | Backup only covers 4 files; entire memory directory .omc/state/ not in scope. trap EXIT auto-deletes backup on mid-failure (V-11). "100% zero risk" is false claim. |
| [Z] UX Interaction Proactivity | 9.8 | 7.5 | turn-counter/inject-project-knowledge/flywheel-report all real and effective, interaction design unique. lx-status initial state has no data, limited value (R-1). |
| [C] Cost Effectiveness | 9.5 | 8.5 | Progressive disclosure token saving mechanism real and credible, on-demand loading design complete. |
| [T] Task Continuity | 9.8 | 5.0 | 50% sweet spot enforcement mechanism does not exist (V-12). Context Guard 80% block default inactive due to state file issue (V-2). auto-snapshot session snapshot real but passive recording, not proactive enforced handoff. |
| [I] Tool Intelligence | 9.0 | 6.5 | Blind review direction correct, build-validator analysis real, lsp-suggest effective. OpenCode plugin 6 behavioral inconsistencies, cross-platform intelligence severely diminished (P-5). |
| [D] Drift Prevention | 9.8 | 8.0 | turn-counter iron rule injection, pretool-rule-anchor anchoring, user-correction-detector all real and effective. pretool-edit-scope silently disabled due to dependency on manual file (R-4), deduction. |
| [C] Config Friendliness | 10.0 | 7.5 | harness_config.sh caching mechanism elegant, merge-profile design reasonable. context-guard/privacy-gate outside hooks_enabled control scope (V-7), config system has blind spot. |
| [E] Documentation Integrity (new) | -- | 3.0 | OWASP/BDD claims completely absent from source code (V-13). "Syscall level" severely misleading (V-8). Scoring table math error 136.7 vs actual 125.8 (V-9). Competitor scores have no data source (P-10). |

#### Corrected Total Score

| | Original Claim | Actual (Post-Correction) |
|---|---|---|
| 12-dimension total (after dedup) | 136.7 / 140 (math error) | 78.5 / 120 |
| Converted to 100-scale | ~105 (exceeds cap, not credible) | 65.4 / 100 |
| Rating | S-grade (Industrial peak) | B-grade (Creative intermediate) |

#### Dimension Breakdown

**Truly solid (score >= 8.0)**:
- [C] Cost Effectiveness 8.5, [D] Drift Prevention 8.0
- Core infrastructure: atomic file locks, varlock bidirectional masking, session snapshots, build failure analysis, turn counting iron rule injection -- rigorous design, reliable code

**Correct design but broken implementation (score 5.0-6.5)**:
- [T] Task Continuity 5.0, [H] Hallucination Prevention 5.5 -- the two most heavily promoted dimensions, with the most severe implementation chain breaks
- [M] Migration Safety 6.0 -- backup design has fundamental flaw

**New deduction item**:
- [E] Documentation Integrity 3.0 -- OWASP/BDD/Syscall and other terminology cause overall credibility collapse

### One-Sentence Characterization

**v6.1.7-stable is a B-grade engineering experiment with a correct design direction, solid partial modules, but systematic chain breaks in critical defense paths, and exaggerated documentation that masks implementation gaps -- not its self-claimed S-grade industrial peak.**

Corrected score approximately **65/100**, placing it at a creative intermediate level among similar AI behavior governance tools -- core ideas are ahead, but the gap between "claimed features" and "actually running features" is too large to support the enterprise-grade compliance positioning in its documentation. After fixing the 5 P0 issues, expected score could rise to **78-82/100**.
