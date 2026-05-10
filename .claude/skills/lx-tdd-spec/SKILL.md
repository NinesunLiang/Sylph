---

name: lx-tdd-spec

version: v4.0.0

description: "Generate testable spec & acceptance criteria for new features/APIs via behavior matrix + GWT."

complexity: intermediate
when_to_use: "Use when user describes a new feature/module/API and needs structured spec + verifiable ACs."

model: sonnet

argument-hint: "<feature/API description>"

paths:

 - "*.go"

 - "go.mod"

harness_version: ">=1.1.0"
role: "Test spec & acceptance criteria generator for new features"
execution_mode: stepwise

triggers:
  - "/lx-tdd-spec"
---

# Requirements Spec Generator

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|context_collector | `../../nodes/context_collector.md` | 收集项目上下文|
|generator | `../../nodes/generator.md` | Spec + AC 生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 研究阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|task_input | `../../schemas/input/task_input.yaml` | 结构化任务输入（功能描述 → task_input 转换）|
|spec_output | `../../schemas/output/spec_output.yaml` | Step 3 Spec 输出契约|
|criteria_output | `../../schemas/output/criteria_output.yaml` | Step 4 验收标准输出契约|
|verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长 Spec 生成会话的上下文总结 |

### 状态机
本 skill 映射到 orchestrator 的 `ready → planning → spec_review` 路径：- Step 1-2 → `planning`（收集上下文 + 构建行为矩阵）- Step 3-4 → `spec_review`（生成 Spec + 验收标准）- Step 5 → Gate 检查（三重验证）- Step 6 → 手交到 `executing`（引导用户进入 TDD RED 阶段）
**核心状态映射**: need_clarification → executing → [Context, Matrix, Spec, AC, Validation, Handoff] → done

### 私有节点
本 skill 无私有节点。Step 2（行为矩阵构建）是 Spec Generator 的前置步骤，未来可提升为通用节点。

---

## Goal
加载 `@../../nodes/behavior_rules.md`（研究阶段行为约束）+ `@../../nodes/generator.md`（Spec + AC 生成模板）。
Convert user's feature description into structured spec + testable ACs with **no implementation details**, **full boundary coverage**, and **triple validation**.

## Minimum InputFeature description from user: $ARGUMENTS
Must have all three before proceeding:1. **Function intent**: what the feature/API does2. **Input outline**: expected inputs or parameters3. **Output outline**: expected outputs or responses
Missing any → ask user, do not proceed.

### 输入验证（Harness 模式）
当用户描述不足以生成 Spec 时，自动展示用途说明 + 用法引导：

```📋 lx-tdd-spec 用途说明： 将功能需求描述转化为结构化 Spec + 可测试的 Given-When-Then 验收标准： - 行为矩阵（正常/边界/错误/并发场景穷举） - 业务规则（原子化、可独立验证） - 验收标准 AC（GWT 格式，优先级 P0/P1/P2） - 三重映射验证（BR→AC / AC→Matrix / 参数→AC） - 输出到 docs/specs/[feature].spec.md
📖 用法：/lx-tdd-spec <功能描述> 必填：功能/API 的一句话描述 建议补充：输入类型、输出类型、边界约束 示例：/lx-tdd-spec "用户注册 API，支持手机号+验证码登录" 示例：/lx-tdd-spec "Task 批量删除，支持按 taskId 列表批量删除" 示例：/lx-tdd-spec "消息查询接口，支持分页+时间范围过滤"
⚠️ 需要至少 3 要素才能生成 Spec： 1. 功能做什么（intent） 2. 输入是什么（参数/类型/约束） 3. 输出是什么（正常响应/错误响应）
```

## Steps

