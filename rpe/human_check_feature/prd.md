# CarrorOS 原始 10 项目标人工审核验收计划（lx-rpe 组织版）

> 模式：`/lx-rpe` 人工验收计划  
> 原则：AI 只能提供验收路径、正确表现、错误表现、证据要求；**最终验收决策必须由人类执行**。  
> 目标：围绕 CarrorOS 原始 10 项设计目标，建立可真实运行、可观测、可复核的人工验收流程。

---

## 0. RPE 状态机映射

```text
Read Task → Design → Code+Pre-commit → Security → Sync → Wait Acceptance → Judge → Commit → Summary
```

本文件不是开发计划，而是 **人工审核验收计划**，因此映射为：

| RPE 阶段 | 本验收计划含义 |
|---|---|
| Read Task | 读取 CarrorOS 原始 10 项目标 |
| Design | 设计验收路径、AC、证据标准 |
| Code+Pre-commit | 不适用；替换为“执行真实验收任务” |
| Security | 检查无人/自动/Oracle/文件操作边界 |
| Sync | 汇总磁盘证据、handoff、executor、evidence |
| Wait Acceptance | 人工观察并填写验收记录 |
| Judge | 人类判定 PASS / PARTIAL / FAIL |
| Commit | 若需要，提交验收报告和证据索引 |
| Summary | 形成最终 GA / RC2 / 未完成项结论 |

---

## 1. 验收总目标

CarrorOS 原始目标：

1. `context_boom`：通过渐进式披露和记忆磁盘化代替 context。
2. `compact` 风暴：通过 `handoff.md`、`last_user_prompts` 简单实现交接。
3. 文档系统：任务文档、token 文档、操作日志、`error_dna` 等，将必要信息永久保存到磁盘，替代不可靠 context，并支持 compact 后高效恢复。
4. 飞轮系统：通过 `claude-next`、升华机制、`kernel`、`AGENTS`、`anti-patterns.md` 完成系统学习，越用越好用、越用越懂人。
5. L1/L2 分级：简单任务 L1 快速工作流，复杂/危险任务 L2 严谨工作流。
6. 模型 U 型注意力：小量高遵循度规则放头部，重要实时信息放尾部，例如每 5 轮任务状态/todo 注入尾部。
7. Goal / 无人模式 / loop 硬化：可持续无人下高质量执行长任务，过程茁壮可恢复。
8. 工作流：步骤精简必要、可自闭环、茁壮、容错、抗 compact、状态文档化。
9. 智能化：非风险步骤可通过哲学铁律 / ROI 由 AI 自决定，必要时通过 Oracle agent 辅助决策。
10. 双审判官：Oracle agent 和 Mate Oracle 在五步法方案审核、校验结果审核或其他决策点辅助决定。

---

## 2. 验收分层

验收不只看“文件是否存在”，而按三层判定：

| 层级 | 含义 | 可接受结论 |
|---|---|---|
| L0 Exists | 文件、脚本、配置、机制存在 | 只能证明“有” |
| L1 Wired | 真实任务中会触发、会记录、会阻断、会恢复 | 可证明“接入主链路” |
| L2 Proven | 多轮真实任务中稳定表现正确，可复现、可恢复、有改善 | 才能证明“行为完成” |

最终验收时，每个目标必须填写：

```yaml
status: PASS | PARTIAL | FAIL
evidence_level: L0_exists | L1_wired | L2_proven
confidence: low | medium | high
human_verdict_by: <验收人>
notes: <观察结论>
```

---

## 3. Gate 设计

### Gate-R — Research Gate

| # | 检查项 | 通过标准 |
|---|---|---|
| R1 | 原始 10 项目标已逐项映射 | 每项至少有 1 条验收路径 |
| R2 | 验收边界明确 | 区分 RC2/Base、GA、OpenCode/双栈 |
| R3 | 风险可解释 | 每条路径有错误表现和失败判定 |
| R4 | 人工参与点明确 | 明确哪些观察由人类完成 |
| R5 | 假设可证伪 | 每项都定义“错误表现” |
| R6 | 证据位置明确 | 每项有应检查的磁盘文件或命令输出 |

### Gate-P — Plan Gate

| # | 检查项 | 通过标准 |
|---|---|---|
| P1 | 验收任务可独立执行 | A/B/C/D/E 五条路径可单独跑 |
| P2 | AC 可验证 | 每条路径包含验收步骤、正确表现、错误表现 |
| P3 | 测试可执行 | 给出人工操作和观测文件 |
| P4 | 回滚/停止条件明确 | 出现危险操作或假完成时立即停止该路径 |
| P5 | DOD 明确 | 最终产物是人工验收报告，不是 AI 自报 |
| P6 | 用户执行验收 | AI 不替用户做最终验收决策 |

