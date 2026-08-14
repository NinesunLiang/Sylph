---
type: benchmark-report
benchmark: carroros-governance-efficacy
version: index6
status: provisional-not-certified
date: 2026-08-11
evaluated_head: 083dfce86e29c9c05515264efab667a17da940cd
method: fresh-local-black-box-popen-plus-targeted-regression-plus-independent-context-audit
---

# CarrorOS 治理效能 Benchmark index6

## 结论

本轮完成当前工作树上的本地真实 `SubAgentManager → Popen → sub_agent_executor` 空上下文矩阵、机制红绿修复、48 项安全 targeted regression、readiness 聚合和两份独立 fresh-context 审查。

> **PROVISIONAL / NOT_CERTIFIED**

真实证据确认：failure、empty output、timeout 和 cancel 不再被顶层聚合为 completed；plan/token 步骤总数、占位符边界、retry 配置写回、active-step lint 计数和基础认证阈值门禁得到修复。但 retry=1 仍未产生第二次请求，timeout 原因会被 retry-cap 路径压成 failed，recovery 只有摘要文件，scope/worktree 与 process-group 隔离未证明，canonical full regression、fresh Oracle、真实 recovery E2E 和独立 UX 研究均未执行。

## 评分摘要

### 独立 fresh-context 证据评分

| 维度 | 得分 | 口径 |
|---|---:|---|
| C1-C9 能力加权 | **7.10 / 10** | 745 / 105 |
| E1-E8 错误防护加权 | **6.95 / 10** | 765 / 110 |
| 长期治理均分 | **6.29 / 10** | 44 / 7 |
| UX 均分 | **6.43 / 10** | 45 / 7；fresh model proxy，不是人类 UX 研究 |
| 24 项总加权 | **未形成 fresh 总分** | 当前聚合器只读取三项 aggregate，历史 8.65 不作为本轮证据 |

### 对抗审查下界

| 维度 | 得分 | 说明 |
|---|---:|---|
| C1-C9 | **4.95 / 10** | 对 retry、recovery、scope、状态矛盾和未完成交付采用严格口径 |
| E1-E8 | **4.53 / 10** | 对无条件矩阵 PASS、timeout 症状混淆和认证契约缺口扣分 |
| 长期治理 | **3.86 / 10** | full regression、recovery、Oracle、学习回流未闭环 |
| UX | **4.29 / 10 proxy** | 无独立 UX transcript/rubric artifact |

评分依据：`artifacts/s4-independent-audit.md`、`artifacts/s4-adversarial-audit.md`、`.claude/references/scorecard.md:3-5,224-234`。

## C1-C9 能力维度

| C | 指标 | 权重 | fresh | 对抗 | 依据摘要 |
|---|---|---:|---:|---:|---|
| C1 | 指令清晰度 | 15 | 8 | 7 | research/plan 明确范围、边界、依赖和 AC |
| C2 | 上下文完整度 | 15 | 7 | 4 | token-plan 对账已修复；handoff/recovery 仍漂移 |
| C3 | 流程结构化 | 15 | 8 | 5 | S1-S5 可推进；canonical full regression 未闭环 |
| C4 | 输出规范化 | 10 | 7 | 5 | failure/cancel 一致；timeout 被重新分类 |
| C5 | 工具生命周期 | 10 | 7 | 5 | Popen/终态保护有效；retry/recovery 未闭环 |
| C6 | 知识密度 | 10 | 7 | 5 | research、red/green、artifact 充分；自动回流未证明 |
| C7 | 关联编排 | 10 | 7 | 4 | 分发/poll/collect 连通；retry=1 只请求一次 |
| C8 | 可维护性 | 10 | 6 | 4 | 锁结果适配器改善；root cwd/header/回归漂移仍在 |
| C9 | 错误恢复 | 10 | 6 | 5 | late-write guard 有效；resume 不续跑 |
| **合计** |  | **105** | **745 / 105 = 7.10** | **520 / 105 = 4.95** |  |

