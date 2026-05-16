#### Bug Fix Path

**Behavior constraint**: Load `@../../.claude/nodes/behavior_rules.md` (Evidence Gate + Git Gate + Fix Cap).

**Root cause method**: Load `@../../.claude/nodes/execute_node.md` (5-Why rapid root cause analysis + degradation trigger matrix). This skill's fix cap is **2 rounds** (stricter than the general 3-round limit, since todo is lightweight mode).

```
1. readFile related code +/- 30 lines of context
1a. Reference original code (must paste <=5 lines of code directly relevant to the bug from readFile output, annotated with file:line)
2. Root cause judgment (30-second rule):
   |- Obvious (any of the following) -> Direct fix (minimal change):
   |  . Missing nil check / missed error / type error / boundary missing
3. go build ./... compiles
4. Symptom/root cause self-check (lx-todo specific):
   - Does this fix only add a guard at the call site?
     - Yes -> Check if other call sites also lack the guard
       - Yes -> Systemic issue, upgrade to main branch and use /root-cause-analysis
       - No -> Single-point defense acceptable, continue to Step 3
     - No -> Fix targets the data source, continue to Step 3
```
**Upgrade condition**: debug 2 rounds still can't locate root cause -> **must upgrade**, do not continue. Transfer context: collected evidence + eliminated hypotheses.

#### Feature Path

```
1. grep existing similar code, extract pattern
1a. Reference example code (must paste <=5 lines of reused pattern code from grep/readFile output, annotated with file:line)
1b. Pattern applicability check: Does existing pattern apply to current scenario?
    - Applicable (input/output types match + no known defects) -> Reuse
    - Not applicable (type mismatch / existing pattern itself has issues / current scenario has special constraints) -> Build from scratch (still <=3 files)
    - Unsure -> readFile existing pattern's callers and tests, confirm before deciding
    \- Tool degradation: grep no results -> AST grep -> readFile manual search
2. Reuse or build from scratch, minimal change
3. go build ./... compiles
```
**Upgrade condition**: During implementation, if new interfaces or proto changes are needed -> **must upgrade**.

#### Refactor Path

```
1. Confirm test coverage: go test -v ./affected/package 2>&1 | tail -5
   |- Tests exist -> Continue
2. Small-step refactor, go build ./... after each step
2a. Reference refactoring changes (must paste <=3 lines of key code before and after each, annotated with file:line)
3. Run existing tests: go test ./affected/package
```
**Upgrade condition**: Refactoring causes large-scale test failures (>3) -> **must upgrade**.

#### Docs Path

```
1. Directly modify documentation/comments
2. -> Skip to Step 4 (no Step 3 verification needed)
```
**Completion criteria for all types**:
- Key code referenced (except Docs)
- `go build ./...` compiles (except Docs), reference actual build output
- Changed files <=3 (`git diff --name-only | wc -l` verify)
- Changed files >3 -> **Stop immediately**, upgrade to lx-task-spec
- debug/fix retries <=2 (see `@../../.claude/nodes/execute_node.md` degradation matrix, this skill cap is 2 rounds)
- Evidence Gate + confidence labeling (see `@../../.claude/nodes/behavior_rules.md` SS1.3 + `@../../.claude/task_sys/unified_delivery_schema.md` Evidence Levels)

---