### 1. Collect ContextUse the Task tool to launch these searches **in parallel in a single message**:- **Agent 1**: `grep` → 2+ same-layer modules → infer naming/parameter/return style- **Agent 2**: `ast-grep`/`LSP` → extract target signature & types- **Agent 3**: `readFile` → `go.mod` → tech stack（若缺失 → 向用户确认技术栈）- **Agent 4**: Document Agent → external API docs if referenced
**工具降级**：任一 Agent 失败（LSP 无响应、文件不存在）→ 记录 `[降级：原因]`，用其他 Agent 结果补充，不阻塞流程。
**Success criteria**:- ✅ Function name & 职责边界明确- ✅ Tech stack confirmed (source: config file)- ✅ Interface style extracted (source: ≥2 modules)- ✅ Input/Output types from LSP or user- ✅ Implicit constraints with confidence tags: `[确认]` / `[推测-中]` / `[推测-低：需确认]`- ❌ Low-confidence items → listed in "待确认事项"

### 2. Build Behavior MatrixEnumerate all behaviors. For each:- Classify: normal / boundary / error / concurrent- Exhaust via: - Equivalence classes - Boundary values (±1) - Special values (null, empty, MAX, NaN) - Parameter combos- Concurrent if: modifies shared state / check-then-act / side effects / order-sensitive resource
**Success criteria**:- ✅ Normal ≥1, Boundary ≥1, Error ≥1, Concurrent ≥0 (with rationale if "not applicable")- ✅ All boundary types applied- ✅ AC-XX IDs assigned- ✅ ≤2 补充轮次 used; if required class = 0 after 2 rounds → abort

### 3. Write Spec (Markdown)Write to `docs/specs/[feature].spec.md` with exactly 9 sections:1. 功能概述2. 输入定义（type + constraint）3. 输出定义（normal + error table）4. 业务规则（BR-01+, independently verifiable）5. 约束与限制（quantified: P99 < Xms, QPS = Y）6. 依赖关系7. 术语表8. 验收标准（AC-XX, GWT format）9. 待确认事项（low-confidence only）
**Success criteria**:- ✅ Low-confidence constraints only in section 9- ✅ BRs are atomic, no "and" chaining- ✅ Rule conflict checked & resolved/flagged

### 4. Generate Acceptance Criteria (GWT)
**验收标准格式**：加载 `@../../nodes/a_terminal.md`（YAML 验收标准格式）。本 skill 额外要求 GWT（Given-When-Then）表述。
For each matrix row → AC with GWT + Priority + Testability.**Assertability self-check**（见 `@../../nodes/b_terminal.md` 验收规则）：- Reject: "correct", "fast", "reasonable"- Must pass: `expect(x).toBe(Y)` directly writable
**Success criteria**:- ✅ AC count = matrix rows (±1 with explanation)- ✅ All ACs in GWT format + pass assertability check- ✅ No PII, only synthetic data

### 5. Triple Validation & Report
**强证据执行协议（Iron Law）**：三重验证不可走过场。
Build 3 mapping tables:- BR → AC- AC → Matrix row- Parameter → AC (in Given)
**每张映射表必须遵循 BUILD-VERIFY-CHALLENGE 三步法**：

```对每张映射
表
：1. BUILD: 逐行构建映射，不可批量声称 "所有 BR 均已映射"2. VERIFY: 检查每行映射的逻辑正确性（BR-01 的业务规则是否真的被 AC-01 的 GWT 覆盖？）3. CHALLENGE: 对每个映射提出反问 "如果 AC-01 通过了，BR-01 真的被验证了吗？"
对每张映射表：1. BUILD: 逐行构建映射，不可批量声称 "所有 BR 均已映射"2. VERIFY: 检查每行映射的逻辑正确性（BR-01 的业务规则是否真的被 AC-01 的 GWT 覆盖？）3. CHALLENGE: 对每个映射提出反问 "如果 AC-01 通过了，BR-01 真的被验证了吗？"
```

