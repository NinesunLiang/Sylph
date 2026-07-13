下面按 **GPT-5.6 Sol 的工程治理视角**评价 Hermes Agent 的执行方案。重点不是再次复述方案，而是判断它是否具备：**可实施、可验证、可回滚、可持续演进**四个条件。

# 结论

```yaml
verdict: CONDITIONAL_APPROVE
phase_0: GO
phase_0_5: GO_AFTER_CORRECTIONS
phase_1_plus: HOLD
overall_score: 8.2/10
confidence: medium_high
```

Hermes 的方案已经达到 **可以进入 Phase 0 施工**的程度，而且 Phase 0 是整份方案中最成熟的部分。

但在正式进入 Phase 0.5 前，必须解决四个结构性问题：

1. `token.json` 与 `state.json` 的唯一真相源冲突。
2. Phase 0 的测量口径和验收口径不完全一致。
3. 工具结果“稳定预览”的定义还不满足真正的内容寻址稳定性。
4. Claude Code 与 OpenCode 的执行路径没有明确拆开。

我的判断与前一份评价总体同向，但有两个重要差异：

- 我不认为“七件套”本身是问题，问题是**是否一次性强制创建、是否存在冗余写入**。
- 我不建议现在增加 `type: oracle` 验证项。Oracle 是**有损、非确定性评审**，不能和确定性 Verify Evidence 混为一类。

---

# 一、执行方案做得好的地方

## 1. Phase 0 的问题边界正确

Hermes 没有先改状态机、Oracle 或飞轮，而是先处理：

```text
Context Boom
→ 基线测量
→ CLAUDE.md Slim
→ Hot Card
→ 工具结果落盘
→ 读盘门禁
→ Context composition 固化
→ 成本报表
→ 回归验证
```

这是正确顺序。

Phase 0 的目标是把可控上下文从约 `19K` 降到 `8K`，而不是声称能消除 Claude Code 的固定开销。这说明它区分了：

- 平台固定成本；
- 项目注入成本；
- 工具输出成本；
- 历史增长成本。

这比只观察整轮 input token 更有诊断价值。

## 2. 每轮重建 Context，而不是继续追加

S6 的固定 composition：

```text
Slim System
Hot Card
当前文件切片
最近工具预览
用户本轮指令
```

符合“Context Capsule 每轮重新编译”的方向。

这部分属于：

- 文件切片、Artifact、原始状态：**无损可回滚**；
- Hot Card：从结构化状态派生，可重建，原则上也是**无损可回滚**；
- LLM 生成 handoff 或摘要：若替代原始状态，则是**有损不可逆**。

Hermes 应把这个分类直接写进实现文档，避免日后把 Capsule 误当新的真相源。

## 3. 工具结果落盘是正确的第一层治理

S4 将长输出完整保存到 `artifacts/`，模型仅接收预览。这解决了两个问题：

- 长日志不持续污染主会话；
- 原文仍可审计和重新加载。

只要 Artifact 带有 hash、大小、生成命令和 exit code，这一层就是**无损可回滚**，不属于有损 compaction。

## 4. PreTool Gate 有明确的阻断能力

六条规则不是“建议模型少读”，而是可以执行的 Gate：

```text
单 tick 文件数限制
大文件 offset/limit
review 文档默认禁入
secret 路径阻断
过宽 glob 阻断
本轮预算阻断
```

这比在 `CLAUDE.md` 里仅写行为约束可靠。

尤其是 review 文档默认不披露，能够避免旧审核意见、模型长篇论证和当前任务状态混进同一个 Context。

## 5. 负向 SLO 是正确的上线判断方式

这些指标方向正确：

```text
tool_full_in_context_rate
l5_as_memory
cache_hit_rate
median_in
l5_rate
```

相比“功能已经实现”，负向 SLO 更能回答“系统是否已经不稳定”。

建议保留这些红线，并增加：

```text
verified_without_evidence
resume_without_canonical_state
handoff_used_as_state
context_growth_tokens_per_turn
preview_hash_mismatch
token_cost_usd_per_session
compaction_trigger_rate
```

---

# 二、必须阻断的高优先级问题

## P0-1：`token.json` 与 `state.json` 仍然冲突

已检索到的方案同时出现：

```text
state.json：唯一运行状态机，兼容旧 token.json
```

以及既有结论：

```text
保留 token.json，并将它正式定义为 TaskState 的持久化格式
```

外部副作用部分又写：

```text
任务状态：state.json CAS 版本
```

这不是命名偏好，而是协议冲突。只要两者都可能被写入，就会产生：

- Resume 读取不同版本；
- lint 检查与执行器结果不一致；
- CAS 只保护一个文件；
- handoff 指向过期状态；
- 多 Agent 发生双写。