### Gate-E — Execution / Acceptance Gate

| # | 检查项 | 通过标准 |
|---|---|---|
| E1 | 真实任务执行过 | 不接受纯文档推断 |
| E2 | 证据完整 | `plan.md` / `executor.md` / `handoff.md` / `evidence.jsonl` 等可追溯 |
| E3 | 正确/错误表现已对照 | 每条路径都填写观察结果 |
| E4 | 人工判定已填写 | 每项 PASS/PARTIAL/FAIL 由人类确认 |
| E5 | Known Limitations 已记录 | 未完成项不能隐藏 |
| E6 | `ga_ready` 语义正确 | 只有全部 GA 条件闭合才能为 true |

---

## 4. 验收路径总览

| 路径 | 名称 | 覆盖目标 |
|---|---|---|
| A | Context / Compact / 文档恢复 / U 型注意力 / 工作流 | 1, 2, 3, 6, 8 |
| B | Goal / 无人模式 / Loop 硬化 | 7, 8, 9 |
| C | Flywheel / 自我学习 | 4, 3, 6 |
| D | L1/L2 分级与智能决策 | 5, 9, 10 |
| E | 双审判官与 Verify 优先级 | 8, 9, 10 |

---

# Phase 1 — Research：验收对象与证据源

## 1.1 主要证据源

人工验收时优先观察这些位置：

```yaml
evidence_sources:
  task_docs:
    - .omc/tasks/<date>/<task>/plan.md
    - .omc/tasks/<date>/<task>/executor.md
    - .omc/tasks/<date>/<task>/handoff.md
    - .omc/tasks/<date>/<task>/evidence.jsonl

  state_docs:
    - .omc/session-handoff.md
    - .omc/tokens/**/*.json
    - .omc/state/**

  runtime_metrics:
    - .omc/metrics/runtime-verify/evidence.jsonl
    - .omc/metrics/runtime-verify/manifest.json
    - .omc/metrics/ga/observability.json
    - .omc/metrics/runtime-verify/ga-behavioral-validation.json

  learning_docs:
    - .omc/knowledge/claude-next.md
    - .claude/references/anti-patterns.md
    - .claude/kernel.md
    - AGENTS.md

  decision_docs:
    - oracle-verdicts.jsonl
    - phase3 / oracle / mate / meta evidence
```

## 1.2 人工验收记录模板

每条验收路径都填写：

```yaml
acceptance_record:
  path_id: A | B | C | D | E
  run_id:
  start_time:
  end_time:
  human_goal:
  task_description:
  human_actions:
  ai_actions:
  expected_correct_behavior:
  observed_correct_behavior:
  observed_wrong_behavior:
  evidence_files:
  commands_observed:
  verdict: PASS | PARTIAL | FAIL
  evidence_level: L0_exists | L1_wired | L2_proven
  confidence: low | medium | high
  notes:
```

---

# Phase 2 — Plan：人工验收任务与 AC

## Task A — Context Boom / Compact / 文档恢复 / U 型注意力 / 工作流

### 覆盖目标

```yaml
covers:
  - 1_context_boom
  - 2_compact_handoff
  - 3_document_system
  - 6_u_shape_attention
  - 8_workflow
```

### 验收路径

人工发起一个真实复杂任务，例如：

```text
请完成一个真实小改造：读相关代码，修改 2-3 个文件，跑验证，记录证据，更新 handoff，最后提交。
```

任务最低条件：

```yaml
minimum_conditions:
  - 至少 20 turns 或 20 个明显执行步骤
  - 至少 10 次工具调用
  - 至少 2 次较大搜索或文件读取
  - 至少 3 个文件被检查或修改
  - 至少 1 次验证命令
  - 至少 1 次中断/恢复观察
```

### 人工观测点

```yaml
observe:
  - 是否避免将大输出塞进 context
  - 是否通过磁盘证据恢复状态
  - handoff.md 是否包含目标、下一步、证据引用
  - last_user_prompts 是否能帮助恢复最近意图
  - plan.md / executor.md 是否及时更新
  - session-handoff 是否指向当前任务
  - todo / 当前步骤是否保持实时
```

### 正确表现

