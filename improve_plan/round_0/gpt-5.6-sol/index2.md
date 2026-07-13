# CarrorOS 最终整合重构方案
## 第 2/8 部分：L1 Base / L2 Enhance 治理工作流与状态协议

本部分在第 1/8 部分冻结的四平面架构上，完整定义 CarrorOS 的主治理链：

```text
IntakeGate
    ↓
PlanBuilder
    ↓
PreActionGate
    ↓
Executor Ledger
    ↓
VerifyGate
    ↓
Archive + Memory Writeback
```

本章的核心裁决是：

> **Context Engine 只维持连续性，VerifyGate 才制造完成事实；文档系统保存长期记忆，状态文件保存运行事实，Artifact 保存原始证据。**

---

# 一、L1 Base 与 L2 Enhance 的最终工作流

## 1.1 L1 Base：三阶段、六组件

面向中型、边界明确、可通过确定性命令验证的任务。

```text
A. Intake / Plan
   ├── IntakeGate
   └── PlanBuilder

B. Execute
   ├── PreActionGate
   └── Executor Ledger

C. Verify / Archive
   ├── VerifyGate
   └── Archive + Memory Writeback
```

L1 的原则：

```text
- 一次只执行一个 step 的一个 action；
- 不默认调用 Oracle；
- 不默认启动多 Agent；
- 不做全仓式上下文加载；
- 主要依赖 command / file / user 三类确定性验证；
- 复杂度超出边界时升级 L2，而不是在 L1 内偷偷扩 scope。
```

## 1.2 L2 Enhance：五阶段、增强治理

面向跨模块、架构变更、研究驱动、高风险或长期任务。

```text
A. Research
   ├── Research Manifest
   ├── 隔离检索/审查 Agent
   └── Knowledge Patch

B. Plan
   ├── IntakeGate Enhanced
   ├── PlanBuilder Enhanced
   └── ROI / 风险 / 回滚设计

C. Execute
   ├── PreActionGate
   ├── Executor Ledger
   └── 多会话/子 Agent 隔离执行

D. Verify
   ├── VerifyGate
   ├── 必要时 Oracle / Multi-Judge
   └── 残余风险裁决

E. Archive / Memory Writeback
   ├── ADR / Contract 更新
   ├── Research 归档
   ├── Error DNA
   └── 可复用知识写回
```

L2 的原则：

```text
- L2 增强治理深度，不增加主执行 Context 的常驻体积；
- Research、Oracle、Review 使用隔离上下文；
- 返回主会话的是结构化 Knowledge Patch / Verdict；
- 无论模型多强，完成仍由 VerifyGate 判定；
- Oracle ACCEPT 不能绕过基础验证；
- Meta-Oracle 只能聚合裁决，不能伪造缺失证据。
```

---

# 二、最终状态机

## 2.1 任务状态

冻结以下任务状态枚举：

```text
DRAFT
INTAKE_PENDING
ASK_USER
READY
PLANNED
RUNNING
COMPACT_SOON
RESUME_REQUIRED
BLOCKED
VERIFYING
WARN
VERIFIED
REJECTED
ARCHIVING
ARCHIVED
CANCELLED
```

状态含义：

| 状态 | 含义 | 是否可执行业务动作 |
|---|---|---:|
| `DRAFT` | 任务目录已创建，信息未检查 | 否 |
| `INTAKE_PENDING` | Intake 正在判定 | 否 |
| `ASK_USER` | 缺少用户才能提供的信息 | 否 |
| `READY` | Intake 通过，可以构建计划 | 否 |
| `PLANNED` | 计划已通过结构检查 | 是 |
| `RUNNING` | 当前 step 正在执行 | 是 |
| `COMPACT_SOON` | 上下文到软水位，需写 handoff | 限制执行 |
| `RESUME_REQUIRED` | 必须切会话或重建 Context | 否 |
| `BLOCKED` | 外部依赖、安全门或工具阻塞 | 否 |
| `VERIFYING` | VerifyGate 正在核验 | 否 |
| `WARN` | 基础验证通过但有残余风险 | 按策略决定 |
| `VERIFIED` | 任务全部通过 VerifyGate | 否，只可归档 |
| `REJECTED` | 验证失败，需要返工 | 否，修复后回 `RUNNING` |
| `ARCHIVING` | 正在归档与写回知识 | 否 |
| `ARCHIVED` | 已完成最终封存 | 否 |
| `CANCELLED` | 用户或治理策略取消 | 否 |

## 2.2 合法状态转换

