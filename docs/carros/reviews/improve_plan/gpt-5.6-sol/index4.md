# CarrorOS 最终整合重构方案
## 第 4/8 部分：Context Engine、渐进式披露与确定性 Context Compiler

本部分承接：

- 第 1/8：四平面架构与系统不变量；
- 第 2/8：任务状态机、PreActionGate 与 VerifyGate；
- 第 3/8：Document-First Memory Plane。

本章冻结 CarrorOS 的 Context Engine：

> **Context Engine 不是聊天历史压缩器，而是把持久记忆、当前状态、代码片段和执行证据编译成本轮最小工作集的确定性运行时。**

它只维护状态连续性和上下文预算，不制造完成事实。

---

# 一、Context Engine 的最终职责

## 1.1 Context Engine 负责什么

```text
1. 从 state / plan / working-set / docs / evidence 重建本轮 Context；
2. 根据模型 profile 分配分区 token 预算；
3. 实施 L0～L5 渐进式披露；
4. 按 section / symbol / line range 精确检索；
5. 生成 Hot Card；
6. 编译 Context Capsule；
7. 生成 Disclosure Receipt；
8. 对额外信息请求执行 DisclosureGate；
9. 监控 Context 水位；
10. 触发 COMPACT_SOON / COMPACT_NOW / RESUME_REQUIRED；
11. 模型切换时按新 profile 重新编译；
12. 检测 state、plan、Capsule 和来源 revision 是否一致。
```

## 1.2 Context Engine 不负责什么

```text
✗ 判断 step 是否完成；
✗ 修改 plan 的 VERIFIED 标记；
✗ 判断 evidence 是否满足 VerifyGate；
✗ 接受 Oracle verdict；
✗ 决定任务是否可 Archive；
✗ 用摘要覆盖 state、ADR、Contract 或 Artifact；
✗ 从旧聊天中猜测任务状态；
✗ 输出 DONE、VERIFIED 或 ACCEPTED。
```

允许输出：

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

最终边界：

> **Context Engine 只维护状态连续性；VerifyGate 才制造完成事实。**

---

# 二、核心模型：每轮重建，而不是持续追加

旧模式：

```text
System
+ 第 1 轮全部内容
+ 第 2 轮全部内容
+ 第 3 轮全部工具输出
+ 完整 plan
+ 完整 executor
+ 长篇 Review
+ 新一轮输入
```

这种方式使第 N 轮承担前 N−1 轮的全部成本。

最终模式：

```text
Persistent Memory
  ├── docs/**
  ├── state.json
  ├── plan.md
  ├── evidence.jsonl
  ├── artifacts/**
  └── handoff.md
          │
          ▼
Deterministic Context Compiler
          │
          ▼
Context Capsule for Turn N
  ├── Stable Core
  ├── Hot Card
  ├── Current Step
  ├── Relevant Memory
  ├── File Slices
  ├── Evidence Previews
  └── User Delta
```

第 N+1 轮重新编译：

```text
Context(N+1) ≠ Context(N) + 所有新历史
Context(N+1) = compile(current durable state, current working set)
```

Context Capsule 是：

- 可丢弃的；
- 可重建的；
- 有版本的；
- 有来源回执的；
- 不是任务真相源。

---

# 三、L0～L5 渐进式披露协议

渐进式披露必须由协议和 Gate 强制实施，不能依赖模型自律。

## 3.1 披露等级

| 等级 | 名称 | 披露内容 | 默认行为 |
|---:|---|---|---|
| L0 | Index | ID、标题、摘要、标签、权威、新鲜度、token 估算 | 默认起点 |
| L1 | Summary | 文档摘要、模块摘要、符号签名 | 可自动选择 |
| L2 | Slice | 精确 heading、symbol、line range | 常规执行级 |
| L3 | Neighborhood | 直接依赖、调用方、相关 Contract/ADR、相邻测试 | 需理由 |
| L4 | Full | 完整文件或完整文档 | 条件允许 |
| L5 | Isolated Global Review | 全局架构、跨模块研究、全文审查 | 隔离 Agent/会话 |

注意：

> 这里的 L0～L5 是“信息披露等级”，不是 Claude Code 的 L1～L5 压缩流水线，也不是 CarrorOS 的 L1 Base / L2 Enhance。

为避免实现中混淆，配置字段使用：

```text
disclosure_level: D0 | D1 | D2 | D3 | D4 | D5
```

## 3.2 D0：索引披露

只给：

```yaml
id: CONTRACT-AUTH
title: Authentication Contract
summary: 认证公共错误类型和刷新行为约束
authority: normative
status: active
freshness: fresh
estimated_tokens:
  summary: 140
  full: 3100
sections:
  - error-semantics
  - refresh-contract
```

不得给正文。

用途：

- 确定应读取哪个知识源；
- 排除 Review、superseded 或 stale 文档；
- 在低成本下建立候选列表。

## 3.3 D1：摘要披露

只给人工维护或确定性提取的摘要：

```text
CONTRACT-AUTH：
刷新失败必须保持 RefreshError 公共类型；内部实现不得改变调用方可观察错误语义。
```

规则：

```text
- 优先使用文档 front matter 的 summary；
- 不因摘要短就视为完整规范；
- 摘要只能帮助判断是否升级到 D2；
- LLM 生成摘要必须标记 lossy=true；
- 有损摘要不得成为关键动作唯一依据。
```

## 3.4 D2：精确片段披露

按稳定地址读取：

```text
CONTRACT-AUTH#error-semantics@v4
src/auth/refresh.ts#refreshToken@abc1234
tests/auth/refresh.test.ts:40-130@abc1234
```

这是 L1 Base 的常规工作等级。

优先级：

```text
文档：section > heading 范围 >全文
代码：symbol > AST 节点 > line range >全文
证据：event + diagnostics > Artifact 全文
```

## 3.5 D3：邻域披露

只扩展与当前 step 直接相连的邻域：

```text
- 直接调用方；
- 直接被调用符号；
- 对应测试；
- 相关 Contract；
- 相关 active ADR；
- 最近一条失败证据；
- 当前修改的直接依赖。
```

必须有理由，例如：

```text
“修改 refreshToken 的返回路径可能影响调用方错误处理，需要读取两个直接调用方。”
```

不得以“为了全面理解”为理由加载整个模块。

## 3.6 D4：全文披露

仅在以下情况允许：

```text
- 修改对象本身就是该完整短文档；
- 文件小于 profile 的 full_file_tokens 限制；
- 局部切片无法证明一致性；
- 需要检查文件级不变量或完整配置；
- 用户明确要求全文审查；
- Gate 已批准且预算足够。
```