**必须采用单写者方案：**

```yaml
task_state:
  logical_schema: carros.task_state.v1
  canonical_path: ".omc/tasks/{task_id}/token.json"
  write_targets:
    - token.json
  compatibility:
    state_json:
      mode: read_only_alias
      expires_after: phase_1
  cas:
    field: revision
    required_on_write: true
  prohibited:
    - dual_write
    - last_write_wins
    - handoff_state_reconstruction
```

这里保留 `token.json` 是因为已有工具链依赖它。逻辑对象可以叫 `TaskState`，没有必要为了语义正确而改文件名。

## P0-2：测量指标口径矛盾

S7 示例里出现：

```text
median_in: 7400 controllable / 23400 total
```

但红线又写：

```text
median_in(p0) > 12000 → FAIL（可调控部分）
```

S8 则要求：

```text
可控 median ≤ 8K
```

因此现在存在三个不同目标：

- 理想目标：`8K`
- S8 验收：`≤8K`
- S7 红线：`≤12K`

必须区分 **目标、SLO、硬上限**，不能都叫 PASS。

建议统一为：

```yaml
context_budget:
  controllable:
    target_median_tokens: 8000
    slo_p50_tokens: 9000
    hard_p95_tokens: 16000
  total:
    target_median_tokens: 24000
    hard_p95_tokens: 48000
```

同时不要把“固定开销约 16K”当常量直接相减。它可能随工具声明、MCP、模型和 Claude Code 版本变化。应该每轮实测或按版本建立 baseline。

## P0-3：当前 Preview 还不能保证真正稳定

方案中的示例预览包含：

```text
path
exit_code
bytes
content[:max_chars]
```

然后要求：

> 同一 content 多次 store，preview 字符串相同。

但如果每次分配不同的 `tool_NNNN.log`，`path` 就不同，因此整个 preview 不可能字节级一致。

另外，简单使用 `content[:2000]` 有三个问题：

- UTF-8 字符边界可能与 byte/char 口径混乱；
- ANSI、时间戳、临时路径等动态内容会破坏稳定性；
- 只保留开头可能丢掉测试失败摘要或末尾 exit information。

建议改成内容寻址：

```python
def build_preview(content: bytes, exit_code: int) -> dict:
    digest = sha256(content).hexdigest()
    normalized = normalize_tool_output(content)
    return {
        "artifact_id": f"sha256:{digest}",
        "exit_code": exit_code,
        "bytes": len(content),
        "head": utf8_slice(normalized, 1200),
        "tail": utf8_tail(normalized, 600),
        "truncated": len(normalized) > 1800,
    }
```

Artifact 路径应由 digest 派生，或者路径不要进入 cache-sensitive 前缀：

```text
.omc/artifacts/sha256/ab/cd/<digest>.log
```

还应区分两种稳定性：

- 原始 Artifact hash：**无损可审计**；
- normalized preview：为了缓存去除动态噪音，属于**有损展示**，但不能替代原始 Artifact。

## P0-4：双栈路径没有分离

当前可见实现主要是：

```text
.claude/scripts/
.claude/hooks/
CLAUDE.md
Claude Checkpoint
Claude AutoCompact
```

这说明 Phase 0 实际是 Claude Code 专用实现，而不是 Claude Code/OpenCode 双栈实施方案。

这本身可以接受，但必须明确声明范围。不能把 Claude 的 L1-L5、Checkpoint、prompt cache 机制直接映射成 OpenCode 的 compaction 语义。

建议补充：

```yaml
platform_scope:
  phase_0:
    platform: claude_code
  phase_0_5:
    platform: claude_code
  opencode:
    implementation_phase: phase_1_5
    adapter_contract:
      - session_roles
      - single_state_writer
      - non_destructive_prune
      - sqlite_audit_retention
      - recent_two_turns_protection
      - skill_output_protection
      - forty_k_token_safety_margin
```

**Claude Code 路径：**

```text
工具落盘/裁剪/微压缩：无损或近似无损，可重建
L4 折叠：有损但应保留回滚入口
L5 AutoCompact：有损不可逆，不得作为记忆源
```

**OpenCode 路径：**

```text
Prune hidden 标记：非物理删除，可审计回溯
隐藏 Agent 摘要：有损不可逆
SQLite 原始记录：保留，作为审计链
```

两者必须拥有不同 adapter 和指标，不应共用一个 `compaction_level` 字段假装语义相同。

---

# 三、我不同意前一评价中的两个建议

## 1. 不建议把 Oracle 加进普通 `verify.type`

确定性验证与 Oracle 评审不是同一种证据。

