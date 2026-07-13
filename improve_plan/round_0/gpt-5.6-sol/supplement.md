## 结论

**我的 8/8 方案已经覆盖你要求的大约 85%～90%，总体方向一致。**

尤其已经完整覆盖：

- Context Boom：渐进式披露、磁盘记忆、Context Compiler；
- Compact/Resume：Artifact、Handoff、Checkpoint、持久状态重建；
- L1/L2 分级；
- 长任务状态机、无人运行、循环保护；
- AI 自主决策、模型路由、Oracle；
- Oracle / Meta-Oracle 多裁决；
- 文档、Evidence、Error DNA 和归档；
- Claude Code 与 OpenCode 双栈差异化治理。

但有 **4 个地方需要修正，3 个能力需要补强**。其中最重要的是：

> `handoff.md + last_user_prompts` 可以作为轻量交接入口，但不能成为恢复的唯一依据；“每 5 轮注入状态”也不应成为固定机制。

---

# 一、逐项覆盖检查

| 你的要求 | 当前方案覆盖度 | 裁决 |
|---|---:|---|
| 1. Context Boom | 100% | 已覆盖，且是核心设计 |
| 2. Compact 风暴与简单交接 | 80% | 已覆盖，但恢复源需要比 `handoff + prompt` 更硬 |
| 3. 文档、token、日志、Error DNA | 95% | 已覆盖；需冻结各文档的权威边界 |
| 4. 飞轮、自我学习、升华 | 65% | 有 Error DNA/Writeback，但“升华流水线”需补全 |
| 5. L1/L2 | 100% | 已完整覆盖 |
| 6. U 型注意力 | 80% | 头尾设计已覆盖；固定每 5 轮注入应调整 |
| 7. Goal/无人/Loop 硬化 | 85% | 状态机、预算、恢复已有；无人模式契约需补强 |
| 8. 自闭环、容错、抗 Compact | 95% | 已覆盖 |
| 9. AI 自主决策、ROI、Oracle | 90% | 已覆盖；需增加自治权限等级 |
| 10. Oracle + Mate Oracle | 90% | 已覆盖为 Oracle/Multi-Judge/Meta-Oracle；需冻结调用点 |

---

# 二、已完整覆盖的部分

## 1. Context Boom

现方案已经给出完整结构：

```text
磁盘 Memory Plane
    ↓
Document Index / Working Set
    ↓
D0～D5 渐进式披露
    ↓
确定性 Context Compiler
    ↓
本轮最小 Context Capsule
```

这与目标完全一致：

> 文档系统负责记住，索引负责找到，Context Compiler 负责本轮带什么，Prompt 只负责现在做什么。

而且不只是“把内容放磁盘”，还补了几个必要约束：

- 文档按 ID、section、symbol、revision 精确读取；
- 工具全文写 Artifact，Prompt 只留稳定 Preview；
- `working-set.yaml` 是当前 step 的披露白名单；
- Review 默认不进入执行 Context；
- Context 每轮重建，而不是持续追加。

这部分不需要大改。

---

## 2. L1/L2 分级

现方案已经明确：

### L1：快速、窄范围、确定性

```text
init → plan → one action → verify → archive
```

适合：

- 文档修改；
- 单文件修复；
- 低风险配置；
- 有明确测试的局部工作；
- DeepSeek V4 Flash 原子执行。

### L2：复杂、危险、严谨

```text
Research → Plan Review → Checkpoint
→ Execute → Verify → Oracle Review
→ Memory Writeback → Archive
```

适合：

- 跨模块修改；
- 公共 Contract 变化；
- 安全、权限、迁移、外部副作用；
- Opus 高阶推理；
- Oracle / Mate Oracle。

这个分级已经符合你的目标，而且 BASE 不依赖 ENHANCE，L2 可以后置上线。

---

## 3. 抗 Compact 和恢复

现方案已有：

```text
state.json
plan.md
working-set.yaml
evidence.jsonl
artifacts/**
handoff.md
checkpoint
```

恢复顺序也已定义为：

```text
manifest
→ state
→ 当前 plan step
→ handoff 导航
→ working-set
→ decisions/docs
→ evidence/artifact
→ checkpoint
→ 重编译 Capsule
```

因此不会把 Compact 后的模型摘要当成真相。

---

# 三、必须修正的 4 个地方

## 修正 1：`handoff.md + last_user_prompts` 不能是唯一恢复机制

你的“简单实现交接”方向是对的，MVP 完全可以只暴露：

```text
AGENTS.md
  @ .omc/session-handoff.md
  @ .omc/state/last-user-prompt.md
```