## E1-E8 错误防护维度

| E | 指标 | 权重 | fresh | 对抗 | 依据摘要 |
|---|---|---:|---:|---:|---|
| E1 | 目标漂移 | 20 | 6 | 3 | 无机械 scope/worktree |
| E2 | 幻觉输出 | 20 | 8 | 6 | readiness 明确 provisional；未覆盖每个维度 |
| E3 | 虚假完成 | 15 | 8 | 8 | failure/empty/cancel 不再 completed；矩阵 PASS 仍误导 |
| E4 | 惯性执行 | 12 | 7 | 3 | retry limit 传播；retry=1 off-by-one |
| E5 | 症状混淆 | 10 | 6 | 4 | timeout 最终表现为 max retries failed |
| E6 | 自我矛盾 | 13 | 7 | 4 | token-plan 对账修复；handoff 投影仍漂移 |
| E7 | 过度自信 | 10 | 7 | 4 | 无 Oracle 不认证；尾部 PASS 与失败 case 矛盾 |
| E8 | 上下文遗忘 | 10 | 6 | 3 | recovery 明确 continuation_attempted=false |
| **合计** |  | **110** | **765 / 110 = 6.95** | **498 / 110 = 4.53** |  |

## 长期治理能力

| 维度 | fresh | 对抗 |
|---|---:|---:|
| 抗衰减防线 | 6 | 4 |
| AI 赋能全流程自动化 | 6 | 4 |
| 学习笔记积累 | 7 | 3 |
| 长期目标一致性 | 7 | 5 |
| 功能标志分明 | 6 | 4 |
| 内置安全与洞察 | 5 | 3 |
| Evaluation 评测框架 | 7 | 4 |
| **均分** | **44 / 7 = 6.29** | **27 / 7 = 3.86** |

## 用户体验（独立维度）

本轮只有 fresh model observer proxy，没有人类参与者、固定 UX transcript 或独立 rubric artifact；不进入 CarrorOS 认证总分。

| 维度 | fresh proxy | 对抗 proxy |
|---|---:|---:|
| 长期目标一致性 | 7 | 5 |
| 用户心智负担减轻 | 5 | 3 |
| 交互现代化 | 6 | 4 |
| 用户掌控感 | 7 | 4 |
| ai 智能感 | 6 | 4 |
| 行为可预测 | 6 | 3 |
| 人机权限分明 | 8 | 7 |
| **均分** | **45 / 7 = 6.43** | **30 / 7 = 4.29** |

## Fresh 运行时矩阵

| 场景 | fresh 结果 | 结论 |
|---|---|---|
| success | manager/worker completed，实际 PID/请求 | PASS |
| API failure | manager has_failures，failed=1 | false-completion aggregation fixed |
| empty output | manager has_failures，failed=1 | bounded failure |
| retry | max_retries=1，requests=1，max retries exceeded | **FAIL：未发生第二请求** |
| timeout | timeout 被记录，最终可能变为 failed/max retries | **FAIL：原因被压扁** |
| cancel | cancelled snapshot 与 child 后状态保持 cancelled | overwrite fixed；process group 未充分证明 |
| empty context | no instruction.md found，API delta=0 | fail-closed；不等于 session isolation |
| recovery | resume.md 存在，continuation_attempted=false | summary-only |

证据：`artifacts/spawn-matrix-output.txt`、`artifacts/s3-spawn-after-fixes.txt`、`artifacts/s4-regression-after-lint.txt`、`artifacts/s4-eval-readiness-after-fixes.txt`。

## 本轮机制修复