```text
DRAFT
  → INTAKE_PENDING

INTAKE_PENDING
  → ASK_USER
  → BLOCKED
  → READY

ASK_USER
  → INTAKE_PENDING
  → CANCELLED

READY
  → PLANNED
  → ASK_USER
  → BLOCKED

PLANNED
  → RUNNING
  → BLOCKED
  → CANCELLED

RUNNING
  → RUNNING
  → COMPACT_SOON
  → VERIFYING
  → ASK_USER
  → BLOCKED
  → CANCELLED

COMPACT_SOON
  → RUNNING             # 写完 handoff 且仍有安全预算
  → RESUME_REQUIRED

RESUME_REQUIRED
  → RUNNING             # 重建验证成功
  → RESUME_REQUIRED     # 仍缺状态
  → BLOCKED

VERIFYING
  → VERIFIED
  → WARN
  → REJECTED
  → BLOCKED

WARN
  → VERIFIED            # 策略允许且残余风险被接受
  → RUNNING             # 需要补验证/修复
  → ASK_USER
  → BLOCKED

REJECTED
  → RUNNING
  → CANCELLED

VERIFIED
  → ARCHIVING

ARCHIVING
  → ARCHIVED
  → BLOCKED
```

禁止转换：

```text
✗ DRAFT → RUNNING
✗ ASK_USER → VERIFIED
✗ BLOCKED → ARCHIVED
✗ RUNNING → ARCHIVED
✗ COMPACT_SOON → VERIFIED
✗ RESUME_REQUIRED → VERIFIED
✗ Oracle ACCEPT → ARCHIVED（绕过 VerifyGate）
✗ handoff 中写“完成” → VERIFIED
```

---

# 三、任务目录与权威关系

每个任务使用以下结构：

```text
.omc/tasks/<date>/<task-id>/
├── manifest.yaml
├── state.json
├── plan.md
├── working-set.yaml
├── handoff.md
├── decisions.md
├── evidence.jsonl
├── executor.md                 # 可选人读账本，不是唯一真相源
├── context/
│   ├── capsule.current.md
│   └── receipts.jsonl
└── artifacts/
```

权威优先级：

```text
安全与权限策略
  > state.json
  > VerifyGate 结构化 verdict
  > manifest.yaml / plan.md 当前有效版本
  > ADR / Contract
  > evidence.jsonl + Artifact 原件
  > handoff.md
  > executor.md
  > Context Capsule
  > transcript / LLM summary
```

冲突处理：

```text
- handoff 与 state 冲突：以 state 为准，恢复进入 BLOCKED 或重建；
- executor 声称完成但无 evidence：不得 VERIFIED；
- plan 标 [x] 但 VerifyGate 无 verdict：撤销完成标记或标记损坏；
- summary 与 ADR 冲突：以有效 ADR 为准；
- evidence 索引与 Artifact hash 不一致：证据无效并进入 BLOCKED；
- Context Capsule 与当前 state_version 不一致：Capsule 作废并重新编译。
```

---

# 四、`manifest.yaml`：任务入口契约

## 4.1 Schema 示例

```yaml
schema_version: carros.task_manifest.v1

task:
  id: fix-auth-001
  title: 修复认证刷新竞态
  level: L1
  created_at: "2026-07-12T08:00:00Z"
  created_by: user

intent:
  goal: 修复同一用户并发刷新导致多次上游调用的问题
  non_goals:
    - 不重构完整认证模块
    - 不修改公共错误类型
  acceptance:
    - 并发刷新只触发一次上游调用
    - 既有认证测试全部通过

scope:
  allowed_paths:
    - src/auth/refresh.ts
    - tests/auth/refresh.test.ts
  denied_paths:
    - .env
    - secrets/**
    - docs/reviews/**
  external_side_effects:
    allowed: false

risk:
  level: medium
  categories:
    - auth_change
    - concurrency
  rollback_required: true

routing:
  preferred_profile: deepseek-v4-flash
  escalation_profile: opus-4.8
  oracle_required: false

references:
  documents:
    - ADR-014#single-flight
    - CONTRACT-AUTH#error-semantics

versions:
  manifest_version: 1
  state_version: 1
```

## 4.2 Manifest 不变量

```text
- `goal` 必须单一且可判断；
- `non_goals` 至少写出最可能的 scope creep；
- `acceptance` 必须可映射到 VerifyGate；
- `allowed_paths` 不能为空；
- `denied_paths` 优先于 allowed；
- 外部副作用必须显式声明；
- L1/L2 必须在 Intake 后冻结；
- 任务升级到 L2 时增加 manifest_version，并记录理由。
```

---

# 五、`state.json`：唯一运行状态

## 5.1 完整示例

```json
{
  "schema_version": "carros.task_state.v1",
  "task_id": "fix-auth-001",
  "level": "L1",
  "status": "RUNNING",
  "state_version": 7,
  "manifest_version": 1,
  "plan_version": 2,
  "current_step": "S2",
  "current_action": "A1",
  "steps": {
    "S1": {
      "status": "VERIFIED",
      "verify_verdict_id": "V-S1-003"
    },
    "S2": {
      "status": "RUNNING",
      "verify_verdict_id": null
    },
    "S3": {
      "status": "PENDING",
      "verify_verdict_id": null
    }
  },
  "blocker": null,
  "question": null,
  "context": {
    "profile": "deepseek-v4-flash",
    "turns": 8,
    "input_tokens_estimate": 7600,
    "watermark": 63,
    "decision": "CONTINUE",
    "capsule_version": 12,
    "capsule_state_version": 7
  },
  "verification": {
    "last_verdict": null,
    "residual_risks": []
  },
  "timestamps": {
    "created_at": "2026-07-12T08:00:00Z",
    "updated_at": "2026-07-12T09:20:00Z"
  }
}
```

