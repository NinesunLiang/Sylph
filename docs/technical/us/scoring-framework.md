[ARCHIVED v6.2.1 — Historical document. Referenced hooks/scripts/skills may no longer exist. See story-10.]

     1|# Carror OS Four-Dimension Scoring Framework
     2|
     3|> **Version**: v6.1.9 | **Updated**: 2026-05-13
     4|> **Status**: Official scoring framework — all evaluation reports should use this as baseline
     5|
     6|---
     7|
     8|## Overview
     9|
    10|Carror OS evaluates itself across four dimensions comprising 28 sub-dimensions. Total weighted score is 345 points, normalized to a 10-point or 8-point scale.
    11|
    12|| Dimension | Name | Sub-dimensions | Total Weight | Description |
    13||-----------|------|---------------|-------------|-------------|
    14|| **C** | Capability | 9 | 105 | Instruction clarity, context completeness, process structure, etc. |
    15|| **E** | Error Prevention | 8 | 110 | Goal drift, hallucination, false completion, etc. |
    16|| **G** | Governance | 6 | 65 | Anti-decay, automation, security gates, etc. |
    17|| **U** | User Experience | 5 | 65 | Mental load, sense of control, interaction quality, etc. |
    18|
    19|**Composite = weighted average of C + E + G + U**, total weight 345.
    20|
    21|---
    22|
    23|## C Dimension: Capability
    24|
    25|Measures Carror OS's capability completeness as an AI governance framework.
    26|
    27|| ID | Name | Weight | Check Method | Maturity |
    28||----|------|--------|-------------|----------|
    29|| C1 | Instruction Clarity | 15 | Hook script `# Role:` comment coverage ratio | 0.85 |
    30|| C2 | Context Completeness | 15 | index.md iron laws / references / knowledge coverage | 0.85 |
    31|| C3 | Process Structure | 15 | completion-gate L3 gate + Oracle review + smoke regression | 1.00 |
    32|| C4 | Output Standardization | 10 | posttool-format-gate registration and matcher scope | 0.85 |
    33|| C5 | Tool Lifecycle | 10 | settings.json event type coverage (6 event types) | 0.90 |
    34|| C6 | Knowledge Density | 10 | claude-next.md line count + R-lessons + memory files | 0.85 |
    35|| C7 | Orchestration | 10 | OMA skill directory existence | 0.85 |
    36|| C8 | Maintainability | 10 | audit-hooks / smoke-test / hook-production-verify presence | 0.90 |
    37|| C9 | Error Recovery | 10 | error-dna / auto-fix / dna-jsonl infrastructure | 0.85 |
    38|
    39|### Sub-dimension Details
    40|
    41|**C1 Instruction Clarity**: Checks what proportion of `.claude/hooks/*.sh` scripts have a `# Role:` comment in their first 5 lines. Target: 100%.
    42|
    43|**C2 Context Completeness**: Checks `index.md` for iron laws quick-reference, hooks reference pointers, anti-patterns/kernel references.
    44|
    45|**C3 Process Structure**: Checks completion-gate.sh implements:
    46|- L3 complexity keyword detection (architecture decisions, multi-file changes)
    47|- Oracle review record block check
    48|- harness-smoke-test E2E-6 test case
    49|
    50|**C4 Output Standardization**: Checks posttool-format-gate.sh is registered in settings.json with matcher `.*` (full coverage).
    51|
    52|**C5 Tool Lifecycle**: Checks registered event types: PreToolUse / PostToolUse / PostToolUseFailure / Stop / UserPromptSubmit / SessionStart.
    53|
    54|**C6 Knowledge Density**: Composite — 50% line count + 30% R-lessons + 20% memory file existence.
    55|
    56|**C7 Orchestration**: Checks OMA skill directories: lx-oma-hier / lx-oma-split / lx-oma-gov / lx-oma-orch.
    57|
    58|**C8 Maintainability**: Checks key maintenance scripts: audit-hooks.sh / harness-smoke-test.sh / hook-production-verify.sh.
    59|
    60|**C9 Error Recovery**: Checks error-dna infrastructure: hook script / auto-fix script / JSONL data file.
    61|
    62|---
    63|
    64|## E Dimension: Error Prevention
    65|
    66|Measures Carror OS's defense against common AI error patterns.
    67|
    68|| ID | Name | Weight | Check Method | Maturity |
    69||----|------|--------|-------------|----------|
    70|| E1 | Goal Drift | 20 | pretool-edit-scope + claude-next lessons + turn-counter detection | 0.85 |
    71|| E2 | Hallucination | 20 | posttool-claim-audit presence + settings registration + claude-next lessons | 0.90 |
    72|| E3 | False Completion | 15 | completion-gate evidence check + anti-patterns A2 entry | 1.00 |
    73|| E4 | Inertial Execution | 12 | fuzzy-block presence + turn-counter fuzzy words + ghost exemption | 1.00 |
    74|| E5 | Symptom Confusion | 10 | error-dna NOISE_PATTERNS filter + JSONL data volume | 0.85 |
    75|| E6 | Self-Contradiction | 13 | claude-next R42 + R43 + anti-pattern-detect hook | 0.85 |
    76|| E7 | Overconfidence | 10 | completion-gate soft words + anti-patterns A2/F1 + quality score | 1.00 |
    77|| E8 | Context Amnesia | 10 | compact-detect knowledge injection + inject-project-knowledge + context-guard | 0.90 |
    78|
    79|### Sub-dimension Details
    80|
    81|**E1 Goal Drift**: Checks edit-scope.sh's scope freeze mechanism, drift lessons in claude-next.md, drift detection in turn-counter.sh.
    82|
    83|**E2 Hallucination**: Checks posttool-claim-audit.sh existence and registration, relevant lessons in claude-next.md. Maturity 0.90 (claim-audit exit 2 hard-block).
    84|
    85|**E3 False Completion**: Checks completion-gate.sh's evidence gating logic, anti-patterns.md A2 entry. Maturity 1.00 (hard-block).
    86|
    87|**E4 Inertial Execution**: Checks fuzzy-block.sh existence, turn-counter.sh fuzzy verb detection, ghost mode fuzzy command exemption. Maturity 1.00.
    88|
    89|**E5 Symptom Confusion**: Checks error-dna.sh's NOISE_PATTERNS filter rules, JSONL data volume > 10 entries.
    90|
    91|**E6 Self-Contradiction**: Checks claude-next.md records R42 (hook rules misapplied to skills) and R43 (CAPTCHA scripted approval).
    92|
    93|**E7 Overconfidence**: Checks completion-gate.sh soft completion word matching, anti-patterns.md A2/F1 definitions, quality score threshold. Maturity 1.00 (A2/F1/H1 all exit 2 hard-block).
    94|
    95|**E8 Context Amnesia**: Checks compact-detect.sh's knowledge reinjection, inject-project-knowledge.sh existence, context-guard.sh existence.
    96|
    97|---
    98|
    99|## G Dimension: Governance
   100|
   101|Measures Carror OS's long-term governance capabilities and infrastructure robustness.
   102|
   103|| ID | Name | Weight | Check Method | Maturity |
   104||----|------|--------|-------------|----------|
   105|| G1 | Anti-Decay Defense | 10 | audit-hooks + hook-production-verify + smoke test + auto-snapshot | 0.90 |
   106|| G2 | AI Automation | 10 | compact-detect + auto-snapshot + error-dna registration + auto-fix | 0.85 |
   107|| G3 | Learning Notes | 10 | claude-next.md > 100 lines + handoff + snapshot + R lessons > 10 | 0.85 |
   108|| G4 | Feature Flags | 10 | harness.yaml hooks_enabled + audit-hooks + hc_enabled full coverage | 0.90 |
   109|| G5 | Built-in Security | 15 | permission-gate + privacy-gate + sensitive-edit + context-guard registered | 1.00 |
   110|| G6 | Evaluation Framework | 10 | score-self-check exists + baseline + report + weights documented | 0.85 |
   111|
   112|### Sub-dimension Details
   113|
   114|**G1 Anti-Decay Defense**: Checks four anti-decay mechanisms: audit-hooks.sh (three-way consistency audit), hook-production-verify.sh (production verification), harness-smoke-test.sh (regression testing), auto-snapshot.sh (session snapshots).
   115|
   116|**G2 AI Automation**: Checks four automation mechanisms: compact-detect.sh (compression detection), auto-snapshot.sh (snapshot capture), error-dna registration in settings.json, error-dna-auto-fix.sh (auto repair).
   117|
   118|**G3 Learning Notes**: Checks knowledge accumulation: claude-next.md > 100 lines, session-handoff.md exists, session-snapshot.json exists, R-lesson count > 10.
   119|
   120|**G4 Feature Flags**: Checks feature toggle infrastructure: harness.yaml defines hooks_enabled, audit-hooks.sh exists, all hook scripts implement hc_enabled gating.
   121|
   122|**G5 Built-in Security**: Checks four security mechanisms registered in settings.json: permission-gate (dangerous command interception), privacy-gate (privacy protection), pretool-sensitive-edit (governance file CAPTCHA), context-guard (context threshold blocking). Maturity 1.00 — all are hard-block mechanisms.
   123|
   124|**G6 Evaluation Framework**: Checks scoring infrastructure: score-self-check.sh exists, score-baseline.json baseline saved, score-report.json report exists, weights defined in script.
   125|
   126|---
   127|
   128|## U Dimension: User Experience
   129|
   130|Measures interaction quality and mental load when users interact with Carror OS.
   131|
   132|| ID | Name | Weight | Check Method | Maturity |
   133||----|------|--------|-------------|----------|
   134|| U1 | Mental Load Reduction | 15 | CAPTCHA clear prompts + ghost exemption + format direction + score direction | 0.90 |
   135|| U2 | User Control | 15 | permission-gate + sensitive-edit CAPTCHA + git gate + Oracle verdict | 0.90 |
   136|| U3 | Behavioral Predictability | 10 | index.md iron laws + scope freeze + fix cap + confidence format | 0.85 |
   137|| U4 | Interaction Quality | 10 | format-gate direction + matcher full coverage + anti-pattern detection | 0.85 |
   138|| U5 | Permission Boundary Clarity | 15 | permission-gate scope + sensitive-edit file list + git gate + privacy targets | 0.90 |
   139|
   140|### Sub-dimension Details
   141|
   142|**U1 Mental Load Reduction**: Checks mechanisms that reduce cognitive burden:
   143|- CAPTCHA prompts in pretool-sensitive-edit.sh include directional guidance ("paste in input box and press Enter")
   144|- turn-counter.sh ghost mode fuzzy command exemption
   145|- posttool-format-gate.sh provides format direction hints
   146|- completion-gate.sh outputs quality breakdown and improvement direction when evidence fails (R38)
   147|
   148|**U2 User Control**: Checks user control over system behavior:
   149|- permission-gate registered in settings.json
   150|- pretool-sensitive-edit.sh uses verification code approval
   151|- index.md includes Git gate rules
   152|- lx-oma-orch SKILL.md includes Oracle gate verdict mechanism
   153|
   154|**U3 Behavioral Predictability**: Checks system behavior predictability:
   155|- index.md includes iron laws quick-reference table
   156|- Contains scope freeze rules
   157|- Contains fix cap rules
   158|- Contains confidence annotation format
   159|
   160|**U4 Interaction Quality**: Checks output quality and interaction experience:
   161|- posttool-format-gate.sh provides direction/summary
   162|- matcher configured as `.*` (full coverage)
   163|- posttool-anti-pattern-detect.sh exists (A2/F1/H1 real-time blocking)
   164|
   165|**U5 Permission Boundary Clarity**: Checks human-AI permission boundary clarity:
   166|- permission-gate.sh includes SCOPE_WRITE_RE / gh_write_regex and other precise scopes
   167|- pretool-sensitive-edit.sh includes sensitive file match list
   168|- index.md includes Git operation gate descriptions
   169|- privacy-gate.sh includes `.env`/private key detection
   170|
   171|---
   172|
   173|## Scoring Formula
   174|
   175|### Base Score
   176|
   177|Each sub-dimension's base score is determined by its check item pass rate:
   178|
   179|```
   180|base_score = features_present / features_total
   181|```
   182|
   183|Example C1 (3 checks): all pass → base = 1.0; 2 pass → base = 0.67.
   184|
   185|### Maturity Coefficient
   186|
   187|Mechanism quality matters more than existence. Maturity reflects actual enforcement strength:
   188|
   189|| Maturity | Value | Meaning | Example |
   190||----------|-------|---------|---------|
   191|| Hard-block | 1.00 | exit 2, aborts execution | permission-gate blocks rm -rf |
   192|| Active | 0.90 | Produces actionable warnings/context, doesn't block | claim-audit outputs additionalContext |
   193|| Advisory | 0.85 | Reference or passive check | index.md iron laws |
   194|
   195|### Lesson Penalty
   196|
   197|R-prefix lessons are parsed from claude-next.md and mapped to dimensions:
   198|
   199|```
   200|penalty = base_penalty × hits
   201|if fixed: penalty ×= 0.3
   202|penalty = min(penalty, 0.3)  # cap at 30%
   203|```
   204|
   205|### Final Score
   206|
   207|```
   208|final = max(0, base × maturity - penalty)
   209|```
   210|
   211|### Weighted Aggregation
   212|
   213|```
   214|weighted_sum = Σ(final × weight) / total_weight
   215|composite_10 = weighted_sum × 10
   216|composite_8 = weighted_sum × 8
   217|```
   218|
   219|---
   220|
   221|## Score Interpretation
   222|
   223|| Composite | Meaning |
   224||-----------|---------|
   225|| 9.0+ | Excellent — all dimensions well covered, key mechanisms at hard-block level |
   226|| 8.0-8.9 | Good — core dimensions complete, some limited by maturity or lesson penalty |
   227|| 7.0-7.9 | Adequate — major dimensions covered, but clear weak spots exist |
   228|| < 7.0 | Needs improvement — multiple dimensions have gaps, mechanisms need supplementing |
   229|
   230|### Current Baseline
   231|
   232|The current Carror OS baseline score is saved at `.omc/state/score-baseline.json`. Run the following to see the latest score:
   233|
   234|```bash
   235|bash .claude/scripts/score-self-check.sh           # Latest report
   236|bash .claude/scripts/score-self-check.sh --init    # Update baseline
   237|bash .claude/scripts/score-self-check.sh --diff <baseline>  # Diff comparison
   238|```
   239|
   240|---
   241|
   242|## Relationship to Other Scoring Systems
   243|
   244|| System | Dimensions | Relationship |
   245||--------|-----------|-------------|
   246|| Three-dimension internal (Defense/Amplification/Governance) | 3 | C+E maps to Defense, G is independent, U is new |
   247|| Dual-domain 12-dimension | 12 | Capability domain ≈ C, Governance domain ≈ G+E |
   248|| Product comparison scorecard | 10 | Different granularity for external benchmarking |
   249|
   250|This scoring framework is the project's **official dimension system**. All evaluation reports should use it as the baseline.
   251|