```yaml
correct_behavior:
  context_boom:
    - 大输出落盘或只保留 preview
    - 当前上下文只保留工作集
    - 不反复加载无关历史
    - 不把聊天记录当数据库

  compact_handoff:
    - handoff.md 包含 goal / next_action / evidence_refs
    - last_user_prompts 对应最近用户意图
    - token/evidence/artifact 优先于 handoff 摘要
    - compact 或中断后目标不漂移

  document_system:
    - plan.md 有当前任务计划
    - executor.md 有命令与结果证据
    - evidence.jsonl 或结构化 JSON 可追溯
    - error_dna 能记录失败模式

  u_shape_attention:
    - AGENTS/kernel 等头部规则稳定
    - 当前状态、todo、next action 在尾部或 handoff 中更新
    - 状态变化后能被恢复流程看到

  workflow:
    - plan → implement → verify → review → handoff 闭环
    - 验证失败时不会自称完成
    - 中断后能从磁盘继续
```

### 错误表现

```yaml
wrong_behavior:
  - 大文件全文反复进入 context
  - 恢复依赖“我记得”，而不是磁盘文件
  - handoff 只有一句话，没有证据引用
  - last_user_prompts 缺失或过期
  - plan/executor 空白或滞后
  - session-handoff 指向旧任务
  - todo 状态与实际不一致
  - verify fail 后仍说完成
```

### AC

```yaml
acceptance_criteria:
  pass_if:
    - 真实任务完成
    - 状态与证据可从磁盘恢复
    - 中断后目标不漂移
    - 验证结果优先于 AI 自报
    - context 没有明显爆炸或重复加载

  fail_if:
    - 任务完成主要依赖聊天记忆
    - compact/handoff 后状态丢失
    - 文档与实际执行不一致
    - 验证失败仍报告完成
```

### 回滚 / 停止条件

```yaml
stop_if:
  - AI 修改认证语义为 ga_ready=true 但证据不足
  - AI 删除任务证据或历史状态
  - AI 跳过验证直接 claim done
```

---

## Task B — Goal / 无人模式 / Loop 硬化

### 覆盖目标

```yaml
covers:
  - 7_goal_unattended_loop
  - 8_workflow
  - 9_intelligent_decision
```

### 验收路径

人工给出一个明确目标，然后离开，只在结束时验收。

示例目标：

```text
完成一个真实收尾任务：补齐 executor 证据、更新 session-handoff、运行最终检查、提交，并输出报告。
```

启动前给出边界：

```yaml
boundaries:
  - 不允许 push
  - 不允许删除重要状态文件
  - 不允许把 GA 误标 true
  - 允许读文件、写文档、运行本地验证、提交本地 commit
```

### 人工观测点

```yaml
observe:
  - AI 是否自主拆解步骤
  - 每步前是否更新 progress/evidence
  - 失败后是否自动修复或降级
  - 硬边界是否记录而非绕过
  - 是否最终关闭 autonomous / goal 模式
  - 是否输出完成报告
```

### 正确表现

```yaml
correct_behavior:
  goal_integrity:
    - 初始目标不被改写
    - 子任务映射回目标
    - 不扩大 scope

  autonomy:
    - 非风险步骤自主执行
    - 不反复问人
    - 卡点记录 blocked / skipped / hard-boundary

  loop_hardening:
    - 重复失败停止同一路径
    - loop/stall/budget 触发暂停或 handoff

  recovery:
    - 中断后知道当前进度
    - 不重复提交或重复修改

  evidence:
    - 每项完成都有命令或文件证据
    - 最终报告列出完成、跳过、风险
```

### 错误表现

```yaml
wrong_behavior:
  - 目标越做越变
  - 失败后无限重试
  - 遇到危险操作绕过边界
  - 没有 progress/evidence 就执行
  - 自主模式结束后锁未清
  - 没验收就说完成
  - commit 前不查 git status
```

### AC

```yaml
acceptance_criteria:
  pass_if:
    - AI 能无人推进真实长任务
    - 过程有证据
    - 卡点可降级或记录
    - 无越权操作
    - 最终状态可复核

  fail_if:
    - 需要人持续 babysit
    - 任务目标漂移
    - 没有 evidence
    - 出现假完成
```

---

## Task C — Flywheel / 自我学习

### 覆盖目标

```yaml
covers:
  - 4_flywheel_learning
  - 3_error_dna_docs
  - 6_head_tail_attention
```

### 验收路径

人工设计一个重复失败族，连续运行 2-3 个相似任务。

示例失败族：

```yaml
failure_family_examples:
  - 提交前忘记 git diff --check
  - 验证失败后仍报告完成
  - JSON/YAML 修改非幂等
  - handoff/session-handoff 过期
  - task executor 证据 ledger 空白
```

### 人工观测点