## 5.2 并发与原子写入

状态更新必须采用 compare-and-swap 语义：

```python
def update_state(task_id: str, expected_version: int, patch: dict) -> dict:
    """
    1. 读取 state.json；
    2. 校验 state_version == expected_version；
    3. 应用受控 patch；
    4. state_version + 1；
    5. 写临时文件、fsync、原子 rename；
    6. append audit event。
    冲突时抛 StateConflict，不覆盖新状态。
    """
```

多 Agent 环境必须遵守：

```text
- 一个任务同一时间只有一个 State Writer；
- 检索/审查 Agent 只能返回 proposal；
- OpenCode 多会话不能同时写 state.json；
- Claude 子 Agent 不直接推进主任务状态；
- 所有状态转换必须记录 actor、from、to、reason、version。
```

---

# 六、IntakeGate

## 6.1 职责

IntakeGate 只回答：

```text
1. 用户要什么？
2. 目标是否足够明确？
3. scope 是否明确且安全？
4. 是否有不可逆副作用？
5. 应走 L1 还是 L2？
6. 缺失信息应 ASK_USER、BLOCKED 还是可采用安全默认值？
```

IntakeGate 不做：

```text
✗ 写具体代码；
✗ 执行工具；
✗ 宣称完成；
✗ 扫描全仓以“理解所有背景”；
✗ 默认调用 Oracle；
✗ 生成几十页方案。
```

## 6.2 Intake 输出

```json
{
  "schema_version": "carros.intake_verdict.v1",
  "task_id": "fix-auth-001",
  "verdict": "READY",
  "level": "L1",
  "goal": "修复认证刷新竞态",
  "assumptions": [],
  "missing_information": [],
  "risk_categories": ["auth_change", "concurrency"],
  "scope": {
    "allowed_paths": [
      "src/auth/refresh.ts",
      "tests/auth/refresh.test.ts"
    ],
    "denied_paths": [".env", "secrets/**", "docs/reviews/**"]
  },
  "reason": "局部修改、目标明确、可通过确定性测试验证"
}
```

合法 verdict：

```text
READY
ASK_USER
BLOCKED
REJECTED
```

其中：

- `ASK_USER`：缺少用户独有信息，例如预期行为、授权或业务取舍；
- `BLOCKED`：工具、权限、仓库状态或安全条件不满足；
- `REJECTED`：请求本身不允许执行，或违反硬约束。

## 6.3 L1 / L2 分类规则

### 默认 L1

满足多数条件：

```text
- 目标明确；
- 涉及模块 ≤2；
- 修改文件预估 ≤5；
- 可通过已有命令/文件断言验证；
- 无生产副作用；
- 无大规模迁移；
- 无需跨领域研究；
- 不需要多个独立审查者。
```

### 升级 L2

任一强条件即可升级：

```text
- 跨 3 个以上模块或涉及公共架构；
- 数据迁移、权限、支付、生产配置等高风险变更；
- 需要研究多个实现路线；
- 需要多 Agent / 多 Judge；
- 验证依赖跨系统证据；
- 预计超过 20 个执行 tick；
- 目标存在重大歧义且需要系统化研究；
- 需要新增或修改多个 ADR/Contract。
```

避免只按文件数机械分类：一个认证核心文件也可能是 L2，一个批量格式化任务即使涉及很多文件也可能仍是 L1。

## 6.4 ASK_USER 持久化

```json
{
  "status": "ASK_USER",
  "question": {
    "id": "Q-003",
    "text": "刷新失败时是否必须保留现有 RefreshError 类型？",
    "why_needed": "该选择影响公共 API 兼容性",
    "options": [
      "保留现有类型",
      "允许新增错误类型"
    ],
    "asked_at": "2026-07-12T08:05:00Z",
    "answered_at": null,
    "answer": null
  }
}
```

规则：

```text
- 问题必须单一、可回答；
- 解释为何无法安全默认；
- 用户回答写入 state/audit；
- transcript 中的“继续”不能自动当作具体确认；
- 恢复后若 question 未回答，仍保持 ASK_USER。
```

---

# 七、PlanBuilder

## 7.1 职责

PlanBuilder 把 Intake 的目标转换为可执行、可验证的 step 图。

每个 step 必须包括：

```text
- intent：该 step 唯一目的；
- inputs：允许依赖的文档/文件；
- allowed_paths：本 step 可修改范围；
- actions：原子动作；
- verify：验证规则；
- rollback：失败回退方法；
- dependencies：前置 step；
- completion：仅 VerifyGate 可更新。
```

## 7.2 `plan.md` 模板