```yaml
verify:
  - type: command
  - type: file_assertion
  - type: schema_check
```

这些可以被复跑和机械判断。

Oracle 输出属于：

- 非确定性判断；
- 模型相关；
- Prompt 和上下文相关；
- 可能有成本预算和置信度；
- 不能证明测试实际通过。

因此应单独建评审层：

```yaml
review:
  trigger:
    risk_level: high
    retry_count_gte: 2
  oracle:
    model_profile: opus_reasoning
    budget_usd: 0.05
    output_schema: carros.oracle_verdict.v1
```

VerifyGate 必须先满足确定性 Evidence；Oracle 只能判断 residual risk，不能把 FAIL 改成 VERIFIED。

## 2. 七件套不是天然过度设计

以下职责本身是合理的：

```text
manifest：任务身份与索引
token：运行状态
plan：计划
working-set：上下文白名单
handoff：恢复导航
evidence：证据索引
artifacts：原始输出
```

真正的问题是：

- 是否每个 L1 小任务都强制创建全部文件；
- 是否多个文件重复保存同一个字段；
- 是否需要 LLM 同步维护；
- 是否存在多写者。

建议按任务等级实例化：

```yaml
task_profiles:
  L1:
    required: [token.json, artifacts]
    derived: [hot_card]
    optional: [plan.md, handoff.md, evidence.jsonl]
  L2:
    required:
      - token.json
      - plan.md
      - working-set.yaml
      - evidence.jsonl
      - artifacts
    conditional: [handoff.md]
  L3:
    required:
      - manifest.yaml
      - token.json
      - plan.md
      - working-set.yaml
      - handoff.md
      - evidence.jsonl
      - artifacts
```

这样既保留结构化治理，也避免小任务被文档税拖垮。

---

# 四、Phase 0 的具体修订建议

## S1：基线样本需要扩大或分层

`3–5` 条会话只能用于发现问题，不能支持稳定的 p95。

建议：

```yaml
baseline:
  exploratory_sessions: 5
  acceptance_turns_min: 30
  task_classes:
    - read_only
    - one_file_edit
    - edit_and_test
    - long_tool_output
    - resume_after_handoff
```

p95 若样本不足，不应作为硬统计结论。

## S2：不要全局禁止 Oracle

Slim Rail 中“禁止调用 Oracle”应限定为：

```text
L1 / Phase 0 baseline tasks 禁止 Oracle
```

否则未来 L2 高风险流程会和全局 CLAUDE.md 冲突。

## S3：Hot Card 必须是派生视图

Hot Card 不能被单独编辑，也不能承担唯一状态：

```yaml
hot_card:
  source:
    - token.json
    - current_plan_step
    - last_evidence
  writable: false
  deterministic: true
```

验收除长度外应加入 snapshot test：

```text
同一输入状态 → 完全相同 Hot Card
字段缺失 → 明确占位，不改变字段顺序
```

## S5：PreTool Gate 不应误伤必要读取

“每 tick 最多两个文件”和“超过 200 行必须 offset/limit”作为默认策略合理，但不能只返回 BLOCK。

需要结构化结果：

```yaml
decision: ALLOW | DENY | NARROW | CHECKPOINT_FIRST
reason_code: G1_FILE_COUNT
suggested_request:
  path: src/auth.ts
  offset: 120
  limit: 80
```

这样低能力模型也知道如何收窄，而不是反复重试。

## S7：增加成本和增长速率指标

至少输出：

```yaml
observability:
  context:
    controllable_tokens_p50: 0
    controllable_tokens_p95: 0
    context_growth_tokens_per_turn: 0
    hot_card_tokens_p95: 0
  cache:
    cache_hit_rate: null
    stable_prefix_hash_changes: 0
  compaction:
    l4_count: 0
    l5_count: 0
    l5_ratio: 0
  correctness:
    verified_without_evidence: 0
    resume_block_count: 0
  cost:
    token_usd_per_session_p50: 0
    token_usd_per_completed_task: 0
    oracle_cost_share: 0
```

若 Claude Code 无法暴露真实 cache hit rate，应记为 `null/not_observable`，不能自动判 FAIL。

## S8：补充真正能触发治理机制的测试

现有 H1-H3 偏轻。至少增加：

```text
H4：100KB 测试日志，验证 Artifact + head/tail preview
H5：12+ 回合、多文件读取，验证 Context 不线性增长
H6：强制接近 soft watermark，验证 handoff/resume
H7：模拟 IN_FLIGHT 外部副作用，验证 Resume BLOCKED
H8：CAS 冲突，验证第二写者失败且不覆盖状态
```

---

# 五、Claude Code 与 OpenCode 的实施裁决

## Claude Code 路径