但内部恢复不能只有这两个文件，因为它们无法可靠回答：

```text
- 哪个 step 已经通过 VerifyGate？
- 最近一次失败是否被新证据覆盖？
- 某个外部动作是否已经执行？
- 当前 workspace revision 是什么？
- handoff 是否已经过期？
```

最终建议是：

```text
对 Agent 的简单入口：
  handoff.md + last-user-prompt.md

对系统的真实恢复：
  state + plan + evidence + artifact + handoff
```

即：**入口保持简单，底层不能简陋。**

建议 `handoff.md` 最小保留：

```markdown
# Goal
# Current Step
# Last Verified Step
# Last Durable Evidence
# Required Reads
# Next Action
# Blocker
# Do Not Reload
```

`last-user-prompts` 推荐保留最近 1～3 条，而不是无限增长：

```yaml
schema_version: carros.last_user_prompts.v1
task_id: fix-auth-001
state_version: 7
prompts:
  - id: U42
    text: 继续，但不要改变公共错误类型。
    persisted_as:
      - decision:D-001
```

其中已转化为长期约束的用户要求，应写入 `decisions/Contract`，不能永久依赖 prompt 文件。

---

## 修正 2：不要固定“每 5 轮重新注入状态”

U 型注意力设计是正确的：

```text
头部：短小、稳定、高遵循度规则
中部：按需代码和文档切片
尾部：当前状态、TODO、用户最新要求、下一动作
```

但是固定每 5 轮注入存在两个问题：

1. 前 4 轮中的状态可能已经变化；
2. 每 5 轮容易重复注入大段状态，重新制造 Context Boom。

建议改为：

```text
每轮：重新生成短 Hot Tail
每 5 轮：持久化 consistency checkpoint，而不是注入全文
状态变化时：立即刷新 Hot Tail
达到 soft watermark：写 handoff
```

推荐 Prompt 结构：

```text
[HEAD — Stable Core]
哲学铁律、权限、安全、VerifyGate，不超过约 1K tokens

[MIDDLE — Working Set]
当前 step 必需文档、symbol、Evidence Preview

[TAIL — Hot State]
Goal、Current Step、TODO、Blocker、Last Evidence、Next Action、User Delta
```

尾部建议不超过 500～900 tokens，并且每轮确定性生成。

这比“每 5 轮注入一次”更符合 U 型注意力，也更实时。

---

## 修正 3：token 文档不能与任务状态形成双真相源

你希望保留“任务文档系统、token 文档系统、操作日志系统”，可以，但需要冻结职责：

```text
task documents：任务目标、scope、plan、验收条件
state/token：机器运行状态、版本、水位、current step
operation logs：发生过什么
Evidence/Artifact：可验证事实
Error DNA：已验证的可复用失败模式
Handoff：恢复导航
```

如果现有 CarrorOS 已经大量依赖 `.omc/tokens/*.json`，不必立刻删除。建议采用兼容方案：

```text
.omc/tokens/<task-id>.json
```

继续保留，但将其正式定义为机器状态文档，等价于前文的 `state.json`；不要再额外维护第二份 state。

也就是说二选一：

```text
方案 A：token.json 就是唯一 state source
方案 B：state.json 是唯一 source，token.json 只是投影
```

不能让两者都可写。

结合你当前 CarrorOS 的既有结构，我更推荐渐进迁移：

```text
短期：token.json 继续作为唯一机器状态源，补 schema_version/CAS
中期：内部代码统一称 TaskState，路径保持兼容
长期：是否改名 state.json 不影响协议
```

这比立即删除 token 系统更稳妥。

---

## 修正 4：Mate Oracle 不能变成第二个 VerifyGate

双审判官是有价值的，但必须区分：

```text
Oracle：主审，检查方案、实现语义和风险
Mate Oracle：异质性副审，挑战 Oracle、寻找遗漏和反例
VerifyGate：最终读取确定性证据并裁决是否完成
```

正确关系：

```text
Oracle ─────┐
            ├─→ Judge Aggregator → 建议 ACCEPT/WARN/REJECT
Mate Oracle ┘

command/file/user evidence
            ↓
        VerifyGate → VERIFIED/REJECTED/BLOCKED
```

即使两个 Oracle 都 ACCEPT：

```text
测试失败 → 仍不能完成
Artifact 缺失 → 仍不能完成
用户确认缺失 → 仍不能完成
外部副作用 UNKNOWN → 仍不能完成
```

---

# 四、需要补强的 3 个能力

## 补强 1：飞轮系统要增加“候选—验证—升华—回滚”协议

现方案已有：