禁止：

```text
- 全文 reviews；
- 完整 transcript；
- 完整 executor；
- 整个仓库树；
- 多个长文档同时全文加载；
- 因模型“不确定”无范围扩张。
```

## 3.7 D5：隔离式全局审查

适用于：

```text
- 跨模块架构审查；
- 大规模重构研究；
- 多份完整规范冲突；
- 仓库级依赖分析；
- Oracle / Multi-Judge；
- 需要大量历史 Review 的整合。
```

D5 不能在主执行轨完成，必须：

```text
1. 创建 fresh-context 子 Agent 或独立会话；
2. 提供明确问题、scope 与输出 Schema；
3. 在隔离 Context 中完成全局读取；
4. 返回 Knowledge Patch / Review Verdict；
5. 主执行轨只接收结构化结论和来源；
6. 禁止把探索 transcript 整段返回。
```

---

# 四、披露升级状态机

```text
D0 INDEX
  ↓ 找到候选
D1 SUMMARY
  ↓ 摘要不足以执行
D2 SLICE
  ↓ 存在直接依赖或冲突
D3 NEIGHBORHOOD
  ↓ 局部信息无法证明一致性
D4 FULL
  ↓ 需要跨模块全局研究
D5 ISOLATED REVIEW
```

升级要求：

```text
D0 → D1：需要判断文档是否与当前 step 相关
D1 → D2：需要具体约束、代码或验证细节
D2 → D3：发现直接依赖、冲突或调用关系
D3 → D4：局部读取无法满足完整性要求
D4 → D5：问题已超出单一执行轨安全预算
```

降级要求：

```text
- 当前 action 完成后，下一轮回到 working-set 默认等级；
- 不因上一轮读过全文，后续每轮都继续携带全文；
- 已提取稳定约束后，只保留来源引用和必要 claim；
- 高阶模型切换到 Flash 时必须重新裁剪；
- 进入新 step 时重算工作集，不继承无关邻域。
```

---

# 五、`working-set.yaml` 最终 Schema

`working-set.yaml` 是当前 step 允许进入 Context 的白名单，不是已加载内容的副本。

```yaml
schema_version: carros.working_set.v1

task_id: fix-auth-001
state_version: 7
plan_version: 2
step_id: S2
profile: deepseek-v4-flash

policy:
  default_disclosure_level: D0
  max_disclosure_level: D3
  require_reason_above: D2
  deny_unlisted_sources: true
  full_document_requires_gate: true
  full_file_requires_gate: true

documents:
  - ref: ADR-014#single-flight
    disclosure_level: D2
    reason: current_step_contract
    authority_required:
      - approved
      - normative
    freshness_required: fresh
    max_tokens: 300
    priority: critical

  - ref: CONTRACT-AUTH#error-semantics
    disclosure_level: D2
    reason: public_behavior_constraint
    authority_required:
      - normative
    freshness_required: fresh
    max_tokens: 300
    priority: critical

files:
  - path: src/auth/refresh.ts
    selector:
      type: symbol
      value: refreshToken
    disclosure_level: D2
    reason: current_edit_target
    mode: read_write
    max_tokens: 3200
    priority: critical

  - path: tests/auth/refresh.test.ts
    selector:
      type: lines
      start: 40
      end: 130
    disclosure_level: D2
    reason: current_verification_target
    mode: read_only
    max_tokens: 1800
    priority: high

evidence:
  filters:
    step: S2
    types:
      - command_result
      - file_change
  latest_per_type: 1
  include_failed: true
  include_artifact_body: false
  max_previews: 2
  max_tokens: 1000

history:
  user_turns: 1
  assistant_turns: 0
  tool_previews: 2
  include_transcript: false
  max_tokens: 800

denied:
  - docs/reviews/**
  - .env
  - secrets/**
  - .omc/tasks/**/artifacts/*.log
  - transcript://**

budget:
  target_tokens: 8000
  soft_tokens: 10000
  hard_tokens: 12000
```

## 5.1 Working Set 不变量

```text
WS-01  task_id、step_id、state_version、plan_version 必须匹配当前状态。
WS-02  未列出的动态来源默认拒绝。
WS-03  denied 优先于 documents/files 白名单。
WS-04  完整 Artifact body 默认禁止。
WS-05  reviews 默认禁止。
WS-06  max_tokens 是硬约束，不是建议。
WS-07  工作集发生变化必须生成新 version 和 Receipt。
WS-08  当前 step 改变后必须重建 working-set。
WS-09  模型 profile 改变后必须重新校验预算。
WS-10  working-set 不能修改任务完成状态。
```

---

# 六、Hot Card

## 6.1 定位

Hot Card 是当前任务状态的极简、确定性投影：

```text
Hot Card ⊂ Context Capsule
```

用途：

```text
- `status --hot`；
- Context Capsule 的状态段；
- 状态栏；
- 恢复前快速检查。
```

它不是：

```text
- 完整 plan；
- 完整 handoff；
- 完整 evidence；
- LLM 总结；
- 任务真相源。
```

## 6.2 模板

```text
[CARROROS HOT CARD]
task: fix-auth-001
level: L1
status: RUNNING
state_version: 7
plan_version: 2
step: S2
action: A1

goal:
修复同一用户并发刷新导致多次上游调用的问题。

scope:
allow: src/auth/refresh.ts, tests/auth/refresh.test.ts
deny: .env, secrets/**, docs/reviews/**

step:
intent: 保证同一用户并发刷新复用一个 promise
verify: pnpm test tests/auth/refresh.test.ts

budget:
profile: deepseek-v4-flash
turns: 8
watermark: 63%
decision: CONTINUE

evidence:
E17 failed: expected one upstream call, received three
artifact: artifacts/test-E17.log

next:
EDIT src/auth/refresh.ts#refreshToken

constraints:
one action per tick
VerifyGate only
```

## 6.3 体积要求

```text
硬上限：4500 chars
推荐：1500～3000 chars
字段顺序：固定
渲染方式：纯程序、无 LLM
同状态渲染 hash：必须一致
```

裁剪顺序：

```text
1. 删除非关键 evidence；
2. 缩短 goal；
3. 省略已 VERIFIED step；
4. 保留 task/status/version/current step/scope/verify/next。
```

---

# 七、Context Capsule

## 7.1 最终组成

```text
Context Capsule =
    Stable Core
  + Hot Card
  + Current Step
  + Relevant Memory
  + File Slices
  + Evidence Previews
  + User Delta
```

