---

name: lx-debug-spec

version: v4.0.0

description: "DEPRECATED (Oracle 审计 2026-05-15): Debug Go code via root-cause investigation → hypothesis verification → fix → regression. Evidence before fix."

complexity: intermediate
when_to_use: "Use when user says 'debug', 'fix bug', test failure, CI broken, intermittent error, race condition, or after failed fixes."

model: sonnet

argument-hint: "<error description, e.g. 'TestUserCreate reports connection refused'>"

disable-model-invocation: true

paths:

 - "*.go"

 - "go.mod"

harness_version: ">=1.1.0"
status: mature
role: "Root-cause debugger for Go — structured investigation protocol"
execution_mode: stepwise

triggers:
  - "/lx-debug-spec"
  - "debug"
---

# Systematic Debugging

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 从错误描述定位目标代码|
|context_collector | `../../nodes/context_collector.md` | Phase 1 收集上下文|
|auto_fixer | `../../nodes/auto_fixer.md` | Phase 4 根因修复|
|verifier | `../../nodes/verifier.md` | Phase 4 回归验证|
|report_generator | `../../nodes/report_generator.md` | 调试报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 研究阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 调试目标定义|
|context_summary | `../../schemas/atomic/context_summary.yaml` | Phase 1 上下文摘要|
|finding | `../../schemas/atomic/finding.yaml` | 发现的问题|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 调试判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Phase 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长调试会话的上下文总结 |

### 状态机
本 skill 映射到 orchestrator 的 `ready → executing → done` 路径，但使用**私有 4 阶段流程**（Phase 1 根因调查 → Phase 2 模式分析 → Phase 3 假说验证 → Phase 4 修复回归）。原因：调试是假设驱动的迭代过程，与通用任务执行不同。
**核心状态映射**: need_clarification → executing → [Phase 1 根因调查 → Phase 2 模式分析 → Phase 3 假说验证 → Phase 4 修复回归] → done

### 私有节点
本 skill 无私有节点。

---
Iron rule: **No fix proposals until Phase 1 root-cause investigation is complete.**
Debug and fix only. Not for new features, security review, or test generation.
Error to investigate: $ARGUMENTS

## Pre-check
User input must contain at least one of:- **Error symptom**: what went wrong- **Observable evidence**: error message / log / test output
If missing, ask: "Please describe the error and provide the full error output including stack trace."

## Phase 1: Root-Cause Investigation
**Goal**: Understand WHAT and WHY. Do NOT propose fixes.

### 1.1 Collect EvidenceUse the Task tool to launch investigation agents **in parallel in a single message**:
**Agent A — Code & History**:- Read full error: stack trace, line numbers, file paths, error codes- Reproduce: run the failing test/command- Check recent changes: `git log --oneline -20`, `git diff HEAD\~5`- Trace data flow: where does the bad value originate? Use Grep for call chains
**Agent B — Context & Environment** (if multi-component or external deps):- Check component boundaries: which component fails- Environment diff: local vs CI vs prod (versions, env vars, configs)- External library known issues (if applicable)
**工具降级**：Agent 失败（git 不可用、LSP 无响应）→ 记录 `[降级：原因]`，用其他途径补充（如 readFile 代替 LSP，用户描述代替 git log）。

### 1.2 Analyze Findings
Synthesize agent outputs. For special scenarios:- **Intermittent (< 50% repro)**: increase logging, run `go test -count=20 -race`, record trigger conditions- **Race condition**: force `-race`, collect full race report (goroutine ID + stack)- **Performance regression**: benchmark before/after, `go tool pprof`- **Deep call stack (> 5 layers)**: read `${CLAUDE_SKILL_DIR}/references/root-cause-tracing.md`

### 1.3 Failure handling- Cannot reproduce → collect more data (max 3 rounds), do NOT guess- Incomplete error → ask user for full stack trace- 3 rounds without localization → output "Investigation Aborted" report
**Success criteria — Phase 1 Gate** (all fields must be filled):