**反虚构规则**：- ❌ 禁止：输出 "BR → AC 映射完成，无空行" 但不展示映射表- ❌ 禁止：快速生成一对一映射而不验证逻辑关联- ❌ 禁止：所有 BR 恰好一对一映射到 AC（这通常是偷懒的信号，真实场景中 1:N 和 N:1 很常见）- ✅ 必须：完整展示每张映射表的每一行
**深度验证强制要求**：- BR → AC：对每个 BR，找到覆盖它的所有 AC（可能 1:N），验证 AC 的 Then 能否直接断言 BR 的约束- AC → Matrix：对每个 AC，确认其场景来自 matrix 的哪一行，验证 GWT 的 Given 条件与 matrix 行的输入条件一致- Parameter → AC：对每个输入参数，确认至少有一个 AC 在 Given 中使用了该参数
**对抗性自检**（三张表完成后执行）：> 随机选择 2 个 BR 和 2 个 AC，尝试找到以下问题之一：> - BR 被映射到了不相关的 AC（逻辑关联错误）> - AC 的 Then 无法断言 BR 的约束（覆盖不足）> - 某个参数的边界值未出现在任何 AC 的 Given 中> 若找到 → 修复映射；若未找到 → 说明验证理由
**Success criteria**:- ✅ 三张映射表已完整展示（不可省略行）- ✅ No empty rows in any mapping- ✅ 每个映射有逻辑关联说明（不可仅凭编号对应）- ✅ 对抗性自检已执行并记录结果- ✅ All quality gates passed- ✅ Output spec is self-contained and review-ready- ❌ Any gate fails → stop, return report with user queries

### 6. Handoff to TDD RED PhaseAll validations passed → guide user into the RED phase:
1. List all P0 ACs with their test target function names2. For each target, suggest the exact command: ``` /lx-golang-test <function/handler name>
/lx-golang-test <function/handler name>

```
 with scenarios extracted from the AC's Given-When-Then3. Output a ready-to-use summary table:
| AC ID | Target Function | Test Type | Scenarios (from GWT)|
|-------|----------------|-----------|---------------------|
|AC-01 | CreateUser | unit | normal + boundary + error|
|AC-02 | GetUser | unit + race | normal + not-found + concurrent |\|
**Success criteria**:- ✅ Every P0/P1 AC mapped to a `/lx-golang-test` invocation- ✅ Scenarios derived from GWT, not invented- ✅ User can copy-paste each command directly
## 跨 Skill 联动
| 方向 | Skill | 触发条件 | 数据契约|
|------|-------|---------|---------|
|下游传至 | `/lx-golang-test` | Step 6 正常流：P0/P1 AC 生成测试 | AC ID + Target Function + Test Type + GWT Scenarios|
|下游传至 | `/lx-debug-spec` | 测试执行后发现 bug（测试失败、运行时错误） | 错误症状 + 失败测试输出 + 相关 AC ID + Spec 文件路径 |\|
### 自动升级规则
在 Step 6 引导用户执行 `/lx-golang-test` 后，如果测试运行发现 bug：
1. **测试失败（非预期）**：生成的测试揭示了实现中的 bug → 建议：`/lx-debug-spec <失败测试名称及错误输出>`
2. **运行时异常**：panic、race condition、timeout → 建议：`/lx-debug-spec <异常描述及堆栈跟踪>`
输出格式：
```⚠️ 测试发现问题，建议进入调试流程：/lx-debug-spec <错误描述>
传递上下文：- 来源 Spec：docs/specs/[feature].spec.md- 失败 AC：AC-XX- 错误输出：[粘贴]

```
## Abort ConditionsStop immediately if:- User input missing: function intent / input outline / output outline- Low-confidence constraint not isolated- Then not assertable- Triple mapping has empty rows→ Return `⛔ 中止` report with exact user questions.
## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|AC 无法量化 | 生成验收标准 | 改为"可观测行为"描述，标注"[主观验收]"|
|缺少现有测试参考 | 提取模式 | AI 基于功能描述直接生成 GWT 框架 |