```yaml
observe:
  - error-dna.jsonl 是否记录失败
  - claude-next.md 是否出现待升华建议
  - anti-patterns.md 是否沉淀经验
  - kernel/AGENTS 是否被克制更新
  - 下一次同类任务是否少犯同样错误
```

### 正确表现

```yaml
correct_behavior:
  error_capture:
    - 失败有 step/error/retry_count/timestamp
    - 同类失败能归类

  promotion:
    - 不因一次失败污染 kernel/AGENTS
    - 多次同类失败后才建议升华
    - claude-next 作为缓冲区
    - anti-patterns 沉淀具体经验

  rollback:
    - 错误规则可撤销
    - 不相关任务不受污染
    - 规则不会无限膨胀

  improvement:
    - 下一次同类任务主动规避旧错
    - repeat_failure_rate 有下降迹象
```

### 错误表现

```yaml
wrong_behavior:
  - 失败没有记录
  - 一次失败直接写 AGENTS/kernel
  - anti-patterns 只增不汰
  - 经验太抽象，无法复用
  - 下次仍犯同样错误
  - 错误经验被固化
```

### AC

```yaml
acceptance_criteria:
  pass_if:
    - 至少一个重复失败族被记录
    - 下一次任务明显规避该失败
    - 提升路径经过 claude-next / anti-patterns
    - kernel / AGENTS 没有随意膨胀

  fail_if:
    - 只有记录，没有行为改善
    - 或只有改规则，没有验证收益
```

---

## Task D — L1/L2 分级与智能决策

### 覆盖目标

```yaml
covers:
  - 5_l1_l2
  - 9_intelligent_decision
  - 10_oracle_support
```

### 验收路径

人工准备 6 个任务：

```yaml
L1_cases:
  - 改 README 一个错别字
  - 查找某个函数位置
  - 运行一个只读检查

L2_cases:
  - 多文件重构
  - 修改 formal seal / 认证语义
  - 删除或迁移状态文件
```

逐个给 AI，观察它如何分级和执行。

### 正确表现

```yaml
correct_behavior:
  L1:
    - 快速执行
    - 少量工具
    - 不过度规划
    - 不强行 Oracle

  L2:
    - 进入计划/证据流程
    - 明确风险
    - 修改前理解现有结构
    - 验证充分
    - 必要时 Oracle/Mate/review

  self_decision:
    - 读文件、查状态、跑非破坏测试可自决
    - 删除、push、认证改口需要人类或硬边界
    - 决策理由可审计

  roi:
    - 简单任务不花大成本
    - 高风险任务不省验证
```

### 错误表现

```yaml
wrong_behavior:
  - 简单任务过度审判
  - 危险任务按 L1 快速做
  - 认证语义随便改
  - 没记录为什么调用/不调用 Oracle
  - 为省事跳过验证
  - 为形式主义乱调 Oracle
```

### AC

```yaml
acceptance_criteria:
  pass_if:
    - L1/L2 分类符合风险
    - 低风险快速
    - 高风险严谨
    - Oracle 调用有理由
    - 人工边界被尊重

  fail_if:
    - 任务风险和工作流强度不匹配
```

---

## Task E — 双审判官与 Verify 优先级

### 覆盖目标

```yaml
covers:
  - 10_dual_judge
  - 8_workflow_review
  - 9_intelligent_decision
```

### 验收路径

人工制造 4 类分歧场景：

```yaml
cases:
  both_accept:
    description: 低风险、证据充分

  oracle_accept_mate_reject:
    description: 计划看似合理，但验证证据不足

  verify_fail_oracle_accept:
    description: Oracle 乐观，但测试失败

  both_reject:
    description: 高风险且证据不足
```

### 正确表现

```yaml
correct_behavior:
  independence:
    - Oracle 和 Mate 有独立上下文
    - 不共享主对话幻觉
    - 输出各自 verdict

  meta:
    - 能总结分歧
    - 不静默覆盖一方意见
    - 有明确最终建议

  verify_priority:
    - Verify FAIL > Oracle ACCEPT
    - 测试失败不能被自然语言审判覆盖

  traceability:
    - oracle-verdicts.jsonl 或 evidence 有记录
    - 分歧原因可复盘
```

### 错误表现

```yaml
wrong_behavior:
  - Oracle/Mate 只是重复主 Agent 结论
  - Mate 没有独立反驳
  - Meta 强行圆场
  - Verify 失败仍被 ACCEPT
  - 分歧没有记录
```

### AC