```markdown
---
schema_version: carros.plan.v1
task_id: fix-auth-001
plan_version: 2
level: L1
status: active
---

# Plan

## Goal
修复同一用户并发刷新导致多次上游调用的问题。

## Non-goals
- 不重构完整认证模块
- 不改变公共错误类型

## S1 · 建立失败证据

- status: VERIFIED
- intent: 复现并确认并发请求会产生多次上游调用
- allowed_paths:
  - tests/auth/refresh.test.ts
- actions:
  - A1: 定位现有并发测试
  - A2: 增加或确认竞态复现断言
- verify:
  - id: V-S1-CMD-1
    type: command
    command: pnpm test tests/auth/refresh.test.ts
    expect_exit: 1
    expect_match: "received 3"
- rollback:
  - git restore tests/auth/refresh.test.ts

## S2 · 修复 single-flight 注册时机

- status: RUNNING
- depends_on: [S1]
- intent: 保证同一用户并发刷新复用同一个 promise
- allowed_paths:
  - src/auth/refresh.ts
- actions:
  - A1: 修改 refreshToken 的 in-flight promise 注册逻辑
- verify:
  - id: V-S2-CMD-1
    type: command
    command: pnpm test tests/auth/refresh.test.ts
    expect_exit: 0
  - id: V-S2-FILE-1
    type: file
    path: src/auth/refresh.ts
    assertion: public_signature_unchanged
- rollback:
  - git restore src/auth/refresh.ts

## S3 · 回归验证

- status: PENDING
- depends_on: [S2]
- intent: 确认认证模块既有行为未回归
- allowed_paths: []
- actions:
  - A1: 运行认证测试集
- verify:
  - id: V-S3-CMD-1
    type: command
    command: pnpm test tests/auth
    expect_exit: 0
```

## 7.3 Plan 不变量

```text
- 每个 step 至少一个 verify；
- action 必须可在一个 tick 内完成或安全停止；
- step 不得隐藏新增 scope；
- verify 命令不得使用无法复现的自然语言；
- 用户确认必须显式写 type: user；
- 高风险 step 必须有 rollback/checkpoint；
- plan 中的 [x]/VERIFIED 只能由 VerifyGate 写入；
- PlanBuilder 不得预先把 step 标记完成；
- 当前 Context 默认只披露 current step，不披露完整 plan。
```

## 7.4 L2 Plan 增强字段

L2 额外要求：

```yaml
research:
  questions:
    - 不同 single-flight 方案如何处理失败重试？
  required_outputs:
    - research/auth-single-flight.md

roi:
  expected_benefit: 降低重复上游调用和竞态失败
  implementation_cost: medium
  operational_risk: medium

oracle:
  required: true
  trigger: public_contract_or_concurrency_semantics_changed

memory_writeback:
  adr_required: true
  contracts_to_review:
    - CONTRACT-AUTH
```

---

# 八、PreActionGate

## 8.1 职责

每个工具调用或文件变更之前，PreActionGate 回答：

```text
- 当前状态是否允许执行？
- action 是否属于 current_step？
- 路径是否在 allowed_paths 内？
- 是否命中 denied_paths？
- 是否超过文件/行数/Context 预算？
- 是否存在不可逆外部副作用？
- 是否需要 checkpoint、用户确认或升级 L2？
```

合法裁决：

```text
ALLOW
NARROW
CHECKPOINT_FIRST
ASK_USER
DOWNGRADE_REQUIRED
BLOCK
```

## 8.2 Gate 顺序

顺序必须固定，先安全后成本：

```text
G0  state/status 是否允许执行
G1  denied_paths / secrets / 权限
G2  action 是否匹配 current_step
G3  allowed_paths 与副作用边界
G4  checkpoint / rollback 是否满足
G5  文件数、行数、命令输出预算
G6  Context disclosure 是否精确
G7  模型 profile 是否适合当前动作
```

## 8.3 决策示例

```json
{
  "schema_version": "carros.preaction_verdict.v1",
  "task_id": "fix-auth-001",
  "step": "S2",
  "action": "A1",
  "decision": "ALLOW",
  "rule": "G3_ALLOWED_PATH",
  "target": "src/auth/refresh.ts",
  "state_version": 7,
  "reason": "目标文件属于当前 step 的 allowed_paths",
  "constraints": {
    "max_files": 1,
    "max_read_lines": 200,
    "external_side_effects": false
  }
}
```

## 8.4 Context 披露门禁

当模型请求额外上下文时，不直接执行全文读取，而是发出：

```json
{
  "type": "context_request",
  "reason": "需要确认错误类型公共契约",
  "targets": [
    {
      "kind": "document_section",
      "doc_id": "CONTRACT-AUTH",
      "section": "error-semantics",
      "max_tokens": 300
    }
  ]
}
```

Gate 可返回：

```text
ALLOW：目标精确且与当前 step 直接相关
NARROW：请求过宽，要求改为 heading/symbol/range
BLOCK：reviews、secrets、整仓树或无关背景
NEW_SESSION：需要全局架构审查，转隔离会话
```

`NEW_SESSION` 在 CLI 层可映射为 `BLOCK + escalation`，避免扩充基础状态枚举。