不再默认包含独立的历史对话区。必要的用户约束应已经写入 `manifest/state/decisions`；最近用户消息作为 `User Delta` 进入。

## 7.2 完整模板

```markdown
---
schema_version: carros.context_capsule.v1
capsule_id: CC-fix-auth-001-0012
task_id: fix-auth-001
capsule_version: 12
state_version: 7
plan_version: 2
step_id: S2
profile: deepseek-v4-flash
compiled_at: 2026-07-12T09:30:00Z
estimated_tokens: 7240
receipt_id: DR-0012
---

# Stable Runtime Contract

- 文档是长期记忆，Context 是可丢弃工作集。
- 每 tick 只执行一个 action。
- denied_paths 优先。
- 完整工具输出必须落盘。
- 只有 VerifyGate 可以标记 VERIFIED。

# Hot State

task: fix-auth-001
status: RUNNING
step: S2
action: A1
state_version: 7
scope: src/auth/refresh.ts
next: EDIT refreshToken

# Current Step

intent:
保证同一用户并发刷新复用一个 in-flight promise。

allowed_paths:
- src/auth/refresh.ts

verification:
- pnpm test tests/auth/refresh.test.ts
- public signature unchanged

rollback:
- git restore src/auth/refresh.ts

# Relevant Memory

## ADR-014#single-flight@abc1234

同一用户并发 refresh 必须复用一个 in-flight promise。

## CONTRACT-AUTH#error-semantics@v4

内部实现不得改变调用方可观察的 RefreshError 类型。

# File Slices

## src/auth/refresh.ts#refreshToken@abc1234

```ts
// 精确符号片段
```

## tests/auth/refresh.test.ts:40-130@abc1234

```ts
// 精确测试片段
```

# Evidence Preview

[artifact]
id: E17
type: command_result
exit_code: 1
path: artifacts/test-E17.log
sha256: ...
preview:
expected one upstream call, received three

# User Delta

继续修复，但不要改变公共错误类型。

# Action Contract

Return exactly one of:
- ACTION_PROPOSAL
- CONTEXT_REQUEST
- ASK_USER
- BLOCKED

Do not mark the step VERIFIED.
```

## 7.3 Capsule 不变量

```text
CAP-01  Capsule 必须绑定 state_version 和 plan_version。
CAP-02  Capsule 必须有唯一 receipt_id。
CAP-03  Stable Core 必须置于最前并尽量保持字节稳定。
CAP-04  动态段按固定顺序排列。
CAP-05  每个外部来源必须携带 ref/revision/hash。
CAP-06  Capsule 不能包含 chain-of-thought。
CAP-07  Capsule 不能包含完整 transcript。
CAP-08  Artifact 只能包含预览和指针。
CAP-09  Capsule 超预算必须裁剪或拒绝，不能静默越界。
CAP-10  Capsule 不能成为下一轮的唯一输入源；下一轮必须重新编译。
```

---

# 八、Stable Core

## 8.1 内容边界

Stable Core 只保留高频且全局有效的不变量：

```text
- 真相源位置；
- 当前 CLI/工具契约；
- denied 优先；
- 一个 tick 一个 action；
- Artifact 落盘；
- VerifyGate 唯一完成；
- Context Request 格式；
- 禁止 transcript 恢复。
```

不能放入：

```text
- 当前任务状态；
- 完整架构说明；
- 外部 Review；
- 当前 plan；
- 模型长篇建议；
- 动态 token 水位；
- 最近工具结果；
- 全量 MCP Schema。
```

## 8.2 推荐上限

```text
Flash：≤1200 tokens
高阶模型：≤1800 tokens
目标字符数：≤6000 chars
修改频率：极低
```

## 8.3 缓存稳定性

为了保护 Claude Code Prompt Cache：

```text
1. Stable Core 内容和顺序冻结；
2. 不写入时间戳；
3. 不写入随机 ID；
4. 不动态改写措辞；
5. 高变任务内容放在 Stable Core 之后；
6. 同一工具预览必须按 artifact hash 原样复用；
7. 同一文档 section 使用确定性格式；
8. provider/tool Schema 仅在需要时披露。
```

指标：

```text
stable_prefix_hash_changes/session ≈ 0
prompt_cache_hit_rate ≥70%，目标≥85%
same_source_render_hash_match_rate = 100%
artifact_preview_reuse_rate ≥95%
```

---

# 九、确定性 Context Compiler

## 9.1 编译输入

```text
task_id
state.json
manifest.yaml
plan.md 当前 step
working-set.yaml
docs/INDEX.yaml
evidence.jsonl
model profile
user delta
repository revision
```

## 9.2 编译输出

```text
capsule.current.md
receipts.jsonl 新记录
context metrics event
ContextDecision
```

## 9.3 编译算法

```python
def compile_context(
    task_id: str,
    user_delta: str,
    profile_name: str | None = None,
) -> dict:
    manifest = load_manifest(task_id)
    state = load_state(task_id)
    plan = load_plan(task_id)

    assert_state_allows_context(state)
    current_step = resolve_current_step(state, plan)

    working_set = load_working_set(task_id)
    validate_working_set(
        working_set=working_set,
        task_id=task_id,
        state_version=state["state_version"],
        plan_version=state["plan_version"],
        step_id=current_step["id"],
    )

    profile = load_profile(
        profile_name or state["context"]["profile"]
    )

    stable_core = render_stable_core(profile)
    hot_card = render_hot_card(
        manifest=manifest,
        state=state,
        current_step=current_step,
        evidence=load_evidence_index(task_id),
    )

    memory = retrieve_document_sections(
        requests=working_set["documents"],
        profile=profile,
        deny=working_set["denied"],
    )

    files = retrieve_file_slices(
        requests=working_set["files"],
        repository_revision=current_repository_revision(),
        profile=profile,
        deny=working_set["denied"],
    )

    evidence = retrieve_evidence_previews(
        task_id=task_id,
        policy=working_set["evidence"],
        profile=profile,
    )

    sections = [
        section("stable_core", stable_core, priority="mandatory"),
        section("hot_card", hot_card, priority="mandatory"),
        section("current_step", render_step(current_step), priority="mandatory"),
        section("relevant_memory", render_memory(memory), priority="high"),
        section("file_slices", render_files(files), priority="high"),
        section("evidence", render_evidence(evidence), priority="medium"),
        section("user_delta", normalize_user_delta(user_delta), priority="mandatory"),
    ]

    bundle = enforce_partition_budgets(sections, profile)
    bundle = enforce_total_budget(bundle, profile)

    if not bundle.mandatory_sections_fit:
        decision = "DOWNGRADE_REQUIRED"
        write_context_failure(task_id, bundle)
        return {
            "decision": decision,
            "reason": "mandatory_context_exceeds_hard_budget"
        }

    receipt = build_disclosure_receipt(
        task_id=task_id,
        state=state,
        profile=profile,
        sources=bundle.sources,
        denied=bundle.denied,
        token_usage=bundle.token_usage,
    )

    capsule = render_capsule(
        task_id=task_id,
        state=state,
        current_step=current_step,
        sections=bundle.sections,
        receipt_id=receipt["receipt_id"],
        profile=profile,
    )

    write_capsule_atomically(task_id, capsule)
    append_receipt(task_id, receipt)
    append_context_metrics(task_id, capsule, receipt)

    return {
        "decision": classify_watermark(
            estimated_tokens=capsule.estimated_tokens,
            profile=profile,
            turns=state["context"]["turns"],
        ),
        "capsule": capsule,
        "receipt": receipt,
    }
```