1. `step_contracts.complete_step_atomic()` 以 plan step 数重建 `stats.total`，修复多步计划提前 VERIFYING。
2. `goal_contracts.is_placeholder()` 对英文/符号 marker 使用边界匹配，修复嵌入式 `n/a` 误报。
3. `sub_agent_executor` 保留 result/token 的 `max_retries`，移除终态写入硬编码 3。
4. `eval-aggregate` 增加 8.6 group threshold 和 fresh PASS 要求；仍未达到 24 项逐项认证契约。
5. `omc_lint` 计入 `[a]/[A]` active steps，修复 token/plan total 假 mismatch。
6. lifecycle gate 允许 VERIFYING 中的幂等 tick，修复早期状态错入 VERIFYING 后无法完成后续多步验证。

主回归最终为 48 passed、5 compile targets passed。

## 过程错误与机制边界

| 编号 | 事件 | 处理 |
|---|---|---|
| E-P0-001 | assert-plan-dir 路径大小写差异 | 验证为同一目录，记录 portability observation |
| E-P0-002 | research 精确替换失败 | 停止重复，改用 Read 后原子 Write |
| E-P0-003 | 文档高频编辑触发 E6 CONTENT_FLIP/EDIT_REPEAT | 记录 claim-audit，后续改用原子写和 artifact |
| E-P0-004 | root run-regression 会 stash/remove 活动状态并含 rm -rf | medium skip-risk；未执行 |
| E-P0-005 | ResearchGate 把正文嵌入式 n/a 判为 placeholder | 红绿测试并修正边界匹配 |
| E-P0-006 | L2 PlanGate 要求 `## Phase N` | 补齐 Phase 结构并通过 |
| E-S1-001 | 依赖 runner 根目录索引错误 | 保存失败 artifact，修正后回归通过 |
| E-S1-002 | VerifyGate 忽略 EV-S1-TDD 且 command 要求 E3/精确 source | 修正主 EV block 契约 |
| E-S3-001 | token total=1 导致 Goal 误入 VERIFYING | plan 对账修复 + sequencing repair |
| E-S4-001 | tick 在 VERIFYING 被 gate 阻断 | 允许 VERIFYING 中幂等 tick，S4 复验通过 |

完整 evidence ledger：`.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8/executor.md`。

## 主要未认证项与优化 backlog

### P0

- 定义 `max_retries` 是额外重试次数还是总尝试数；用 0/1/2、failure-then-success、timeout 组合测试锁定契约。
- 保留 timeout 终态及根因，不让 retry-cap 覆盖原始症状。
- 为 `eval-aggregate` 增加 item-level 24 维 score manifest、freshness/task/commit/hash 绑定和算术校验。
- 在安全隔离副本中重建 canonical regression manifest，逐套记录 exit code；根目录入口继续保持 skip-risk。
- 实现真正 resume → continue → verify → done/off，并统一 manager/recovery token schema。

### P1

- 强制 task scope、isolated cwd/worktree、non-loopback fail-closed 和 process-group cancellation。
- 增加跨 session/邻居 task isolation 测试，不把 missing instruction 当成完整隔离证明。
- 增加固定 UX 场景、rubric、observer transcript 和独立性声明；proxy 不替代人类 UX 结论。
- 消除 handoff、token、plan、executor 状态漂移，并提供 Goal recovery 状态重建 API。

## 认证裁决

不得 CERTIFIED 的条件：fresh Oracle PASS 与 task/commit/evidence 绑定；canonical regression 或安全隔离等价套件逐套通过；24 项逐项最低分与算术机械一致；recovery E2E 真实续跑；UX 结果有明确 proxy/独立研究标签；所有未执行路径和 medium+ skip-risk 保留。

本轮仍为 **PROVISIONAL / NOT_CERTIFIED**。

## Concurrent working-tree note

评测期间检测到另一并发会话/linter 对 lifecycle 文件产生未提交修改，包括 `goal_state_machine.py`、`lx-goal.py`、`pre_action_gate.py`、Goal skill 文档和 `session-handoff.md`。本报告不回滚这些变更，也不把它们全部归因于本轮；fresh 结果代表当前工作树快照，故认证状态保持 provisional。