- Error DNA；
- Memory Writeback；
- ADR/Contract；
- Knowledge Patch；
- 审计指标。

但还缺少你强调的：

```text
claude-next → 升华机制 → kernel → AGENTS
失败经验 → anti-patterns.md
用户偏好 → 越用越懂人
```

建议增加正式的 **Learning Promotion Pipeline**：

```text
运行事件
  ↓
Learning Candidate
  ↓
去重 / 归因 / 证据绑定
  ↓
Sandbox 验证
  ↓
升华裁决
  ├── task memory
  ├── project pattern
  ├── error_dna
  ├── anti-patterns
  ├── runbook
  ├── kernel candidate
  └── user preference
  ↓
观测效果
  ↓
保留 / 降级 / 回滚
```

### 学习层级

```text
L0 Observation
  单次观察，不进入规则。

L1 Task Lesson
  仅当前任务有效。

L2 Project Pattern
  在同项目重复出现，可进入 patterns/error_dna。

L3 Governance Candidate
  可提议进入 anti-patterns/runbook。

L4 Kernel Candidate
  跨项目、多次验证，并经过人类批准。

L5 AGENTS Promotion
  极少发生；属于治理宪法修改，必须人工裁决。
```

### 关键约束

```text
- Agent 不得直接自改 kernel.md 或 AGENTS.md；
- claude-next 只能生成候选 Patch；
- 升华必须有来源任务和 VerifyGate evidence；
- 新规则必须带适用范围、反例和撤销条件；
- 规则增加后必须观察是否提高成本或误阻断率；
- 无收益或误伤的规则自动降级为 advisory。
```

建议 Schema：

```yaml
schema_version: carros.learning_candidate.v1
candidate_id: LC-021
kind: anti_pattern
claim: 不要在异步调用完成后才注册 single-flight promise
source_tasks: [fix-auth-001, fix-auth-014]
evidence_refs: [V-S2-005, EDNA-017]
scope: src/auth/**
confidence: verified_candidate
promotion_target: docs/anti-patterns.md
human_approval_required: false
rollback_condition: false_positive_rate_above_0.10
```

### “越用越懂人”需单独建用户偏好层

不能把用户偏好混进通用 kernel：

```text
组织铁律       → kernel/AGENTS
项目惯例       → project memory
用户偏好       → user-profile.md
任务约束       → manifest/decisions
瞬时指令       → last-user-prompt
```

例如：

```yaml
preference_id: PREF-008
claim: 用户偏好先给结论，再给实现细节
scope: user
confidence: repeated_explicit
observations: 4
last_confirmed_at: "..."
reversible: true
```

涉及隐私、敏感推断或人格判断时禁止自动学习。

---

## 补强 2：无人模式需要独立的 Autonomy Contract

已有状态机、loop、checkpoint 和恢复还不够。无人模式必须明确“系统能自己决定到什么程度”。

建议增加：

```yaml
schema_version: carros.autonomy_policy.v1
mode: unattended

limits:
  max_actions: 30
  max_wall_minutes: 120
  max_cost_usd: 2.00
  max_same_failure_retries: 1
  max_model_escalations: 2
  max_scope_files: 5

allowed:
  - read_repo
  - edit_allowed_paths
  - run_declared_tests
  - create_checkpoint
  - revert_own_changes

requires_confirmation:
  - public_api_change
  - dependency_upgrade
  - external_side_effect
  - destructive_command
  - cost_overrun

stop_conditions:
  - acceptance_verified
  - blocker
  - unknown_external_effect
  - repeated_failure
  - hard_context_watermark
  - budget_exhausted
  - scope_expansion_required

heartbeat:
  every_actions: 3
  write_state: true
  write_handoff: false
```

无人 Loop 应采用：

```text
OBSERVE
→ DECIDE
→ GATE
→ CHECKPOINT（必要时）
→ ACT ONE STEP
→ RECORD
→ VERIFY LOCAL INVARIANT
→ UPDATE STATE
→ CONTINUE / REPLAN / STOP
```

硬规则：

```text
- 一次循环只执行一个可回滚 action；
- 每次循环都有进展度量；
- 连续无进展时停止，而不是无限思考；
- 无人模式不能自动扩大 scope；
- 无法恢复到确定状态时 BLOCKED；
- compact/resume 后不能盲目重放 action；
- 所有停止都生成 handoff 和原因。
```

推荐增加 `progress_fingerprint`，检测空转：

```text
hash(current_step, workspace_diff, latest_evidence, blocker)
```

连续多轮 fingerprint 不变即判定 `NO_PROGRESS_LOOP`。

---