## 9.4 Compiler 禁止调用 LLM 的阶段

以下必须是确定性的：

```text
- state 读取；
- current step 解析；
- token 估算；
- budget 裁剪；
-文档 authority/status/freshness 过滤；
- section 和 symbol 提取；
- Artifact 预览；
- Hot Card 渲染；
- Receipt 生成；
- Capsule 排序和序列化。
```

允许 LLM 的位置：

```text
- L2 隔离检索 Agent 提议候选来源；
- 大型语义检索产生候选文档 ID；
- 有损导航摘要；
- Oracle/Review。
```

即使使用 LLM，最终来源仍必须通过确定性 Gate 校验。

---

# 十、分区 Token Budget

仅设置一个总预算不足以防止某一类内容吞掉全部 Context，因此必须分区。

## 10.1 DeepSeek V4 Flash profile

```yaml
# .omc/profiles/deepseek-v4-flash.yaml
schema_version: carros.context_profile.v1

id: deepseek-v4-flash
model_class: flash

budget:
  stable_core: 1200
  hot_card: 700
  current_step: 900
  document_memory: 1300
  file_slices: 3500
  evidence: 700
  user_delta: 800
  reserve: 900

limits:
  target_input_tokens: 8000
  soft_input_tokens: 10000
  hard_input_tokens: 12000

  max_files_per_action: 2
  max_document_sections: 3
  max_tool_previews: 1
  max_full_files: 0
  max_full_documents: 0

  max_read_lines_per_slice: 200
  max_actions_per_tick: 1

disclosure:
  default_level: D0
  normal_max_level: D2
  gated_max_level: D3
  allow_d4_full: false
  allow_d5_global_review: false

watermark:
  soft_turns: 15
  hard_turns: 20
  soft_percent: 80
  hard_percent: 95

behavior:
  require_context_request: true
  require_disclosure_receipt: true
  architecture_synthesis: false
  prefer_symbol_slice: true
```

适用原则：

```text
- 单动作、低歧义、窄 scope；
- 不承担全局架构综合；
- 不读取完整长文；
- 文件优先按 symbol；
- 超出 D3 转高阶隔离会话；
- 不通过增加上下文弥补能力不足。
```

## 10.2 Opus 4.8 类高阶 profile

```yaml
# .omc/profiles/opus-4.8.yaml
schema_version: carros.context_profile.v1

id: opus-4.8
model_class: reasoning

budget:
  stable_core: 1800
  hot_card: 900
  current_step: 1200
  document_memory: 3000
  file_slices: 7000
  evidence: 1600
  user_delta: 1200
  reserve: 2500

limits:
  target_input_tokens: 18000
  soft_input_tokens: 24000
  hard_input_tokens: 32000

  max_files_per_action: 4
  max_document_sections: 6
  max_tool_previews: 2
  max_full_files: 1
  max_full_documents: 1

  max_read_lines_per_slice: 400
  max_actions_per_tick: 1

disclosure:
  default_level: D0
  normal_max_level: D3
  gated_max_level: D4
  allow_d4_full: conditional
  allow_d5_global_review: isolated_session_only

watermark:
  soft_percent: 70
  hard_percent: 85
  soft_turns: 15
  hard_turns: 20

behavior:
  require_context_request: true
  require_disclosure_receipt: true
  architecture_synthesis: isolated_session_only
  prefer_symbol_slice: true
```

高阶模型不应因容量较大而默认加载更多历史：

> **更强的模型用于处理更高密度的问题，不用于吞更多低密度上下文。**

## 10.3 通用目标

```text
Flash 执行轨：
  median ≤8K
  P95 ≤16K
  hard ≤24K（异常逃生上限，不是日常预算）

高阶执行轨：
  median ≤16K
  P95 ≤32K
  全局审查转隔离会话

系统级：
  full_document_load_rate <2%
  full_tool_output_in_context_rate =0
  L5/有损摘要恢复依赖 =0
```

---

# 十一、预算裁剪算法

## 11.1 不可裁剪内容

```text
- Stable Core 中的安全与真相不变量；
- task ID、status、state_version；
- current step intent；
- allowed/denied scope；
- 当前 action；
- 必需验证条件；
- 未解决 blocker / ASK_USER；
- 用户本轮有效指令；
- 关键 normative Contract。
```

## 11.2 裁剪优先级

从最先裁剪到最后裁剪：

```text
P1  重复说明和格式性文本
P2  已 VERIFIED step 的历史信息
P3  低权威 informative/advisory 背景
P4  旧的成功工具预览
P5  非当前 action 的相邻文件
P6  非关键 ADR 背景
P7  多余 evidence 预览
P8  当前文件的非目标邻域
P9  高优先级相关记忆
P10 强制 Contract / scope / current step（不可裁）
```

## 11.3 超预算裁决

```text
estimated ≤ target:
  CONTINUE

target < estimated ≤ soft:
  CONTINUE + metric warning

soft < estimated ≤ hard:
  COMPACT_SOON
  缩减低优先级段
  当前 action 后写 handoff

estimated > hard 且裁剪后可容纳：
  COMPACT_NOW
  重建最小 Capsule

mandatory sections > hard:
  DOWNGRADE_REQUIRED 或 RESUME_BLOCKED
  不生成不完整的危险 Capsule
```

“DOWNGRADE_REQUIRED”可表示：

```text
- 将任务拆为更小 step；
- 缩小 scope；
- 切换更合适模型；
- 转隔离审查会话；
- 补充结构化文档，使无需加载大量原文。
```

它不一定指切换到更弱模型。

---

# 十二、Context Request 协议

当 Capsule 信息不足时，Agent 必须发出结构化请求，不能直接自由读取。