---

# 九、Executor Ledger

## 9.1 Executor 的职责

Executor 只做三件事：

```text
1. 执行 PreActionGate 已批准的一个 action；
2. 将完整输出写入 Artifact；
3. 把结构化事实追加到 evidence.jsonl 和短 Ledger。
```

Executor 不做：

```text
✗ 自己把 step 标为 VERIFIED；
✗ 用“看起来成功”代替命令退出码；
✗ 把完整日志复制进 executor.md；
✗ 依赖模型记忆描述发生了什么；
✗ 因工具失败自动扩大 scope；
✗ 将 Oracle 意见写成基础事实。
```

## 9.2 `evidence.jsonl`

一行一个不可变事件：

```json
{"schema_version":"carros.evidence.v1","event_id":"E17","task_id":"fix-auth-001","step":"S2","action":"A1","type":"file_change","path":"src/auth/refresh.ts","artifact":"artifacts/patch-E17.diff","sha256":"abc...","state_version":8,"created_at":"2026-07-12T09:31:00Z"}
{"schema_version":"carros.evidence.v1","event_id":"E18","task_id":"fix-auth-001","step":"S2","action":"A1","type":"command_result","command":"pnpm test tests/auth/refresh.test.ts","exit_code":0,"artifact":"artifacts/test-E18.log","sha256":"def...","preview":"12 passed, 0 failed","state_version":8,"created_at":"2026-07-12T09:34:00Z"}
```

证据性质：

```text
Artifact 原文：无损可回滚/可审计
Evidence 索引：原始事实的结构化指针
确定性 preview：有界视图，原件仍在
LLM summary：有损，仅可导航
```

## 9.3 `executor.md` 的最终定位

保留 `executor.md` 只是为了人读：

```markdown
# Executor Ledger

## E17 · S2/A1 · file_change
- path: src/auth/refresh.ts
- artifact: artifacts/patch-E17.diff
- result: recorded

## E18 · S2/A1 · command_result
- command: pnpm test tests/auth/refresh.test.ts
- exit_code: 0
- preview: 12 passed, 0 failed
- artifact: artifacts/test-E18.log
```

限制：

```text
- 每条记录推荐 ≤12 行；
- 不粘贴完整 stdout/stderr；
- 不写 chain-of-thought；
- 不记录秘密；
- 不作为恢复必读全文；
- Context 最多读取相关 step 的尾部记录或 evidence 索引。
```

---

# 十、VerifyGate：唯一完成门

## 10.1 VerifyGate 回答的问题

```text
- plan 中该 step 要求哪些验证？
- evidence 中是否有对应证据？
- Artifact 是否存在且 hash 匹配？
- command/file/user 验证是否满足？
- 是否存在尚未覆盖的失败？
- 是否有残余风险？
- 能否把 step 或 task 标记为 VERIFIED？
```

VerifyGate 不接受以下完成证据：

```text
✗ “代码已经改好了”；
✗ “理论上应该可以”；
✗ 模型自己的成功描述；
✗ handoff 中的完成声明；
✗ compact summary 的历史判断；
✗ Oracle 单独给出的 ACCEPT；
✗ plan.md 预先存在的 [x]。
```

## 10.2 三类基础验证

### Command 验证

```yaml
- id: V-S2-CMD-1
  type: command
  command: pnpm test tests/auth/refresh.test.ts
  expect_exit: 0
  expect_match: "12 passed"
```

要求：

```text
- 命令文本匹配或满足规范化等价；
- exit_code 满足；
- 必要输出断言满足；
- Artifact 存在且 hash 一致；
- 证据产生时间晚于相关代码修改。
```

### File 验证

```yaml
- id: V-S2-FILE-1
  type: file
  path: src/auth/refresh.ts
  assertion: public_signature_unchanged
```

可用断言：

```text
exists
not_exists
contains
not_contains
sha256_equals
json_schema_valid
public_signature_unchanged
changed_only_within_scope
```

### User 验证

```yaml
- id: V-S4-USER-1
  type: user
  question_id: Q-007
  expected: approved
```

要求：

```text
- 必须有明确 question_id；
- 用户回答必须持久化；
- 普通“继续”不能替代 approval；
- 不能由 Agent 伪造确认。
```

## 10.3 VerifyGate verdict

最终使用：

```text
VERIFIED
WARN
BLOCKED
REJECTED
```

语义：

| Verdict | 含义 | 后续 |
|---|---|---|
| `VERIFIED` | 所有必需验证通过，无阻断风险 | step 完成；全部 step 完成后任务 VERIFIED |
| `WARN` | 基础验证通过，但存在明确残余风险 | 按策略补验证、用户接受或 L2 审查 |
| `BLOCKED` | 无法取得证据或环境不可用 | 进入 BLOCKED |
| `REJECTED` | 证据表明验证失败 | 返回 RUNNING 修复 |

## 10.4 Verdict 文件

建议每次验证写入独立 Artifact：