```- Error summary: [one sentence]- Repro status: [stable / intermittent (rate: X%) / cannot reproduce]- Repro steps: [exact steps] (source: [executed / user-described])- Recent related changes: [found / none] (source: [git log/diff])- Data flow trace: [bad value origin path] (source: [Grep / manual])- Concurrency related: [yes (race report: ...) / no]- Initial localization: problem is in [X] because [evidence]- Data collection rounds: [X]/3- Each conclusion tagged: [verified] / [speculative] / [unconfirmed]
- Error summary: [one sentence]- Repro status: [stable / intermittent (rate: X%) / cannot reproduce]- Repro steps: [exact steps] (source: [executed / user-described])- Recent related changes: [found / none] (source: [git log/diff])- Data flow trace: [bad value origin path] (source: [Grep / manual])- Concurrency related: [yes (race report: ...) / no]- Initial localization: problem is in [X] because [evidence]- Data collection rounds: [X]/3- Each conclusion tagged: [verified] / [speculative] / [unconfirmed]

```
Cannot fill "error summary" or "initial localization" → stay in Phase 1.

## Phase 2: Pattern Analysis
> 加载 `@references/defense-in-depth.md` 获取详细模式分析规则。

## Phase 3: Hypothesis Verification
> 加载 `@references/condition-based-waiting.md` 获取详细模式分析规则。

## Phase 4: Implement Fix
**Goal**: Fix root cause, not symptoms.

### Steps1. **Create failing test**: minimal reproduction, automated2. **Single fix**: only the root cause, one change, no bundled refactoring3. **Verify**: target test passes + regression tests pass + `-race` detection4. **Concurrency extra**: `go test -race -count=50` confirms race eliminated

### Failure handling- Fix fails < 3 times → back to Phase 1 (do NOT stack changes)- Fix fails ≥ 3 times → **Architecture Challenge**: each fix exposing new issues at different locations = architectural flaw. Discuss with user before continuing.
**Success criteria — Phase 4 Gate**:

```- Failing test: [name and path] (created: yes/no)- Fix summary: [one sentence]- Changed: [path:line]- Verification: - Target test: ✅/❌ - Regression tests: ✅/❌ - -race detection: ✅/❌/N/A - Manual verification: ✅/❌/N/A- Fix attempts: [X]/3- Cross-phase consistency: Phase 3 root cause = Phase 4 fix target [YES/NO]
- Failing test: [name and path] (created: yes/no)- Fix summary: [one sentence]- Changed: [path:line]- Verification: - Target test: ✅/❌ - Regression tests: ✅/❌ - -race detection: ✅/❌/N/A - Manual verification: ✅/❌/N/A- Fix attempts: [X]/3- Cross-phase consistency: Phase 3 root cause = Phase 4 fix target [YES/NO]
```
Cross-phase consistency = NO → stop, back to Phase 3.

## 上下文保持
长调试会话中，在以下时间点使用 `<remember priority>` 保存关键发现防止上下文遗忘：- Phase 1 Gate 完成后：保存错误摘要 + 初始定位- Phase 3 Gate 完成后：保存确认的根因 + 假说历史- 每次假说被拒绝后：保存已排除假说列表

## Prohibited Actions & Danger Signals
Before every action, load and self-check: `readFile("${CLAUDE_SKILL_DIR}/references/checklists/danger-signals.md")`（若文件不存在 → 使用内置规则：禁止未验证就提出修复、禁止堆叠变更、禁止跳过复现步骤）

## 跨 Skill 联动
| 方向 | Skill | 触发条件 | 数据契约|
|------|-------|---------|---------|
|上游来自 | `/lx-tdd-spec` | TDD 测试发现 bug | 接收：错误症状 + 失败测试输出 + AC ID + Spec 路径|
|上游来自 | `/lx-golang-test` | 生成的测试运行失败 | 接收：失败测试名 + 错误输出 + 测试文件路径|
|上游来自 | `/lx-security-review` | 安全漏洞 auto-fix 失败 | 接收：漏洞描述 + 严重级别 + 失败修复尝试 + 文件路径|
|下游传至 | `/lx-root-cause-analysis` | 调查中止或架构挑战（3 次修复失败） | 传递：症状摘要 + 复现步骤 + 已排除假说 + 已收集证据|
|下游传至 | `/lx-golang-test` | Phase 4 修复完成后生成回归测试 | 传递：修复函数名 + 根因场景 + 测试类型 |