```json
{
  "schema_version": "carros.context_request.v1",
  "request_id": "CR-011",
  "task_id": "fix-auth-001",
  "state_version": 7,
  "step_id": "S2",
  "reason": "需要确认调用方是否依赖 RefreshError 的具体类型",
  "targets": [
    {
      "kind": "document_section",
      "ref": "CONTRACT-AUTH#error-semantics",
      "requested_level": "D2",
      "max_tokens": 300
    },
    {
      "kind": "code_symbol",
      "path": "src/auth/errors.ts",
      "symbol": "RefreshError",
      "requested_level": "D2",
      "max_tokens": 600
    }
  ],
  "expected_decision_impact": "决定是否允许修改内部错误映射",
  "not_requested": [
    "full repository",
    "full contract",
    "historical reviews"
  ]
}
```

## 12.1 DisclosureGate 裁决

```text
ALLOW
NARROW
BLOCK
NEW_SESSION
ASK_USER
```

### ALLOW

条件：

```text
- 与 current step 直接相关；
- 来源精确；
- authority/freshness 合格；
- 在预算内；
- 未命中 denied；
- requested level 合理。
```

### NARROW

示例：

```text
请求：读取完整认证模块
裁决：只允许 auth/errors.ts#RefreshError 和两个直接调用方
```

### BLOCK

命中：

```text
- reviews 默认拒绝；
- secrets；
- 完整 transcript；
- 与当前 step 无关；
- 请求缺少理由；
- source 不存在或 hash 冲突；
- 当前状态不允许执行。
```

### NEW_SESSION

用于：

```text
- D5 全局审查；
- 超出主轨 hard budget；
- 多个长文档冲突；
- 跨模块架构研究；
- Oracle/Multi-Judge。
```

### ASK_USER

仅当所需信息只能由用户提供，不应通过更多检索猜测时使用。

## 12.2 Gate 输出

```json
{
  "schema_version": "carros.disclosure_verdict.v1",
  "request_id": "CR-011",
  "decision": "ALLOW",
  "state_version": 7,
  "approved_targets": [
    {
      "kind": "document_section",
      "ref": "CONTRACT-AUTH#error-semantics@v4",
      "max_tokens": 300
    },
    {
      "kind": "code_symbol",
      "path": "src/auth/errors.ts",
      "symbol": "RefreshError",
      "revision": "abc1234",
      "max_tokens": 600
    }
  ],
  "denied_targets": [],
  "budget_after_approval": {
    "estimated_total_tokens": 8120,
    "soft_limit": 10000
  },
  "reason": "请求精确且直接影响当前实现边界"
}
```

---

# 十三、Disclosure Receipt

每次编译必须记录“加载了什么、为什么、多少 token、哪个 revision”。

```json
{
  "schema_version": "carros.disclosure_receipt.v1",
  "receipt_id": "DR-0012",
  "capsule_id": "CC-fix-auth-001-0012",
  "task_id": "fix-auth-001",
  "state_version": 7,
  "plan_version": 2,
  "step_id": "S2",
  "profile": "deepseek-v4-flash",
  "compiled_at": "2026-07-12T09:30:00Z",
  "sources": [
    {
      "kind": "document_section",
      "ref": "ADR-014#single-flight@abc1234",
      "reason": "current_step_contract",
      "authority": "approved",
      "freshness": "fresh",
      "estimated_tokens": 112,
      "render_sha256": "..."
    },
    {
      "kind": "code_symbol",
      "ref": "src/auth/refresh.ts#refreshToken@abc1234",
      "reason": "current_edit_target",
      "estimated_tokens": 1740,
      "render_sha256": "..."
    },
    {
      "kind": "evidence_preview",
      "ref": "E17",
      "artifact_sha256": "...",
      "estimated_tokens": 94,
      "render_sha256": "..."
    }
  ],
  "denied": [
    {
      "ref": "docs/reviews/opus/context-cost-improve.md",
      "rule": "REVIEW_DENY_DEFAULT"
    }
  ],
  "token_usage": {
    "stable_core": 1040,
    "hot_card": 410,
    "current_step": 510,
    "document_memory": 270,
    "file_slices": 3050,
    "evidence": 210,
    "user_delta": 180,
    "total_estimated": 5670
  },
  "decision": "CONTINUE"
}
```

Receipt 属于治理审计，不默认进入模型。

## 13.1 Receipt 用途

```text
- 计算 Context 成本；
- 发现全文滥用；
- 调试为什么模型获得某项知识；
- 重放相同 Capsule；
- 检测来源漂移；
- 评估 unused context；
- 验证缓存稳定性；
- 证明 reviews 未被默认注入。
```

---

# 十四、文件切片策略

## 14.1 选择优先级

```text
1. AST / LSP symbol
2. 函数、类、接口精确范围
3. heading / config key
4. 行范围
5. 文件全文
```

## 14.2 每个切片必须携带

```text
path
selector
repository revision
content hash
estimated tokens
reason
read/write mode
```

渲染示例：

```text
[file_slice]
path: src/auth/refresh.ts
selector: symbol:refreshToken
revision: abc1234
sha256: ...
reason: current_edit_target
content:
...
```

## 14.3 邻域扩张

模型需要更多文件时：

```text
- 先请求直接调用方/被调用方；
- 每次最多增加 profile 允许的文件数；
- 不允许递归遍历整个依赖图；
- 超过两层依赖默认转 D5；
- 新文件必须更新 working-set 和 Receipt。
```

---

# 十五、工具结果和 Evidence Preview

## 15.1 完整结果处理

```text
stdout/stderr
   ↓
Artifact Store
   ↓
evidence.jsonl
   ↓
确定性 Preview
   ↓
Context Capsule
```

性质：

| 处理 | 性质 |
|---|---|
| Artifact 完整落盘 | **无损可回滚、可审计** |
| evidence 指针 | 结构化索引 |
| 有界确定性预览 | 原件存在，因此可恢复 |
| LLM 工具摘要 | **有损**，只可导航 |
| 用摘要替换 Artifact | 禁止 |

## 15.2 确定性 Preview

不能只取前 2000 字符，因为错误常在末尾。

```python
def deterministic_preview(text: str, limit: int = 2000) -> str:
    head = text[:600]
    diagnostics = select_matching_lines(
        text,
        patterns=[
            "error",
            "failed",
            "failure",
            "exception",
            "traceback",
            "panic",
        ],
        max_lines=5,
    )
    tail = text[-800:] if len(text) > 800 else ""

    return stable_preview_format(
        head=head,
        diagnostics=diagnostics,
        tail=tail,
        limit=limit,
    )
```

