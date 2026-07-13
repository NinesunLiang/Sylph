# CarrorOS 最终整合重构方案
## 第 3/8 部分：文档记忆系统（Memory Plane）

本部分承接第 1/8 的四平面架构与第 2/8 的任务状态协议，冻结 CarrorOS 的长期记忆系统：

> **文档负责保存可复用知识，任务文件负责保存运行事实，Artifact 负责保存原始证据；Context 只保存本轮需要的临时工作集。**

本章完成后，CarrorOS 必须能够在不读取旧 transcript 的情况下，通过文档索引、任务状态和精确片段恢复执行。

---

# 一、Memory Plane 的职责边界

## 1.1 四类载体

```text
Project Memory   项目级长期知识：docs/**
Task Memory      当前任务状态与决策：.omc/tasks/**
Evidence Store   原始执行证据：artifacts/** + evidence.jsonl
Audit Trail      治理行为记录：.omc/audit/**、OpenCode SQLite、Claude transcript
```

| 载体 | 保存内容 | 是否是真相源 | 是否默认入模 |
|---|---|---:|---:|
| `docs/architecture/**` | 当前有效架构 | 是 | 否，按 section 披露 |
| `docs/contracts/**` | 接口、Schema、不变量 | 是 | 按需 |
| `docs/adr/**` | 已裁决的架构决策 | 是 | 按需 |
| `docs/runbooks/**` | 操作和恢复流程 | 是 | 按需 |
| `docs/reviews/**` | 外部模型建议与历史审核 | 否，参考材料 | 默认禁止 |
| `manifest.yaml` | 任务目标、scope、等级 | 是 | 切片 |
| `state.json` | 当前运行状态 | 是，唯一运行状态源 | 必要字段 |
| `plan.md` | 当前有效计划 | 是 | 仅当前 step |
| `handoff.md` | 跨会话恢复摘要 | 次级来源 | 恢复时读取 |
| `decisions.md` | 尚未升级为全局 ADR 的任务决策 | 是，任务内 | 按需 |
| `evidence.jsonl` | 证据索引 | 是 | 相关记录 |
| `artifacts/**` | 原始日志、patch、报告 | 原始证据 | 默认不入模 |
| transcript | 会话审计 | 否 | 正常恢复禁止 |
| LLM summary | 导航摘要 | 否 | 仅辅助定位 |

## 1.2 三条硬边界

```text
MEM-01  文档不是 Prompt：存在 docs/ 不代表应加载全文。
MEM-02  摘要不是事实：摘要不得覆盖 ADR、Contract、state 或 Artifact。
MEM-03  Transcript 不是恢复源：正常 resume 不加载旧会话全文。
```

---

# 二、最终目录结构

```text
docs/
├── INDEX.yaml
├── project/
│   ├── INDEX.yaml
│   ├── overview.md
│   ├── constraints.md
│   └── glossary.md
├── architecture/
│   ├── INDEX.yaml
│   ├── governance-runtime.md
│   ├── context-engine.md
│   └── verify-gate.md
├── contracts/
│   ├── INDEX.yaml
│   ├── task-state.md
│   ├── evidence.md
│   ├── context-capsule.md
│   └── cli.md
├── adr/
│   ├── INDEX.yaml
│   ├── ADR-001-document-first-memory.md
│   └── ADR-002-compaction-boundary.md
├── runbooks/
│   ├── INDEX.yaml
│   ├── token-governance.md
│   ├── resume.md
│   └── context-overflow.md
├── generated/
│   ├── repo-map.json
│   ├── symbol-index.json
│   └── dependency-map.json
└── reviews/
    ├── INDEX.yaml
    ├── grok/
    ├── opus/
    ├── deepseek/
    └── gpt/
```

任务级记忆：

```text
.omc/tasks/<date>/<task-id>/
├── manifest.yaml
├── state.json
├── plan.md
├── working-set.yaml
├── handoff.md
├── decisions.md
├── evidence.jsonl
├── context/
│   ├── capsule.current.md
│   └── receipts.jsonl
└── artifacts/
```

冻结原则：