Phase 0 可立即实施：

```text
S1 baseline
S2 Slim Rail
S3 deterministic Hot Card
S4 content-addressed Artifact
S5 PreTool Gate
S6 stable composition
S7 observability
S8 regression
```

关键 SLO：

```yaml
claude_code_slo:
  cache_hit_rate_target: 0.60
  stable_prefix_hash_change_rate: "< 0.05"
  l5_ratio: "< 0.05"
  l5_as_memory: 0
  controllable_tokens_p50: "<= 9000"
  total_tokens_p95: "<= 48000"
  verified_without_evidence: 0
```

`cache_hit_rate` 不可观测时，用 `stable_prefix_hash_change_rate` 作为代理指标。

## OpenCode 路径

当前方案不能视为已完成 OpenCode 设计，只能算预留。

进入 OpenCode 实施前必须增加：

```yaml
opencode_governance:
  sessions:
    roles: [execute, retrieve, review, govern]
    max_state_writers: 1
    writer_lease_required: true
  compaction:
    prune:
      destructive: false
      preserve_recent_turns: 2
      safety_margin_tokens: 40000
      protect_skill_outputs: true
    llm_summary:
      lossy: true
      trigger_only_after_prune: true
  audit:
    sqlite_retention: enabled
    compacted_rows_physically_deleted: false
```

OpenCode 指标：

```yaml
opencode_slo:
  prune_physical_delete: 0
  prune_to_summary_ratio: "> 4"
  writer_conflict_count: 0
  resume_from_sqlite_success_rate: "> 0.99"
  lossy_summary_trigger_rate: "< 0.10"
  token_usd_per_session: tracked
```

---

# 六、实施放行矩阵

| 阶段 | 裁决 | 放行条件 |
|---|---|---|
| Phase 0 / S1 | **GO** | 先记录现状，禁止边测边改 |
| Phase 0 / S2-S6 | **GO** | canonical state 路径先钉死 |
| Phase 0 / S7-S8 | **GO** | 统一 8K/9K/16K 预算口径 |
| Phase 0.5 | **条件放行** | handoff 非真相源、Evidence Gate、CAS、按等级实例化文件 |
| Phase 1 | **暂缓** | Phase 0.5 连续通过 H4-H8 |
| Phase 2 飞轮/无人 | **暂缓** | Knowledge Patch 不默认注入 Context |
| Phase 3 双审判官 | **按需** | 仅高风险/争议场景，成本与 residual risk 可观测 |
| OpenCode 接入 | **独立项目放行** | adapter、单写者、非破坏 prune、SQLite 审计齐备 |

---

# 七、最终评分

| 维度 | 得分 | 判断 |
|---|---:|---|
| Phase 0 问题聚焦 | 9.5 | 非常准确 |
| 实施可操作性 | 9.0 | S1-S8 已接近任务板 |
| 上下文稳定性 | 8.5 | Preview 内容寻址还需修正 |
| 状态一致性 | 6.5 | token/state 冲突是主要阻断项 |
| 验证与证据 | 8.5 | 方向正确，需与 Oracle 分层 |
| 可观测性 | 8.5 | 已有红线，缺增长率/CAS 等指标 |
| Claude Code 适配 | 9.0 | Phase 0 很贴合 |
| OpenCode 适配 | 5.0 | 目前更多是概念承诺 |
| 成本治理 | 7.5 | 有报表，缺明确模型路由落地 |
| 长期可持续性 | 8.0 | 分层正确，但后续复杂度仍需 Gate |
| **综合** | **8.2/10** | **可开工，但不是无条件全阶段批准** |

# 最终裁决

Hermes 的执行方案不是“继续讨论的草案”，而是可以开始实施的 **Phase 0 工程计划**。它最大的价值是把 Context 治理从文档原则转换成了 `Hot Card + Artifact + Gate + Metrics + Regression` 的可执行链条。

正式发令时应限定为：

```text
批准 Hermes 实施 Phase 0。

开工前先完成：
1. token.json 作为唯一 TaskState 写入源；
2. 统一 Context 目标/SLO/硬上限口径；
3. Tool Artifact 改为内容寻址，Preview 做确定性快照测试；
4. 明确 Phase 0/0.5 为 Claude Code 路径，OpenCode 独立适配。

禁止抢跑：
- state.json 双写迁移
- Oracle 进入普通 VerifyGate
- 飞轮自动回写 Context
- Multi-Judge
- OpenCode 与 Claude 共用压缩语义
```

完成上述修订后，我对 **Phase 0 给出正式 GO**；Phase 0.5 应在 Phase 0 的 before/after 数据、H4-H8 回归和 CAS 冲突测试通过后再放行。