```json
{
  "schema_version": "carros.verify_verdict.v1",
  "verdict_id": "V-S2-005",
  "task_id": "fix-auth-001",
  "step": "S2",
  "verdict": "VERIFIED",
  "plan_version": 2,
  "state_version_before": 9,
  "checks": [
    {
      "verify_id": "V-S2-CMD-1",
      "result": "PASS",
      "evidence_event": "E18",
      "artifact": "artifacts/test-E18.log"
    },
    {
      "verify_id": "V-S2-FILE-1",
      "result": "PASS",
      "evidence_event": "E19"
    }
  ],
  "residual_risks": [],
  "created_at": "2026-07-12T09:40:00Z"
}
```

VerifyGate 成功后采用一个受控事务：

```text
1. 写 verdict Artifact；
2. append evidence event；
3. compare-and-swap 更新 state.steps[Sx]；
4. 更新 plan.md 对应 step 的 status；
5. append audit；
6. 若所有 step VERIFIED，任务 status → VERIFIED。
```

若任何一步失败，不得留下“plan 已勾选但 state 未更新”的半完成状态；需要事务日志或恢复校验修复。

---

# 十一、Context Engine 与完成语义的边界

Context Engine 允许输出：

```text
CONTINUE
COMPACT_SOON
COMPACT_NOW
RESUME_OK
RESUME_BLOCKED
DOWNGRADE_REQUIRED
```

禁止输出：

```text
DONE
VERIFIED
ACCEPTED
TRUSTED_MEMORY
SKIP_VERIFY
RESUME_FROM_CHAT_ONLY
```

明确边界：

```text
Context Engine 不回答：
- step 是否完成；
- plan 是否可标 [x]；
- evidence 是否足够；
- Oracle 是否可替代验证；
- Archive 是否可执行。

Context Engine 只负责：
- Context 水位；
- Capsule 编译；
- handoff 生成；
- compact/resume；
- 模型 profile 降级；
- 状态连续性检查。
```

恢复后 VerifyGate 必须重新计算：

```text
1. state.current_step；
2. plan 第一个非 VERIFIED step；
3. 当前 step 的有效 evidence；
4. 失败证据是否已被新证据覆盖；
5. plan/state/version 是否一致。
```

禁止 compact 后凭记忆续接或直接标完成。

---

# 十二、BLOCKED 与 Fallback 协议

## 12.1 Blocker 结构

```json
{
  "status": "BLOCKED",
  "blocker": {
    "id": "B-004",
    "type": "TOOL_UNAVAILABLE",
    "source": "VerifyGate",
    "message": "pnpm 不可用，无法执行必需测试",
    "recoverable": true,
    "required_action": "安装依赖或提供可用测试环境",
    "fallback_attempted": true,
    "fallback_result": "NO_EQUIVALENT_VERIFICATION",
    "created_at": "2026-07-12T09:45:00Z"
  }
}
```

建议 failure type：

```text
MISSING_INFORMATION
PERMISSION_DENIED
TOOL_UNAVAILABLE
DEPENDENCY_UNAVAILABLE
STATE_CONFLICT
SCOPE_VIOLATION
BUDGET_EXCEEDED
CONTEXT_CORRUPT
EVIDENCE_MISSING
VERIFY_FAILED
EXTERNAL_SIDE_EFFECT_RISK
MODEL_CAPABILITY_LIMIT
```

## 12.2 Fallback 原则

合法结果：

```text
CONTINUE
DOWNGRADE_TO_BASE
ASK_USER
BLOCKED
```

规则：

```text
- Fallback 不能降低必需验证标准；
- 不允许把“无法验证”改写成 WARN 后完成；
- 模型不可用时可切换模型，但必须重建 Capsule；
- Oracle 不可用时，若 Oracle 只是增强项可降 L1；若是风险要求则 BLOCKED；
- Hook 失败时采用 fail-closed，不是默认放行；
- 外部副作用失败不能只靠 Git 回滚声明已恢复。
```

---

# 十三、Archive + Memory Writeback

## 13.1 Archive 触发条件

只有以下条件同时满足，才允许 `VERIFIED → ARCHIVING`：

```text
- state.status == VERIFIED；
- 所有必需 step == VERIFIED；
- 每个 step 有有效 verdict_id；
- verdict Artifact 与 evidence 索引 hash 一致；
- 无 unresolved blocker；
- 无未回答的 ASK_USER；
- required memory writeback 已完成或明确标记 not_required；
- 工作区状态符合任务策略；
- 外部副作用有独立确认记录（若存在）。
```

## 13.2 Archive 输出

```text
archive/
├── final-report.md
├── manifest.final.yaml
├── state.final.json
├── plan.final.md
├── evidence.final.jsonl
├── verdicts/
├── artifacts/                    # 或内容寻址后的引用
├── memory-writeback.json
└── tombstone.json
```

`final-report.md` 模板：