```text
- `docs/**` 保存跨任务可复用知识；
- `.omc/tasks/**` 保存单任务事实；
- 不把一次性执行日志升级为项目知识；
- 不把长期架构约束永久留在任务归档里；
- `reviews/**` 永远不能自动升级为规范。
```

---

# 三、文档类型与权威级别

## 3.1 文档类型

### Project

用于稳定项目背景：

```text
overview      系统是什么
constraints   全局硬限制
 glossary      术语与命名
```

### Architecture

描述当前系统如何组成、模块如何协作。它回答“现在怎么设计”，但不必重复所有决策过程。

### ADR

记录重要决策及取舍。它回答“为什么这样决定”。ADR 一旦接受，不直接重写历史；通过 supersede 形成演进链。

### Contract

机器或人可验证的公共约束：CLI、状态转换、Schema、事件格式、权限边界。

### Runbook

描述可重复执行的操作：安装、恢复、故障处理、上下文溢出响应。

### Review

保存 Grok、Opus、DeepSeek、GPT 或人工审核原文。它是输入材料，不是最终规范。

### Generated

由工具生成的 repo map、symbol index、依赖图。可重建，不应人工维护为真相。

## 3.2 Authority 枚举

```text
normative      当前强制规范
approved       已接受但非强制契约
informative    说明材料
advisory       外部建议或审查意见
generated      自动生成索引
historical     历史资料，不再适用
```

权威优先级：

```text
安全策略
  > normative Contract
  > accepted ADR
  > normative Architecture
  > approved Runbook
  > informative Project docs
  > advisory Review
  > historical 内容
```

注意：`state.json` 的当前任务运行事实不受文档 authority 排序替代。

## 3.3 Status 枚举

```text
draft
proposed
active
deprecated
superseded
archived
invalid
```

合法组合示例：

```text
Contract: authority=normative, status=active
ADR:      authority=approved,  status=active
Review:   authority=advisory,  status=archived
Repo map: authority=generated, status=active
```

禁止：

```text
- advisory Review 标为 normative；
- superseded 文档继续被 Context Compiler 默认检索；
- draft Contract 覆盖 active Contract；
- generated 文件承载无法重建的人工决策。
```

---

# 四、稳定文档地址

长期记忆必须可以精确引用，而不是只引用文件路径。

最终引用格式：

```text
<DOC-ID>#<SECTION-ID>@<REVISION>
```

示例：

```text
ADR-001#decision@abc1234
CONTRACT-STATE#legal-transitions@v3
ARCH-CONTEXT#progressive-disclosure@2026-07-12
```

其中 revision 可以是：

```text
Git commit
内容 hash
文档 version
已验证日期
```

## 4.1 Heading ID

Markdown 标题必须提供稳定 section ID。推荐显式锚点：

```markdown
## 渐进式披露 {#progressive-disclosure}
```

若渲染器不支持显式锚点，则在 front matter 中维护：

```yaml
sections:
  - id: progressive-disclosure
    heading: 渐进式披露
  - id: context-capsule
    heading: Context Capsule
```

禁止长期使用行号作为唯一地址；行号只能是索引加速提示，因为文档修改会导致漂移。

---

# 五、统一文档头部规范

所有受治理文档必须包含 front matter：

```markdown
---
schema_version: carros.document.v1
id: ARCH-CONTEXT
title: CarrorOS Context Engine
type: architecture
authority: normative
status: active
version: 3
owners:
  - carros-core
created_at: 2026-07-12
updated_at: 2026-07-12
last_verified_commit: abc1234
supersedes: []
superseded_by: null
depends_on:
  - ADR-001
  - CONTRACT-STATE
tags:
  - context
  - memory
  - compaction
summary: CarrorOS 文档记忆、渐进披露、Context 编译与恢复规范。
sections:
  - id: invariants
    heading: 系统不变量
  - id: progressive-disclosure
    heading: 渐进式披露
  - id: context-capsule
    heading: Context Capsule
---

# CarrorOS Context Engine

## 系统不变量 {#invariants}

- 文档负责长期记忆；
- Context 是可丢弃缓存；
- Transcript 不是正常恢复入口。
```

## 5.1 必填字段

```text
schema_version
id
title
type
authority
status
version
owners
updated_at
summary
sections
```

## 5.2 Freshness 字段

```text
last_verified_commit
verified_against
expires_at            # 可选；适合 provider/API 文档
freshness_policy      # commit / duration / manual
```

示例：

```yaml
freshness_policy:
  mode: commit
  watched_paths:
    - .claude/scripts/lib/context_engine.py
    - docs/contracts/context-capsule.md
```

当 watched path 在 `last_verified_commit` 后发生变化，索引将文档标记为 `possibly_stale`，但不自动篡改文档 status。

---

# 六、`docs/INDEX.yaml` 最终 Schema

```yaml
schema_version: carros.document_index.v1
generated_at: "2026-07-12T10:00:00Z"
repository_revision: abc1234

policies:
  default_disclosure: index_only
  full_document_requires_reason: true
  deny_by_default:
    - docs/reviews/**
  authority_precedence:
    - normative
    - approved
    - informative
    - advisory
    - historical

entries:
  - id: ARCH-CONTEXT
    path: docs/architecture/context-engine.md
    type: architecture
    authority: normative
    status: active
    version: 3
    summary: 文档记忆、渐进披露、Context 编译与恢复协议。
    tags: [context, memory, compaction]
    owners: [carros-core]
    sections:
      - id: invariants
        heading: 系统不变量
        byte_range: [920, 1510]
        estimated_tokens: 180
      - id: progressive-disclosure
        heading: 渐进式披露
        byte_range: [1511, 5100]
        estimated_tokens: 960
      - id: context-capsule
        heading: Context Capsule
        byte_range: [5101, 8400]
        estimated_tokens: 820
    estimated_tokens:
      summary: 80
      full: 4200
    depends_on:
      - ADR-001
      - CONTRACT-STATE
    last_verified_commit: abc1234
    freshness: fresh
    content_sha256: "..."

  - id: REVIEW-OPUS-CONTEXT
    path: docs/reviews/opus/context-cost-improve.md
    type: review
    authority: advisory
    status: archived
    summary: Opus 对 Context 成本治理的外部建议。
    tags: [review, context]
    disclosure:
      default: denied
      require_explicit_user_request: true
    estimated_tokens:
      summary: 90
      full: 18000
```

## 6.1 INDEX 规则

```text
- INDEX 可以自动生成，但其来源是文档 front matter；
- INDEX 不得修改正文事实；
- 同一 id 只能对应一个 active 文档；
- active 文档的 content_sha256 必须匹配；
- section 的 byte range 只是优化，读取后必须校验 heading；
- 索引损坏时退化为 front matter 扫描，而不是加载所有正文；
- reviews 必须显式标记 default=denied。
```

## 6.2 子索引

目录可有局部 `INDEX.yaml`，全局索引只保存摘要：

```text
docs/INDEX.yaml                 全局入口
docs/architecture/INDEX.yaml    架构文档详细索引
docs/adr/INDEX.yaml             ADR 状态和 supersede 链
docs/reviews/INDEX.yaml         仅元数据，默认拒绝正文
```

这避免全局索引本身再次膨胀。

---

# 七、ADR 最终模板与升级条件

## 7.1 何时必须写 ADR

满足任一条件：

```text
- 存在两个以上可行方案，且取舍会长期影响系统；
- 改变跨模块边界或公共接口；
- 改变安全、权限、状态、压缩或恢复语义；
- 后续维护者很可能重新质疑该决定；
- 决策需要覆盖多个未来任务；
- 推翻已有 ADR。
```

不应写 ADR：

```text
- 一次性 bug 修复细节；
- 普通变量命名；
- 工具日志；
- 尚未验证的模型建议；
- 仅对当前任务有效的临时选择。
```

这些留在 `decisions.md` 或任务归档。

## 7.2 ADR 模板

```markdown
---
schema_version: carros.document.v1
id: ADR-001
title: 使用 Document-First Memory
 type: adr
authority: approved
status: active
version: 1
owners: [carros-core]
created_at: 2026-07-12
updated_at: 2026-07-12
last_verified_commit: abc1234
supersedes: []
superseded_by: null
depends_on: []
tags: [memory, context]
summary: 文档是持久记忆，Context 仅为可重建缓存。
sections:
  - id: context
    heading: 背景
  - id: decision
    heading: 决策
  - id: consequences
    heading: 后果
---

# ADR-001：使用 Document-First Memory

## 背景 {#context}

CarrorOS 将项目知识、任务状态和工具历史持续注入 Prompt，导致每轮 35K～320K token。

## 决策 {#decision}

- 文档系统保存长期知识；
- state.json 保存任务运行状态；
- Artifact 保存原始证据；
- Context 每轮重新编译；
- transcript 不作为正常恢复源。

## 被否决方案

### 全 transcript 恢复

否决原因：成本线性增长，状态不可验证。

### 仅依赖 LLM 摘要

否决原因：有损且不可作为事实源。

## 后果 {#consequences}

正面：可恢复、可审计、成本稳定。

负面：需要维护索引、文档新鲜度和写回协议。

## 来源

- task: carros-context-rewrite-001
- verdict: V-S4-008
- commit: abc1234
```

## 7.3 Supersede

不得重写旧 ADR 的历史决策；创建新 ADR：

```yaml
# 新 ADR
id: ADR-008
supersedes: [ADR-001]

# 旧 ADR
status: superseded
superseded_by: ADR-008
```

Context Compiler 默认只检索新 ADR；如果任务涉及迁移原因，可披露旧 ADR 的摘要而非全文。

---

# 八、Contract 最终模板

Contract 必须优先使用可测试表达。

```markdown
---
schema_version: carros.document.v1
id: CONTRACT-STATE
title: Task State Contract
type: contract
authority: normative
status: active
version: 3
owners: [carros-core]
updated_at: 2026-07-12
summary: CarrorOS 任务状态字段、转换和并发写入规则。
sections:
  - id: schema
    heading: Schema
  - id: legal-transitions
    heading: 合法转换
  - id: invariants
    heading: 不变量
---

# Task State Contract

## Schema {#schema}

`state.json` 必须符合 `carros.task_state.v1`。

## 合法转换 {#legal-transitions}

```text
DRAFT → INTAKE_PENDING
...
```

## 不变量 {#invariants}

- `state_version` 单调递增；
- 写入采用 compare-and-swap；
- `VERIFIED` step 必须有 `verify_verdict_id`；
- Context Engine 不得写入 `VERIFIED`。
```

Contract 改动要求：

```text
- 增加 version；
- 更新依赖文档的 freshness；
- 更新对应 Schema/测试；
- 兼容性破坏必须有迁移说明和 ADR；
- 未通过 Contract 测试不得标 active。
```

---

# 九、Runbook 最终模板

```markdown
---
schema_version: carros.document.v1
id: RUNBOOK-CONTEXT-OVERFLOW
title: Context Overflow Response
type: runbook
authority: approved
status: active
version: 1
owners: [carros-ops]
updated_at: 2026-07-12
summary: 上下文超过硬水位时的停止、handoff 和恢复步骤。
sections:
  - id: triggers
    heading: 触发条件
  - id: procedure
    heading: 处置步骤
  - id: verification
    heading: 恢复验证
---

# Context Overflow Response

## 触发条件 {#triggers}

- Context 超过 profile hard limit；
- Capsule 无法在保留硬约束后完成编译；
- Claude 即将触发 L5；
- OpenCode prune 后仍无安全空间。

## 处置步骤 {#procedure}

1. 停止新 action；
2. 原子更新 state 为 `RESUME_REQUIRED`；
3. 生成 handoff；
4. 校验 Required Reads；
5. 开新会话并重建 Capsule。

## 恢复验证 {#verification}

- state_version 一致；
- current_step 重新计算；
- 不读取旧 transcript；
- 不跳过 VerifyGate。
```

Runbook 不能偷偷修改 Contract；若流程与 Contract 冲突，以 Contract 为准并触发文档冲突告警。

---

# 十、Review 隔离协议

外部模型建议统一进入：

```text
docs/reviews/<source>/<document>.md
```

Review front matter：

```yaml
id: REVIEW-GPT-CONTEXT-20260712
type: review
authority: advisory
status: archived
source:
  model: gpt-5.6-sol
  retrieved_at: 2026-07-12
  original_file: gpt-5.6-sol_context_cost_improve.md
disclosure:
  default: denied
  require_explicit_user_request: true
promoted_claims:
  - target: ADR-001#decision
    status: accepted_with_rewrite
```

规则：

```text
- Review 原文不进入 Stable Core；
- Review 不进入默认检索集合；
- “模型说过”不是权威来源；
- 接受的结论必须重写进 ADR/Contract/Architecture；
- 最终规范引用 Review 时，应同时引用被接受后的规范地址；
- 多模型重复建议不能自动提升 authority。
```

这解决“全面审核内容每轮重复注入”的根因。

---

# 十一、任务级 `decisions.md`

并非所有决策都应立即升级为 ADR。任务内使用：

```markdown
---
schema_version: carros.task_decisions.v1
task_id: fix-auth-001
---

# Task Decisions

## D-001 · 保留现有 RefreshError

- status: accepted
- scope: task
- reason: 避免公共 API 破坏
- source: user/Q-003
- affects:
  - src/auth/refresh.ts
- promote_to_adr: false
- created_at: 2026-07-12T08:10:00Z
```

升级判断：

```text
任务结束时 Memory Writeback 扫描 decisions：
- 仅本任务有效 → 留 Archive；
- 跨任务长期有效 → ADR/Contract 候选；
- 未验证猜测 → 不升级；
- 已被推翻 → 标 rejected，保留审计；
- 涉及秘密 → 不写文档正文，只保留脱敏引用。
```

---

# 十二、Knowledge Patch：隔离 Agent 的唯一回传格式

检索、研究或审查 Agent 不能把完整探索历史返回主会话，只能返回结构化补丁。

```yaml
schema_version: carros.knowledge_patch.v1
patch_id: KP-018
request_id: CR-011
producer:
  type: retrieval_agent
  session_id: retrieval-20260712-01
status: complete

sources:
  - ref: ADR-014#single-flight@abc1234
    authority: approved
    freshness: fresh
    content_sha256: "..."
  - ref: CONTRACT-AUTH#error-semantics@v4
    authority: normative
    freshness: fresh
    content_sha256: "..."

claims:
  - id: C1
    text: 同一用户并发 refresh 必须复用一个 in-flight promise。
    source_ref: ADR-014#single-flight@abc1234
    confidence: sourced
  - id: C2
    text: 修改不得改变 RefreshError 公共类型。
    source_ref: CONTRACT-AUTH#error-semantics@v4
    confidence: sourced

conflicts: []
unknowns: []
recommended_disclosure:
  max_tokens: 300
  include_claims: [C1, C2]
```

## 12.1 Knowledge Patch 约束

```text
- 每条 claim 必须有 source_ref，或显式标记 unsourced；
- unsourced claim 不能进入 normative 文档；
- 不返回 chain-of-thought；
- 不粘贴全文文档；
- 主 Agent 校验 source hash 后才能使用；
- Patch 不直接修改 state；
- 冲突不得由检索 Agent私自裁决。
```

Claude Code：通过 fresh-context subagent 生成 Patch。

OpenCode：通过独立 retrieval/review session 生成 Patch，主执行会话是唯一状态写入者。

---

# 十三、文档写回事务

Memory Writeback 发生在：

```text
- L1：Verify 后、Archive 前；
- L2：Verify/Oracle 后、Archive 前；
- 长任务中间：只有明确的 durable decision 才可提前写回。
```

## 13.1 写回流程

```text
1. COLLECT
   从 verified task 提取决策、契约变化、runbook 变化。

2. CLASSIFY
   分类为 ADR / Contract / Architecture / Runbook / Task-only。

3. PROPOSE
   生成 writeback proposal，不直接覆盖规范。

4. VALIDATE
   校验来源 verdict、Artifact、scope、文档 Schema、链接。

5. APPLY
   写临时文件，更新版本和 supersede 链。

6. REINDEX
   重建局部 INDEX，更新 hash/token estimate/freshness。

7. TEST
   跑链接、唯一 ID、Contract、索引一致性测试。

8. COMMIT
   原子提交文档和索引；写 memory-writeback evidence。

9. RECEIPT
   记录写入了什么、来源是什么、谁批准。
```

## 13.2 Writeback Proposal

```yaml
schema_version: carros.memory_writeback.v1
writeback_id: MW-009
source_task: fix-auth-001
source_verdicts: [V-S2-005, V-S3-002]
proposals:
  - action: update
    target: CONTRACT-AUTH#error-semantics
    reason: 明确 single-flight 不改变错误类型
    authority: normative
    patch_artifact: artifacts/memory-patch-MW-009.diff
  - action: retain_task_only
    source_decision: D-002
    reason: 仅为本次测试夹具选择
status: proposed
```

## 13.3 原子性

必须避免“正文更新但 INDEX 未更新”：

```text
- 先在 staging 目录生成文档和索引；
- 全部 lint/test 通过后统一 rename 或 Git commit；
- 失败则保留 proposal 和 patch Artifact；
- active 文档不可处于无索引状态；
- 写回失败时任务进入 ARCHIVING/BLOCKED，不能假装 ARCHIVED。
```

---

# 十四、冲突、过期与失效处理

## 14.1 冲突类型

```text
ID_CONFLICT            同一 ID 对应多个 active 文档
AUTHORITY_CONFLICT     同权威文档给出互斥规范
REVISION_CONFLICT      引用 revision 与正文不匹配
FRESHNESS_CONFLICT     文档依赖代码已改变
STATE_DOC_CONFLICT     当前任务状态与文档假设冲突
SUPERSEDE_BROKEN       superseded_by 链断裂
SOURCE_MISSING         claim 来源不存在
```

## 14.2 裁决规则

```text
- 不自动把最新时间戳当作正确；
- 不让 LLM 静默合并 normative 冲突；
- 同权威冲突进入 BLOCKED 或新 ADR；
- stale 文档可作为背景，但必须标记，不可用于关键验证；
- superseded 文档默认排除；
- source hash 不匹配时重新检索；
- Review 与 Contract 冲突时忽略 Review，除非用户明确发起重构任务。
```

## 14.3 Freshness 状态

```text
fresh
possibly_stale
stale
unknown
```

Context Capsule 中必须显示非 fresh 来源：

```text
[STALE] ARCH-CONTEXT#budget-policy@abc1234
原因：context_engine.py 在该 commit 后发生修改
```

关键安全、权限、状态机操作不得仅依赖 stale 文档。

---

# 十五、Document Retrieval API

完整实现放在第 6/8，本章冻结接口。

```python
# document_index.py

def build_index(root: str = "docs") -> dict:
    """扫描 front matter，生成全局/局部索引；不调用 LLM。"""

def load_index(path: str = "docs/INDEX.yaml") -> dict: ...

def resolve_doc(doc_id: str, require_active: bool = True) -> dict:
    """返回唯一文档元数据；冲突时 fail closed。"""

def resolve_section(doc_id: str, section_id: str) -> dict:
    """按稳定 heading 提取片段并校验内容 hash。"""

def search_index(
    tags: list[str] | None = None,
    doc_type: str | None = None,
    authority: list[str] | None = None,
    query: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """只搜索索引元数据；Base 默认不做正文语义检索。"""

def check_freshness(doc_id: str, repo_revision: str) -> dict: ...

def validate_index(index: dict) -> list[dict]: ...
```

文档读取门禁：

```python
def authorize_disclosure(
    doc_id: str,
    section_id: str | None,
    task_id: str,
    reason: str,
    max_tokens: int,
) -> dict:
    """
    返回 ALLOW / NARROW / BLOCK / NEW_SESSION。
    reviews 默认 BLOCK；全文必须有显式理由。
    """
```

---

# 十六、Claude Code 路径

Claude Code 侧采用：

```text
CLAUDE.md                   只保留 Slim Runtime Contract
@docs/INDEX.yaml            仅在需要检索项目知识时读取
精确 section                通过脚本提取，不 cat 全文
subagent                    隔离研究/全局审查
transcript                  审计兜底，不用于正常 resume
CLAUDE.md / auto memory     只保存稳定入口，不复制任务状态
```

## 16.1 Prompt Cache 约束

文档记忆系统必须保护稳定前缀：

```text
- CLAUDE.md 内容和顺序保持稳定；
- 不把动态任务状态写回 CLAUDE.md；
- Context Capsule 的高变内容放在稳定前缀之后；
- 同一 section 使用确定性格式和内容 hash；
- 同一 Artifact preview 原样复用；
- 避免每轮重新生成措辞不同但语义相同的摘要。
```

可观测指标：

```text
prompt_cache_hit_rate ≥ 70%，目标 ≥85%
stable_prefix_hash_changes/session ≈ 0
same_section_render_hash_match_rate = 100%
review_content_in_system_count = 0
```

## 16.2 Checkpoint 边界

```text
文档/Git 文件修改：可通过 checkpoint + Git 回滚
外部副作用：不能仅靠 checkpoint 回滚
Artifact：追加式保存，不因 Context 裁剪丢失
LLM 摘要：有损不可逆，不能覆盖文档原件
```

---

# 十七、OpenCode 路径

OpenCode 侧采用：

```text
SQLite transcript             审计链
.omc/tasks/**                 CarrorOS 任务真相
 docs/**                       项目长期知识
独立 execute/retrieve/review   多会话隔离
Prune(hidden)                 优先于有损摘要
```

冻结规则：

```text
- SQLite 有记录不等于 Context 应加载；
- non-destructive prune 用于审计回溯，不作为任务状态文件；
- 最近两回合与 skill 输出受保护，但不替代 handoff；
- 隐藏摘要 Agent 的输出是有损导航；
- 多会话只允许一个 State Writer；
- Review 会话不能直接更新 normative 文档，必须提交 Writeback Proposal。
```

建议会话：

```text
/session execute   主执行与唯一状态写入
/session retrieve  文档/代码检索，只产 Knowledge Patch
/session review    Patch/Contract 审查，只产 Verdict
/session govern    成本和审计，只读
```

可观测指标：

```text
prune_before_summary_rate = 100%
lossy_summary_as_authority_count = 0
multi_session_state_write_conflicts = 0
knowledge_patch_source_valid_rate = 100%
SQLite audit retention 按组织策略达标
```

---

# 十八、文档系统配置

```yaml
# .omc/document-policy.yaml
schema_version: carros.document_policy.v1

roots:
  project_memory: docs
  task_memory: .omc/tasks

index:
  global: docs/INDEX.yaml
  auto_rebuild: true
  validate_content_hash: true

retrieval:
  default_level: index
  max_index_results: 10
  prefer_section: true
  full_document_requires_reason: true
  reject_stale_for_critical_actions: true

access:
  denied_by_default:
    - docs/reviews/**
    - .env
    - secrets/**
  review_access:
    require_explicit_user_request: true
    allow_in_execution_context: false

writeback:
  require_verified_task: true
  require_source_verdict: true
  atomic: true
  rebuild_index: true
  run_contract_tests: true

freshness:
  mark_stale_on_dependency_change: true
  default_unknown_is_usable: false
```

---

# 十九、Memory Plane 可观测指标

## 19.1 检索质量

| 指标 | 目标 |
|---|---:|
| `index_lookup_success_rate` | ≥99% |
| `section_resolution_success_rate` | ≥99% |
| `full_document_load_rate` | <2% |
| `review_disclosure_without_override` | 0 |
| `average_sections_per_turn` | Flash ≤3；高阶 ≤6 |
| `unresolved_source_reference_rate` | 0 |

## 19.2 文档健康

| 指标 | 目标 |
|---|---:|
| `duplicate_active_doc_id` | 0 |
| `broken_supersede_chain` | 0 |
| `stale_normative_reference_rate` | <2% |
| `content_hash_mismatch_rate` | 0 |
| `contract_test_pass_rate` | 100% |
| `docs_without_required_front_matter` | 0 |

## 19.3 记忆持续性

| 指标 | 目标 |
|---|---:|
| `resume_without_transcript_success_rate` | ≥95% |
| `context_rebuild_success_rate` | ≥99% |
| `claims_with_source_reference_rate` | ≥90% |
| `critical_claim_source_rate` | 100% |
| `memory_writeback_latency` | 关键决策当轮或归档前 |
| `handoff_required_reads_resolution_rate` | 100% |

## 19.4 成本

```text
index_tokens/session
retrieved_document_tokens/session
full_document_tokens/session
token_$/verified_step
document_memory_tokens / total_input_tokens
unused_retrieved_context_ratio
```

其中 `unused_retrieved_context_ratio` 目标 `<20%`。若持续偏高，应缩小 section 或优化索引，而不是直接扩大 Context 窗口。

---

# 二十、验收测试

## Test M-01：只读索引

```text
给定一个需要 CONTRACT-STATE 的任务；
系统先返回 INDEX 中的摘要，不打开全文。
```

通过：首次披露只有元数据和 summary。

## Test M-02：Section 精确读取

```text
请求 CONTRACT-STATE#legal-transitions。
```

通过：只读取指定 section；不携带其它章节；hash 和 heading 匹配。

## Test M-03：Review 默认隔离

```text
普通执行任务命中 tags=context 的多个结果，其中包括 Review。
```

通过：Review 不进入候选工作集；audit 记录 deny 规则。

## Test M-04：过期文档

```text
修改 context_engine.py，但不更新 ARCH-CONTEXT 的 verified commit。
```

通过：文档被标 `possibly_stale`；关键动作不得只依赖该文档。

## Test M-05：冲突规范

```text
建立两个 active、normative、同 ID 的 Contract。
```

通过：索引构建失败；不得选择“较新的一个”继续。

## Test M-06：冷启动恢复

```text
清除会话；仅提供 task-id。
```

通过：从 state、handoff 和 Required Reads 重建，未加载 transcript。

## Test M-07：摘要冲突

```text
LLM summary 声称 S2 已完成，state 显示 RUNNING。
```

通过：以 state 为准；summary 被标记不可信。

## Test M-08：ADR 升级

```text
一个 verified 任务产生跨任务架构决策。
```

通过：生成 Writeback Proposal；未验证任务不能直接建立 active ADR。

## Test M-09：写回事务失败

```text
正文修改成功，但索引验证故意失败。
```

通过：不提交 active 文档；保留 proposal/patch Artifact；任务停在 ARCHIVING/BLOCKED。

## Test M-10：多会话写冲突

```text
OpenCode retrieve 和 execute 会话同时尝试更新规范。
```

通过：retrieve 只能提交 proposal；唯一 writer 完成写回。

---

# 二十一、最低自动测试签名

```python
def test_duplicate_active_ids_fail_closed(): ...
def test_review_is_denied_by_default(): ...
def test_section_read_does_not_load_full_doc(): ...
def test_stale_normative_doc_is_flagged(): ...
def test_summary_cannot_override_state(): ...
def test_superseded_doc_is_excluded(): ...
def test_knowledge_patch_requires_sources(): ...
def test_writeback_requires_verified_task(): ...
def test_writeback_is_atomic_with_index(): ...
def test_resume_without_transcript(): ...
def test_content_hash_mismatch_blocks_use(): ...
def test_only_one_state_writer_across_sessions(): ...
```

---

# 二十二、迁移步骤

本章落地顺序冻结为：

```text
1. 建 docs/ 分类目录；
2. 把 Grok/Opus/DeepSeek/GPT 审核原文迁入 reviews/；
3. 为当前有效规范识别 Architecture/Contract/ADR/Runbook；
4. 给核心文档增加 front matter 和稳定 section ID；
5. 建 docs/INDEX.yaml；
6. 建冲突、hash、freshness 检查器；
7. 把旧 token/executor 中长期决策迁到 decisions/ADR；
8. 建 Knowledge Patch 格式；
9. 接入 Memory Writeback Proposal；
10. 跑冷启动恢复和 Review 隔离测试。
```

迁移期间兼容策略：

```text
- 无 front matter 的旧文档视为 authority=informative、status=unknown；
- 旧 Review 一律 advisory；
- 不自动将旧模型建议提升为 ADR；
- 旧 executor.md 仅作为审计材料，提取后不得默认入模；
- 旧 token.json 映射 state.json 后保留只读备份直至迁移验收。
```

---

# 二十三、本部分最终裁决

```text
1. 文档系统是 CarrorOS 的长期 Memory Plane，不是 Prompt 附件目录；
2. Project Memory、Task Memory、Evidence 和 Audit 必须分离；
3. 所有受治理文档必须有稳定 ID、section、authority、status 和 revision；
4. 默认披露顺序从 INDEX 开始，不得直接读全文；
5. ADR 记录长期决策，Contract 记录可验证约束，Runbook 记录操作流程；
6. Review 永远是 advisory，默认禁止进入执行 Context；
7. 隔离 Agent 只能通过带来源的 Knowledge Patch 回传知识；
8. Memory Writeback 必须来源于 VERIFIED 任务并采用原子事务；
9. stale、冲突、hash 不一致必须显式处理，禁止模型静默猜测；
10. 成功标准是删掉 transcript 后仍能从文档与任务文件重建工作状态。
```

---

# 下一部分：第 4/8 部分

将完整输出 **Context Engine 与渐进式披露协议**：

```text
- L0～L5 Progressive Disclosure
- working-set.yaml 最终 Schema
- Hot Card 与 Context Capsule 模板
- 确定性 Context Compiler 算法
- Stable Core / Relevant Memory / File Slices / Evidence Preview
- context_request 与 DisclosureGate
- 分区 token budget 与裁剪优先级
- DeepSeek V4 Flash / Opus profile
- Disclosure Receipt
- 每轮重建而非 transcript 追加
- 缓存稳定性规则
- Context Engine 验收测试
```