### 自动升级至 lx-root-cause-analysis
当以下条件满足时，自动建议升级：
1. **调查中止**：Phase 1→3 循环达到 2 次上限仍无法定位2. **架构挑战**：Phase 4 修复失败 3 次，每次暴露不同位置的新问题3. **bug 复现**：修复后同一 bug 再次出现
输出格式：

```⚠️ 系统调试无法解决此问题，建议进入根因分析：/lx-root-cause-analysis <症状描述>
传递上下文：- 症状：[一句话]- 复现状态：[stable / intermittent]- 已排除假说：[列表]- 已收集证据：[列表，含来源]- 修复尝试：[次数] 次，均失败
```

## User Correction Signals
If user says any of these → stop → back to Phase 1:- "That didn't happen though?" → you assumed without verifying- "Stop guessing" → you're guessing fixes- "Think deeper" → you're fixing symptoms- "Are we stuck?" → your approach is wrong

## Auxiliary Documents
| Document | Trigger | Phase|
|---|---|---|
|`${CLAUDE_SKILL_DIR}/references/root-cause-tracing.md` | Call stack > 5 layers deep | Phase 1|
|`${CLAUDE_SKILL_DIR}/references/defense-in-depth.md` | Multi-layer verification needed after fix | Post Phase 4|
|`${CLAUDE_SKILL_DIR}/references/condition-based-waiting.md` | Code contains `time.Sleep()` or fixed timeouts | Phase 4 |

## Output Templates

### Normal Completion

```## Systematic Debugging Report

### Phase 1: Root-Cause Investigation
加载 `@../../nodes/behavior_rules.md`，应用研究阶段行为约束。加载 `@../../nodes/context_collector.md`，收集错误上下文。- Error summary: [one sentence]- Repro: [stable/intermittent/cannot] — Steps: [steps]- Recent changes: [found/none]- Data flow: [bad value path]- Concurrency: [yes/no]- Localization: [X] because [evidence] [verified]

### Phase 2: Pattern Analysis- Working example: [path]- Key differences: [list with relevance tags]- Most likely root cause: [analysis] (confidence: [level])

### Phase 3: Hypothesis Verification- Hypothesis: "[X] because [Y]"- Result: [confirmed] (evidence: [output])- Confirmed root cause: [final] (confidence: [high])

### Phase 4: Fix
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略。- Failing test: [path]- Fix: [one sentence]- File: [path:line]- Target test: ✅ | Regression: ✅ | Race: ✅/N/A- Cross-phase consistency: ✅

### Conclusion- Root cause: [one sentence]- Fix: [one sentence]- Scope: [affected files/modules]- Prevention: [how to avoid recurrence]
```

### Investigation Aborted

```## Systematic Debugging (Aborted)

### Excluded Hypotheses1. [A]: excluded because [evidence]

### Collected Evidence- [evidence] (source: [tool]) [verified/unconfirmed]

### Abort Reason- Loop count: [X]/2 (limit reached)- Why: [environment / timing / external / insufficient info]

### Next Steps- Add logging at: [locations]- Reproduce command: `go test -race -count=N ./...
`
```

### Architecture Challenge (3 failed fixes)

```## Systematic Debugging (Architecture Challenge)
| # | Fix | Result | New Issue|
|---|---|---|---|
|1 | [desc] | ❌ | [issue]|
|2 | [desc] | ❌ | [issue]|
|3 | [desc] | ❌ | [issue] |

### PatternEach fix exposes issues at different locations → architectural flaw signal

### Options- A) Refactor [module]- B) Workaround: [alternative + cost]- C) Accept limitation: [conditions + risk]
**Discuss with user before continuing.**
```

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|git log 不可用 | 查看提交历史 | 用 readFile 读取最近变更文件，人工判断|
|go test -race 挂起 | 并发调试 | 加 -timeout 30s，减少 -count 值|
|LSP 无响应 | 代码导航 | 用 grep + readFile 替代，标注"[降级:无LSP]"|
|无法复现（<10%复现率）| 定位根因 | 增加日志，记录触发条件，标注"[间歇性]" |