固定模板：

```text
[artifact]
id: {event_id}
type: {type}
exit_code: {exit_code}
path: {artifact_path}
sha256: {sha256}
bytes: {bytes}
preview:
[head]
{head}
[diagnostics]
{diagnostics}
[tail]
{tail}
```

同一 Artifact 的 preview 必须按 hash 复用，不能每轮重新措辞。

---

# 十六、每轮运行协议

## 16.1 标准回合

```text
1. 读取 state.json；
2. 校验 current step；
3. 校验 working-set 版本；
4. 编译 Context Capsule；
5. 记录 Disclosure Receipt；
6. 将 Capsule 提交模型；
7. 模型返回一个 ACTION_PROPOSAL 或 CONTEXT_REQUEST；
8. PreActionGate 裁决；
9. 执行一个 action；
10. 完整结果落 Artifact；
11. 写 evidence；
12. 更新 state/context metrics；
13. 下一轮重新编译。
```

## 16.2 禁止回合

```text
✗ 把上一轮完整回答继续拼入下一轮；
✗ 自动附上完整 executor；
✗ 每五轮把所有状态重新注入；
✗ 因“帮助模型记忆”加载完整 handoff；
✗ 把 Review 放进 Stable Core；
✗ 把工具日志原文复制回 Prompt；
✗ Context 达到水位后继续启动新 step。
```

## 16.3 用户消息持久化

用户消息只有三类处理：

```text
A. 瞬时指令
   作为 User Delta，只影响本轮。

B. 任务级事实/约束
   写入 manifest/state/decisions，再进入后续 Capsule。

C. 项目级长期决策
   经验证后走 Memory Writeback，进入 ADR/Contract。
```

这避免“为了记住用户说过什么”永久携带整个聊天。

---

# 十七、水位与长会话策略

## 17.1 双水位

建议同时监控：

```text
token watermark
turn watermark
```

### L1 Base 默认值

```text
soft turns: 15
hard turns: 20

soft tokens: profile 的 80%
hard tokens: profile 的 95%
```

### L2 Enhance 默认值

```text
soft tokens: 70%
hard tokens: 85%

turn 仅作辅助，不依赖固定回合数；
复杂研究轨更应提前隔离。
```

## 17.2 状态决策

```text
低于 soft：
  CONTINUE

达到 soft：
  COMPACT_SOON
  当前 action 后刷新 handoff
  禁止扩大 scope

达到 hard：
  COMPACT_NOW
  不启动新 action
  最小 Capsule 重编译

必要信息仍超过 hard：
  RESUME_REQUIRED / DOWNGRADE_REQUIRED
  转新会话、拆 step 或切换模型
```

## 17.3 无损与有损边界

```text
状态/工具/证据落盘：
  无损可回滚

重新编译 Capsule：
  不删除 Memory Plane，属于无损工作集重建

裁剪已落盘的旧 preview：
  原件仍在，逻辑可恢复

LLM 摘要：
  有损

Claude L5 AutoCompact：
  有损不可逆，不能作为正常记忆机制

OpenCode Prune(hidden)：
  非物理删除，可审计回溯
```

压缩与恢复的双栈完整策略放在第 5/8。

---

# 十八、模型切换协议

从高阶模型切到 Flash，或反向切换时，不得直接复用旧 Capsule。

```text
1. 保存当前 state；
2. 完成或停止当前 action；
3. 记录 Artifact/evidence；
4. 选择新 profile；
5. 重新验证 working-set；
6. 按新分区预算重新编译；
7. 生成新 Receipt；
8. 更新 state.context.profile；
9. 才允许继续。
```

## 18.1 Opus → Flash

必须：

```text
- D4 降到 D2/D3；
- 完整文件改为 symbol slices；
- 文档 section 数量减少；
- Review/研究结论转换为 Knowledge Patch；
- 一个 tick 一个更小动作；
- 架构综合留在高阶隔离会话。
```

## 18.2 Flash → Opus

允许增加邻域，但不自动增加：

```text
- transcript；
- 完整工具日志；
- 历史 Review；
- 已完成 step；
- 无关文档。
```

模型能力升级不是取消 Context 治理的理由。

---

# 十九、Claude Code 路径

Claude Code 侧的 Context Engine 重点：

```text
1. Slim CLAUDE.md 作为 Stable Core；
2. 工具结果 L1 落盘，只保留稳定 Preview；
3. 旧工具结果裁剪前确认 Artifact 已写入；
4. ContentReplacementState 范式：同一结果复用相同预览文本；
5. 长研究使用 fresh-context subagent；
6. Checkpoint 用于文件级撤回；
7. transcript 用于审计和极端恢复，不是正常 Memory Plane；
8. L5 AutoCompact 是最后兜底。
```

Claude Code 压缩性质：

```text
L1 工具落盘 + Preview：
  无损可回滚

L2 已外置历史裁剪：
  原件仍在 Artifact，可恢复

L3 微压缩重复解释：
  轻度有损

L4 上下文折叠：
  有损，应保留恢复指针

L5 AutoCompact：
  有损不可逆，不得作为 CarrorOS 记忆机制
```

关键指标：

```text
prompt_cache_hit_rate
cache_read_tokens
stable_prefix_hash_changes
artifact_preview_reuse_rate
compaction_events/session
L5_rate
token_$/verified_step
```

目标：

```text
prompt_cache_hit_rate ≥70%，目标≥85%
L5 dependency =0
tool_full_in_context_rate =0
```

---

# 二十、OpenCode 路径

OpenCode 侧不能照搬 Claude 的 L1～L5 压缩名称。

正确顺序：

```text
1. Context Compiler 限制新内容进入；
2. Artifact 和 SQLite 保留审计原件；
3. transcript 先 Prune(hidden)；
4. 保护最近约 40K token 安全垫；
5. 保留最近两个完整回合；
6. skill 输出不剪；
7. 仍不足时才调用隐藏摘要 Agent；
8. 摘要完成后重放最后一条用户消息；
9. 任务状态仍从 state/handoff 重建。
```

性质：

```text
Prune(hidden)：
  非物理删除，可审计回溯

SQLite 原始会话：
  审计链，不是任务状态源

隐藏 Agent 摘要：
  有损，只能导航

.omc/tasks/**：
  CarrorOS 任务真相
```

多会话约束：

```text
execute 会话：唯一 State Writer
retrieve 会话：只产 Knowledge Patch
review 会话：只产 Verdict
govern 会话：只读指标和审计
```

关键指标：