```markdown
# CarrorOS Final Report

## Task
- id: fix-auth-001
- level: L1
- verdict: VERIFIED

## Goal
修复同一用户并发刷新导致多次上游调用的问题。

## Changed Files
- src/auth/refresh.ts
- tests/auth/refresh.test.ts

## Verification
- S1: VERIFIED · V-S1-003
- S2: VERIFIED · V-S2-005
- S3: VERIFIED · V-S3-002

## Residual Risks
- none

## Memory Writeback
- ADR: not_required
- Contract: reviewed, unchanged
- Runbook: not_required

## Evidence Root
- evidence.final.jsonl
```

## 13.3 Memory Writeback 分类

| 内容 | 目标 | 条件 |
|---|---|---|
| 架构选择 | `docs/adr/` | 长期有效且有替代方案权衡 |
| 接口/状态约束 | `docs/contracts/` | 影响公共契约或自动校验 |
| 操作流程 | `docs/runbooks/` | 可重复操作或故障恢复 |
| 项目限制 | `docs/project/constraints.md` | 跨任务长期有效 |
| 一次性任务事实 | 任务 Archive | 不进入全局知识库 |
| 外部模型建议原文 | `docs/reviews/` | 参考材料，不是规范 |
| 失败模式 | Error DNA / runbook | 可复现且有治理价值 |

写回必须包含来源：

```yaml
source_task: fix-auth-001
source_verdicts:
  - V-S2-005
source_commit: abc1234
authority: normative
status: active
```

## 13.4 Tombstone 裁决

归档后不直接删除所有任务状态。保留轻量 tombstone：

```json
{
  "schema_version": "carros.task_tombstone.v1",
  "task_id": "fix-auth-001",
  "final_status": "ARCHIVED",
  "archive_path": ".omc/archive/2026-07/fix-auth-001",
  "final_state_version": 14,
  "evidence_root_sha256": "...",
  "archived_at": "2026-07-12T10:10:00Z"
}
```

这属于**无损可审计**治理。原始 Artifact 的保留期可按组织策略配置，但不能在归档事务完成前删除。

---

# 十四、L1 完整运行示例

```bash
# 1. 创建任务
python3 .claude/scripts/carros_base.py init \
  --task-id fix-auth-001 \
  --level L1

# 2. Intake
python3 .claude/scripts/carros_base.py intake \
  --task-id fix-auth-001

# 3. 构建并检查计划
python3 .claude/scripts/carros_base.py plan \
  --task-id fix-auth-001
python3 .claude/scripts/carros_base.py lint \
  --task-id fix-auth-001

# 4. 查看最小状态
python3 .claude/scripts/carros_base.py status \
  --task-id fix-auth-001 --hot

# 5. 编译本轮 Context
python3 .claude/scripts/carros_base.py context compile \
  --task-id fix-auth-001 \
  --profile deepseek-v4-flash

# 6. 获取一个 action
python3 .claude/scripts/carros_base.py tick \
  --task-id fix-auth-001

# 7. 工具执行由 Gate 约束，输出自动进入 artifacts/evidence

# 8. 验证当前 step
python3 .claude/scripts/carros_base.py verify \
  --task-id fix-auth-001 --step S2

# 9. 所有 step 通过后归档
python3 .claude/scripts/carros_base.py archive \
  --task-id fix-auth-001
```

L1 正常回合：

```text
status --hot
  → context compile
  → tick
  → PreActionGate
  → 一个 action
  → Artifact + evidence
  → 必要时 verify
  → 下一个 tick
```

---

# 十五、L2 完整运行示例

```bash
python3 .claude/scripts/carros_enhance.py init \
  --task-id auth-architecture-001

python3 .claude/scripts/carros_enhance.py intake \
  --task-id auth-architecture-001

python3 .claude/scripts/carros_enhance.py research \
  --task-id auth-architecture-001

python3 .claude/scripts/carros_enhance.py plan \
  --task-id auth-architecture-001

python3 .claude/scripts/carros_enhance.py execute \
  --task-id auth-architecture-001 --next

python3 .claude/scripts/carros_enhance.py verify \
  --task-id auth-architecture-001

python3 .claude/scripts/carros_enhance.py oracle \
  --task-id auth-architecture-001 --if-required

python3 .claude/scripts/carros_enhance.py archive \
  --task-id auth-architecture-001
```

隔离轨道：

```text
主执行会话：只持有 Context Capsule
研究会话：输出 Knowledge Patch
审查会话：输出 Review Verdict
验证会话：输出 Evidence Reference
治理会话：监控 cost/context/cache，不写业务状态
```

单一写入原则：

```text
只有主执行轨或专用 State Writer 可以更新 state.json；
其它会话只能产出 proposal/artifact，由主轨接纳后写入。
```

---

# 十六、核心 Python 接口冻结

本章只冻结接口，完整代码在第 6/8 部分给出。