## 补强 3：把“五步法 + 双审判官”的调用点正式冻结

建议 CarrorOS 五步法统一为：

```text
1. Observe
   读取 Hot State、当前 step、必要证据。

2. Plan
   生成一个原子 Action Proposal。

3. Judge Plan
   PreActionGate；L2/高风险时 Oracle + Mate Oracle 审方案。

4. Execute
   Checkpoint 后只执行一个 action，结果写 Artifact。

5. Verify & Learn
   VerifyGate 校验；必要时双 Oracle 审 residual risk；
   通过后生成 Learning Candidate。
```

双审判官不应每步都调用，否则会造成成本和上下文反噬。

建议触发矩阵：

| 决策点 | L1 | L2/危险 |
|---|---|---|
| 方案生成后 | PreActionGate | PreActionGate + 双 Oracle |
| 普通局部修改后 | VerifyGate | VerifyGate |
| 公共 Contract 修改后 | 可升级 L2 | VerifyGate + 双 Oracle |
| Archive 前 | VerifyGate 汇总 | VerifyGate + 风险审判 |
| 学习升华到 kernel | 禁止自动 | 双 Oracle + 人类批准 |

Mate Oracle 应采用不同角度，而不是重复主 Oracle：

```text
Oracle：正确性、架构一致性、方案可行性
Mate Oracle：反例、边界、误伤、过度工程、用户意图偏离
```

这样才是真正的“双审判”，而不是同一个意见说两遍。

---

# 五、建议的最终 CarrorOS 结构

```text
┌──────────────────────────────────────┐
│ HEAD：Kernel / AGENTS / 铁律          │
│ 小、稳定、高遵循度                   │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ Memory Plane                         │
│ task / token-state / plan / docs     │
│ operation-log / evidence / artifact  │
│ error_dna / anti-patterns / profile  │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ Context Compiler                     │
│ Index → Summary → Slice → Neighbor   │
│ 每轮生成最小工作集                    │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ Autonomous Loop                      │
│ Observe → Plan → Judge → Act → Verify│
│ L1 Fast / L2 Rigorous                │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ TAIL：Hot State                      │
│ Goal / TODO / Evidence / User Delta  │
│ Next Action / Blocker                │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ Learning Flywheel                    │
│ Candidate → Validate → Promote       │
│ Error DNA / Anti-pattern / Runbook   │
│ Kernel Candidate / User Preference   │
└──────────────────────────────────────┘
```

---

# 六、建议冻结的最终原则

```text
1. 磁盘负责记忆，Context 只负责当前工作集。
2. handoff + last_user_prompts 是简单入口，不是唯一真相源。
3. token/state 必须只有一个可写权威源。
4. 每轮刷新短 Hot Tail，不固定每 5 轮注入大段状态。
5. 每 5 轮可以做持久化 checkpoint 和一致性检查。
6. L1 默认快而窄；风险、歧义、跨模块才升级 L2。
7. 无人模式必须有预算、权限、重试和停止条件。
8. 一个 loop 只执行一个可验证 action。
9. Oracle 审语义和风险，Mate Oracle 主攻反例和误伤。
10. 双 Oracle 都不能替代 VerifyGate。
11. 飞轮不能直接自改 kernel/AGENTS，只能生成升级候选。
12. 只有重复出现、证据充分、收益可观测的经验才能升华。
13. 用户偏好与系统铁律分层，避免“越懂人”变成错误固化。
14. Compact、Summary、Handoff 都不能制造完成事实。
15. 系统成长的指标不是规则越来越多，而是成功率提高、成本下降、误阻断减少。
```

# 最终评价

你的十项要求不是与前述 8/8 方案冲突，而是进一步明确了 CarrorOS 的“灵魂”：

> **CarrorOS 不只是上下文治理工具，而是一个以磁盘记忆为基础、以可验证循环为执行核心、以受控升华为成长机制的长期自治 Agent OS。**

我建议保留现有架构主体，只做以下增补：

```text
P0：保留 handoff + last-user-prompt 的简单交接入口
P0：冻结 token/state 唯一真相源
P1：每轮 Hot Tail，替代固定每 5 轮大段注入
P1：增加 Autonomy Contract 和无进展熔断
P2：增加 Learning Candidate → Promotion → Rollback 飞轮
P2：增加独立 user preference memory
P2：冻结 Oracle/Mate Oracle 的异质职责和触发点
```

补完这几项后，覆盖度可以达到约 **95% 以上**，并且不会因为追求“自成长”而破坏 CarrorOS 最重要的三条底线：

```text
不自改治理
不以摘要代替真相
不以审判代替验证
```