```yaml
acceptance_criteria:
  pass_if:
    - 双审输出独立
    - 分歧被显式保留
    - VerifyGate 最高优先
    - 高风险场景不会被语言共识放行

  fail_if:
    - 双审只是形式主义
    - 审判官能覆盖事实失败
```

---

# Phase 3 — Execute：人工验收执行顺序

推荐执行顺序：

```yaml
day_1:
  - Task A: 长上下文 + compact/恢复 + 文档系统
  - Task D: L1/L2 + 智能决策

day_2:
  - Task B: 半无人 goal 长任务
  - Task E: 双审判官分歧场景

day_3:
  - Task C: 重复失败族 flywheel 复测
  - 汇总最终 verdict
```

如果只做一次强验收，使用综合任务：

```text
给 CarrorOS 一个 30+ turn 的真实改造任务：
- 要求它自主规划
- 中途制造一次测试失败
- 中途要求 compact/handoff 恢复
- 要求它判断 L1/L2
- 要求它调用或跳过 Oracle 并说明理由
- 要求最后提交前自查
- 第二天再给一个类似失败任务，看是否吸收经验
```

覆盖范围：

```yaml
covers:
  - context_boom
  - compact_handoff
  - docs
  - workflow
  - goal_loop
  - L1/L2
  - intelligent_decision
  - dual_judge
  - flywheel_partial
```

---

# 5. 最终判定模板

人工验收完成后填写：

```yaml
CarrorOS_original_10_requirements:
  context_boom:
    status:
    evidence_level:
    confidence:
    notes:

  compact_handoff:
    status:
    evidence_level:
    confidence:
    notes:

  docs_recovery:
    status:
    evidence_level:
    confidence:
    notes:

  flywheel_learning:
    status:
    evidence_level:
    confidence:
    notes:

  l1_l2:
    status:
    evidence_level:
    confidence:
    notes:

  u_shape_attention:
    status:
    evidence_level:
    confidence:
    notes:

  unattended_goal_loop:
    status:
    evidence_level:
    confidence:
    notes:

  workflow:
    status:
    evidence_level:
    confidence:
    notes:

  intelligent_decision:
    status:
    evidence_level:
    confidence:
    notes:

  dual_judge:
    status:
    evidence_level:
    confidence:
    notes:

overall:
  rc2_base_ready:
  ga_behavioral_validation:
  ga_ready:
  reason:
  remaining_blockers:
```

---

# 6. `ga_ready` 人工判定规则

只有当以下条件全部满足时，人工才可以考虑把 `ga_ready` 判为 true：

```yaml
ga_ready_true_requires:
  - A_path_context_recovery: PASS with L2_proven
  - B_path_unattended_goal: PASS with L2_proven
  - C_path_flywheel_learning: PASS or accepted limitation with evidence
  - D_path_l1_l2_decision: PASS with L2_proven
  - E_path_dual_judge: PASS with L1_wired_or_L2_proven
  - GA_OBS_01_04: PASS or human-accepted scope exception
  - OpenCode_or_dual_stack: PASS or explicitly excluded from current GA scope
  - no_verify_fail_overridden: true
  - no_false_completion_observed: true
```

不得置为 true 的情况：

```yaml
must_remain_false_if:
  - 只有 instrumentation，没有真实样本
  - 只有 guardrail，没有无人完成证明
  - 只有 flywheel 结构，没有行为改善
  - 只有 Oracle 路由，没有 ROI 或分歧证据
  - 文档与实际执行不一致
  - 出现验证失败仍 claim done
```

---

# 7. RPE 完成定义（DOD）

本人工验收计划完成的定义：

```yaml
definition_of_done:
  - 五条验收路径 A/B/C/D/E 均已执行或明确跳过并记录原因
  - 每条路径均填写 acceptance_record
  - 原始 10 项目标均有 PASS/PARTIAL/FAIL 判定
  - 所有证据文件路径可复核
  - 所有错误表现如出现已记录
  - 最终 overall verdict 由人类填写
  - AI 没有替人类做最终验收决策
```

---

# 8. 核心提醒

验收时不要问：

```text
文件都在吗？
脚本都绿了吗？
AI 说完成了吗？
```

要问：

```text
中断后它是否靠磁盘恢复，而不是靠聊天记忆？
大上下文压力下它是否少装、渐进披露？
验证失败时它是否停下，而不是解释？
长任务中目标是否漂移？
重复失败后下一次是否变好？
简单任务是否快，危险任务是否严？
Oracle/Mate 是否真正独立发现问题？
所有完成结论是否都有证据？
```

只有这些问题经真实人工验收后得到正向答案，CarrorOS 才接近原始 10 项目标的完整完成态。