```text
prune_before_summary_rate =100%
lossy_summary_as_truth_count =0
multi_session_state_write_conflicts =0
SQLite audit retention 达标
token_$/verified_step
```

---

# 二十一、核心配置

## 21.1 Context Engine 配置

```yaml
# .omc/context-engine.yaml
schema_version: carros.context_engine_config.v1

compiler:
  deterministic: true
  rebuild_each_turn: true
  require_receipt: true
  validate_source_hash: true
  validate_state_version: true
  validate_plan_version: true

stable_core:
  path: CLAUDE.md
  max_chars: 6000
  freeze_order: true
  forbid_dynamic_state: true

retrieval:
  default_level: D0
  prefer_section: true
  prefer_symbol: true
  full_document_requires_gate: true
  full_file_requires_gate: true
  max_dependency_depth: 2

history:
  include_transcript: false
  recent_user_turns: 1
  recent_assistant_turns: 0
  max_tool_previews: 2

artifacts:
  store_full_result: true
  preview_chars: 2000
  preview_strategy: head_diagnostics_tail
  reuse_preview_by_hash: true

denied:
  - docs/reviews/**
  - .env
  - secrets/**
  - transcript://**
  - .omc/tasks/**/artifacts/*.log

failure:
  fail_closed_on_index_conflict: true
  fail_closed_on_state_mismatch: true
  fail_closed_on_hash_mismatch: true
```

## 21.2 `.claude/settings.json`

以下是 CarrorOS 环境约定；实际 Hook 结构需按所用 Claude Code 版本适配：

```json
{
  "env": {
    "CARROS_CONTEXT_CONFIG": ".omc/context-engine.yaml",
    "CARROS_CONTEXT_PROFILE": "deepseek-v4-flash",
    "CARROS_REQUIRE_DISCLOSURE_RECEIPT": "1",
    "CARROS_REBUILD_CONTEXT_EACH_TURN": "1",
    "CARROS_FORBID_TRANSCRIPT_MEMORY": "1",
    "CARROS_FORBID_REVIEW_DOCS": "1",
    "CARROS_ARTIFACT_PREVIEW_CHARS": "2000",
    "CARROS_ARTIFACT_PREVIEW_MODE": "head_diagnostics_tail",
    "CARROS_FAIL_CLOSED": "1"
  },
  "permissions": {
    "defaultMode": "default"
  }
}
```

## 21.3 OpenCode CarrorOS 层配置

这不是宣称为 OpenCode 原生 Schema，而是 CarrorOS 插件/包装器配置：

```json
{
  "carros": {
    "contextEngine": {
      "config": ".omc/context-engine.yaml",
      "profile": "deepseek-v4-flash",
      "rebuildEachTurn": true,
      "requireDisclosureReceipt": true
    },
    "compaction": {
      "preferPrune": true,
      "preserveRecentTurns": 2,
      "preserveSkillOutputs": true,
      "summaryIsAuthoritative": false
    },
    "sessions": {
      "singleStateWriter": true,
      "executeSessionCanWrite": true,
      "retrieveSessionCanWrite": false,
      "reviewSessionCanWrite": false
    },
    "audit": {
      "preserveSQLiteSession": true,
      "preserveArtifacts": true,
      "recordDisclosureReceipts": true
    }
  }
}
```

---

# 二十二、CLI 冻结

```bash
# 查看 Hot Card
python3 .claude/scripts/carros_base.py status \
  --task-id fix-auth-001 \
  --hot

# 编译 Capsule
python3 .claude/scripts/carros_base.py context compile \
  --task-id fix-auth-001 \
  --profile deepseek-v4-flash \
  --user-delta-file /tmp/user-delta.txt

# 查看 Receipt
python3 .claude/scripts/carros_base.py context receipt \
  --task-id fix-auth-001 \
  --latest

# 检查预算
python3 .claude/scripts/carros_base.py context budget \
  --task-id fix-auth-001

# 提交额外披露请求
python3 .claude/scripts/carros_base.py context request \
  --task-id fix-auth-001 \
  --request-file .omc/requests/CR-011.json

# 验证 Capsule 是否过期
python3 .claude/scripts/carros_base.py context validate \
  --task-id fix-auth-001

# 强制重建
python3 .claude/scripts/carros_base.py context rebuild \
  --task-id fix-auth-001

# 生成 handoff
python3 .claude/scripts/carros_base.py context handoff \
  --task-id fix-auth-001
```

CLI 只展示和路由，不产生完成事实：

```text
context compile 不得标记 step 完成；
context validate 不等于 VerifyGate；
context handoff 不得写 VERIFIED；
status --hot 不得把模型总结当状态。
```

---

# 二十三、可观测指标

## 23.1 Context 成本

| 指标 | 目标 |
|---|---:|
| `input_tokens_per_turn.median` | 全局 ≤10K |
| `input_tokens_per_turn.p95` | ≤24K |
| `flash_input_tokens.median` | ≤8K |
| `reasoning_input_tokens.median` | ≤16K |
| `token_usd_per_verified_step` | 相比基线下降 ≥70% |
| `capsule_rebuild_latency_ms.p95` | 按仓库规模建基线 |

## 23.2 渐进式披露

| 指标 | 目标 |
|---|---:|
| `full_document_load_rate` | <2% |
| `full_file_load_rate` | <5% |
| `average_document_sections_per_turn` | Flash ≤3，高阶 ≤6 |
| `average_files_per_action` | Flash ≤2，高阶 ≤4 |
| `D5_main_session_count` | 0 |
| `review_default_disclosure_count` | 0 |
| `context_request_narrow_rate` | 持续下降 |
| `denied_source_bypass_count` | 0 |

## 23.3 工作集质量

```text
unused_context_ratio <20%
mandatory_section_drop_count =0
capsule_state_version_mismatch_rate <1%，发现即重编译
capsule_plan_version_mismatch_count =0
source_hash_mismatch_count =0
working_set_unlisted_source_count =0
```

## 23.4 缓存与压缩

```text
Claude:
  prompt_cache_hit_rate ≥70%，目标≥85%
  stable_prefix_hash_changes ≈0
  L5_rate =0 或接近0

OpenCode:
  prune_before_summary_rate =100%
  summary_as_authority_count =0
  non_destructive_audit_retention 达标
```

---

# 二十四、验收测试

## Test C-01：每轮重建

```text
执行 20 个 tick。
```

通过：

```text
第 20 轮 Context 不包含前 19 轮完整 transcript；
输入 token 不随轮次线性增长；
每轮有新的 Receipt；
状态从 state/plan 重建。
```

## Test C-02：工作集白名单

```text
模型请求读取未列出的文件。
```