```python
# task_store.py

def create_task(task_id: str, level: str, seed: dict) -> dict: ...
def load_manifest(task_id: str) -> dict: ...
def load_state(task_id: str) -> dict: ...
def update_state(task_id: str, expected_version: int, patch: dict) -> dict: ...

# intake_gate.py

def evaluate_intake(request: dict, repo_facts: dict) -> dict: ...

# plan_builder.py

def build_plan(manifest: dict, research_refs: list[dict] | None = None) -> str: ...
def validate_plan(plan_text: str, manifest: dict) -> list[dict]: ...

# preaction_gate.py

def decide_action(task_id: str, action: dict, context_request: dict | None = None) -> dict: ...

# artifact_store.py

def store_artifact(task_id: str, kind: str, content: bytes, meta: dict) -> dict: ...
def append_evidence(task_id: str, event: dict) -> dict: ...

# verify_gate.py

def verify_step(task_id: str, step_id: str) -> dict: ...
def verify_task(task_id: str) -> dict: ...

# archive.py

def preflight_archive(task_id: str) -> list[dict]: ...
def archive_task(task_id: str) -> dict: ...
```

所有改变治理事实的函数必须：

```text
- 读取 expected state_version；
- 使用原子写入；
- 记录 audit；
- 返回结构化 verdict；
- 不依赖聊天文本中的隐含状态。
```

---

# 十七、可观测指标

## 17.1 主治理链

```text
intake_ready_rate
ask_user_resolution_latency
plan_lint_failure_rate
preaction_block_rate_by_rule
scope_violation_attempts
steps_per_task
verify_pass_rate_first_attempt
verify_rejection_rate
archive_preflight_failure_rate
state_conflict_rate
```

## 17.2 证据健康度

```text
evidence_with_artifact_rate = 100%（要求原件的类型）
artifact_hash_mismatch_rate = 0
steps_without_verdict_id = 0（VERIFIED step）
full_tool_output_in_executor_rate = 0
unresolved_failure_evidence_rate = 0（归档时）
```

## 17.3 连续性

```text
resume_without_transcript_success_rate ≥ 95%
state_plan_consistency_rate = 100%
capsule_state_version_mismatch_rate < 1%，发现即重编译
compact_to_verify_bypass_count = 0
handoff_claim_used_as_verification = 0
```

---

# 十八、本部分验收矩阵

| ID | 验收项 | 通过标准 |
|---|---|---|
| W-01 | 状态转换 | 非法转换全部拒绝 |
| W-02 | ASK_USER | 问题持久化，恢复后仍阻塞 |
| W-03 | Scope | denied 路径即使同时 allowed 也 BLOCK |
| W-04 | Plan | 每个 step 至少一条 verify |
| W-05 | Evidence | 完整日志只在 Artifact，不进 Ledger |
| W-06 | Verify | 无证据的“已完成”返回 REJECTED/BLOCKED |
| W-07 | Compact | Context Engine 不能输出 VERIFIED |
| W-08 | Resume | handoff 与 state 冲突时不继续执行 |
| W-09 | Archive | 非 VERIFIED 任务无法归档 |
| W-10 | Concurrency | state_version 冲突不覆盖新状态 |
| W-11 | L2 隔离 | 子 Agent 不直接写主状态 |
| W-12 | Writeback | 长期决策带来源和 authority |

最低自动测试：

```python
def test_handoff_cannot_verify(): ...
def test_oracle_cannot_bypass_verify_gate(): ...
def test_denied_path_wins(): ...
def test_archive_requires_verified(): ...
def test_state_compare_and_swap(): ...
def test_artifact_hash_is_verified(): ...
def test_context_engine_has_no_done_verdict(): ...
def test_resume_recomputes_current_step(): ...
def test_verified_step_requires_verdict_id(): ...
def test_executor_does_not_store_full_log(): ...
```

---

# 十九、本部分最终裁决

```text
1. L1 使用 Intake/Plan → Execute → Verify/Archive 三阶段；
2. L2 增加 Research、Oracle 与完整 Memory Writeback，但保持主 Context 隔离；
3. state.json 是唯一运行状态源；
4. manifest 定义目标与边界，plan 定义可验证步骤；
5. PreActionGate 在每个动作前执行安全与预算裁决；
6. Executor 只产生 Artifact 和 Evidence，不制造完成事实；
7. VerifyGate 是唯一完成门；
8. Context Engine 只能维护连续性，禁止输出 DONE/VERIFIED；
9. Archive 只接受 VERIFIED，且必须完成证据封存与知识写回；
10. ASK_USER、BLOCKED、WARN、REJECTED 均必须持久化，不能只留在聊天中。
```

---

# 下一部分：第 3/8 部分

将完整输出 **文档记忆系统（Memory Plane）**：

```text
- docs/INDEX.yaml 最终 Schema
- 文档 authority / status / freshness
- ADR、Contract、Runbook、Review 的职责边界
- 文档 heading 级稳定地址
- Project Memory 与 Task Memory 分层
- 决策何时写入 ADR，何时只留任务归档
- Knowledge Patch 协议
- 文档写回事务
- stale / conflict / supersede 处理
- 文档系统如何支持 Claude Code 与 OpenCode
- 可直接建立的完整目录与模板
- Memory Plane 验收测试
```