通过：

```text
返回 CONTEXT_REQUEST/Gate 裁决；
不会直接读取；
批准后 working-set 和 Receipt 同步更新。
```

## Test C-03：Review 隔离

```text
索引候选中包含高相关 Review。
```

通过：

```text
主执行轨拒绝；
D5 独立会话只有显式批准后才能读取；
Review 原文不进入 Capsule。
```

## Test C-04：100K 工具日志

```text
工具产生 100K chars 输出。
```

通过：

```text
全文进入 Artifact；
Capsule 只进入 ≤2K 稳定预览；
下一轮 token 不随日志体积线性增长。
```

## Test C-05：Capsule 版本失效

```text
编译 Capsule 后更新 state_version。
```

通过：

```text
旧 Capsule 被拒绝；
重新编译；
不得使用旧 current step 执行动作。
```

## Test C-06：模型切换

```text
Opus profile 切换到 Flash profile。
```

通过：

```text
不复用旧 Capsule；
D4 来源被裁剪或转切片；
重新生成 Receipt；
任务状态不丢失。
```

## Test C-07：硬预算

```text
必需文件片段和 Contract 超出 hard limit。
```

通过：

```text
返回 DOWNGRADE_REQUIRED/RESUME_BLOCKED；
不静默删除安全约束；
不生成不完整危险 Capsule。
```

## Test C-08：披露升级

```text
模型请求完整模块，实际只需一个符号。
```

通过：

```text
Gate 返回 NARROW；
批准 symbol slice；
Receipt 记录裁决。
```

## Test C-09：缓存稳定

```text
相同 state/source 连续编译两次。
```

通过：

```text
Stable Core hash 相同；
同一 section 渲染 hash 相同；
同一 Artifact preview 完全一致。
```

## Test C-10：Context 与 Verify 隔离

```text
handoff/Capsule 声称 step 已完成，但无 VerifyGate verdict。
```

通过：

```text
Context Engine 不写 VERIFIED；
state 保持 RUNNING；
VerifyGate 重新计算证据。
```

## Test C-11：用户长期约束写回

```text
用户说“以后所有刷新错误必须保留 RefreshError”。
```

通过：

```text
先持久化到 task decision；
经验证和 Writeback 后进入 Contract；
不依赖永久携带该聊天消息。
```

## Test C-12：D5 隔离

```text
需要审查整个认证架构。
```

通过：

```text
主执行轨返回 NEW_SESSION；
隔离 Agent 输出 Knowledge Patch；
主轨不接收完整审查 transcript。
```

---

# 二十五、最低自动测试签名

```python
def test_context_is_rebuilt_each_turn(): ...
def test_context_does_not_include_transcript(): ...
def test_working_set_denies_unlisted_sources(): ...
def test_denied_path_overrides_allow(): ...
def test_review_is_not_disclosed_in_execution(): ...
def test_capsule_binds_state_version(): ...
def test_capsule_binds_plan_version(): ...
def test_same_source_renders_identically(): ...
def test_large_tool_output_is_artifacted(): ...
def test_artifact_preview_is_deterministic(): ...
def test_hard_budget_never_drops_mandatory_contracts(): ...
def test_full_document_requires_gate(): ...
def test_context_request_can_be_narrowed(): ...
def test_profile_switch_recompiles_capsule(): ...
def test_d5_runs_in_isolated_session(): ...
def test_context_engine_cannot_verify_step(): ...
def test_receipt_lists_every_dynamic_source(): ...
def test_source_hash_mismatch_fails_closed(): ...
def test_user_constraint_is_persisted_not_replayed_forever(): ...
def test_context_tokens_do_not_grow_linearly_with_turns(): ...
```

---

# 二十六、迁移顺序

```text
1. 冻结 Slim Stable Core；
2. 建 deepseek-v4-flash / opus-4.8 profile；
3. 建 working-set.yaml；
4. 实现 Hot Card 确定性渲染；
5. 实现 section/symbol/file slice；
6. 实现 Artifact 稳定预览；
7. 实现 Context Capsule；
8. 实现 Disclosure Receipt；
9. 实现 Context Request + DisclosureGate；
10. 接入每轮重新编译；
11. 禁止 transcript 默认注入；
12. 接入水位与 handoff；
13. 运行 20/30 tick 非线性增长测试；
14. 再接 Claude/OpenCode 原生压缩机制。
```

止血阶段可以先落地最小子集：

```text
P0：
  Slim Core
  Hot Card
  工具落盘
  禁 Review
  禁 transcript

P1：
  working-set
  section/symbol slice
  Capsule
  Receipt

P2：
  Context Request
  profile routing
  watermarks
  multi-session isolation
```

---

# 二十七、本部分最终裁决

```text
1. Context Engine 是确定性工作集编译器，不是完成门；
2. 每轮从 Memory Plane 重建 Capsule，不持续追加旧 Context；
3. 渐进式披露采用 D0 Index → D5 Isolated Review；
4. L1 Base 常态停在 D2，D3 需理由，D5 必须隔离；
5. working-set.yaml 是当前 step 的 Context 白名单；
6. Hot Card 是极简状态投影，属于 Context Capsule 的子集；
7. Capsule 必须绑定 state/plan version，并为每个来源生成 Receipt；
8. 工具全文无损落盘，Context 只使用确定性预览；
9. Flash 与高阶模型使用不同预算，但都不能取消披露纪律；
10. 超预算时优先裁剪低价值背景，绝不删除安全、scope 和验证约束；
11. Claude Code 路径保护稳定前缀和 Prompt Cache；
12. OpenCode 路径先 Prune(hidden)，有损摘要只作最后导航；
13. 成功标准不是“能塞进窗口”，而是第 30 轮仍能维持稳定工作集；
14. Context 丢失后必须能从 state、plan、documents、evidence 和 handoff 重建。
```

---

# 下一部分：第 5/8 部分

将完整输出 **Compact、Checkpoint、Handoff 与 Resume 双栈治理**：

```text
- 无损可回滚与有损不可逆的完整边界
- Context 水位状态转换
- handoff.md 最终 Schema
- Claude Code L1～L5 压缩路径
- Prompt Cache 与 ContentReplacementState 稳定策略
- OpenCode Prune(hidden) → Summary 路径
- OpenCode SQLite 审计与 non-destructive recovery
- checkpoint / Git / 外部副作用的回滚边界
- resume 重建算法
- state/plan/evidence/Artifact 一致性校验
- compact 后禁止跳过 VerifyGate
- Claude Code 与 OpenCode 可粘贴配置
- 故障恢复和验收测试
```