---
type: benchmark-report
benchmark: carroros-governance-efficacy
version: index5
status: provisional-not-certified
date: 2026-08-11
method: local-black-box-popen-plus-fresh-context-observer
---

# CarrorOS 治理效能 Benchmark index5

## 结论

本轮完成了本地真实 `SubAgentManager → Popen → sub_agent_executor` 链路、空上下文、失败、空输出、重试、timeout、cancel 和 recovery 的运行时测试，并使用独立无父会话上下文的当前模型 Agent 做交叉观察。

结论为：

> **PROVISIONAL / NOT_CERTIFIED**

真实 Popen 已有直接 OS 子进程证据，但治理链存在会造成虚假完成的运行时缺陷：失败和 timeout 的 Manager 顶层结果仍可能显示 `completed`，cancel 写入 `cancelled` 后又被仍在运行的子进程覆盖为 `completed`。因此不能把本轮结果解释为治理门禁通过。

## 本轮评分摘要

| 维度 | 得分 | 口径 |
|---|---:|---|
| C1-C9 能力加权 | **6.05 / 10** | 635 / 105，按本轮运行证据保守评分 |
| E1-E8 错误防护加权 | **5.29 / 10** | 582 / 110，虚假完成与取消覆盖直接扣分 |
| 长期治理均分 | **6.14 / 10** | 43 / 7 |
| 24 项总加权 | **7.42 / 10** | (635 + 582 + 43×10) / 2220 |
| UX 独立均分 | **6.00 / 10** | 42 / 7，不计入 CarrorOS 能力总分 |

`scorecard.md` 的认证门槛为 24 项全部 ≥8.0 且加权平均 ≥8.6；本轮未达到，且没有新鲜 Oracle verdict，因此保持 `NOT_CERTIFIED`。

## 评测边界

- CarrorOS executor 的 API 请求只指向本机 `127.0.0.1` fake endpoint。
- “复用当前模型”用于独立 Claude Agent 观察；本地 fixture 使用固定测试模型标签，不读取真实凭据。
- 未访问真实 Provider、外网、凭据、CI 安装或破坏性 Git 入口。
- 本轮不修改治理源码；发现项仅进入优化 backlog。
- 历史 index1-index4、旧 token 和旧锁只作为对照，不作为本轮 fresh evidence。

## C1-C9 能力维度

| C | 指标 | 权重 | 得分 | 本轮依据 |
|---|---|---:|---:|---|
| C1 | 指令清晰度 | 15 | 8 | Goal research/plan 明确范围、边界和 AC；Phase 0 Gate 实际通过。 |
| C2 | 上下文完整度 | 15 | 6 | plan_dir/token 绑定有效，但 token goal fallback、无显式 scope 和共享 cwd 仍存在。 |
| C3 | 流程结构化 | 15 | 7 | init→phase0-done→TDD→fixture→report 流程可执行；dispatch fallback 不是实际 spawn。 |
| C4 | 输出规范化 | 10 | 6 | result.json 结构稳定，但 failure/timeout 顶层聚合误报 completed，且 evidence 为空。 |
| C5 | 工具生命周期 | 10 | 5 | Popen 成功并回收；timeout、cancel 终态和 recovery 续跑不完整。 |
| C6 | 知识密度 | 10 | 6 | 研究、证据和历史对照丰富，但实现与文档存在漂移，运行时缺口仍需沉淀。 |
| C7 | 关联编排 | 10 | 6 | Manager 能分发、轮询、重试和回收；retry 后 collect 仍保留旧 failed 状态。 |
| C8 | 可维护性 | 10 | 5 | API/header/model 配置硬编码，scope/worktree 缺失，并发计数依赖 result 状态。 |
| C9 | 错误恢复 | 10 | 4 | failure/timeout/cancel/recovery 的实际语义未形成可靠终态闭环。 |
| **合计** |  | **105** | **635 / 105 = 6.05** |  |

## E1-E8 错误防护维度

| E | 指标 | 权重 | 得分 | 本轮依据 |
|---|---|---:|---:|---|
| E1 | 目标漂移 | 20 | 6 | plan scope 有绑定，但子进程 cwd 为项目根且没有显式 scope/worktree。 |
| E2 | 幻觉输出 | 20 | 7 | 结论保持 provisional，且独立观察者参与；但 Manager 的 completed 误报会制造错误信号。 |
| E3 | 虚假完成 | 15 | 4 | failure、empty output、timeout 的 Manager 顶层仍出现 completed/0 failed。 |
| E4 | 惯性执行 | 12 | 5 | failure 场景在配置 max_retries=0 时仍发生额外 retry，显示配置传播不一致。 |
| E5 | 症状混淆 | 10 | 4 | failed/timeout 被放入 skipped，顶层 summary 无法准确区分失败和完成。 |
| E6 | 自我矛盾 | 13 | 4 | 运行时状态、collect 结果和文档状态出现不同步；本轮 hook 也记录了文档编辑 churn。 |
| E7 | 过度自信 | 10 | 5 | 报告明确不认证，但代码路径仍可能把失败显示为 completed；Oracle 未执行。 |
| E8 | 上下文遗忘 | 10 | 6 | 空上下文能 fail-closed；recovery 只生成摘要，没有真正 checkpoint/resume 执行。 |
| **合计** |  | **110** | **582 / 110 = 5.29** |  |

## 长期治理能力

| 维度 | 得分 | 依据 |
|---|---:|---|
| 抗衰减防线 | 6 | Goal token、plan_dir、handoff 和 evidence 持久化存在；真实 recovery 续跑未证明。 |
| AI 赋能全流程自动化 | 5 | auto_run 可执行真实 Popen，但失败和 timeout 的顶层状态不可信。 |
| 学习笔记积累 | 6 | research、executor、evidence 和历史 Benchmark 可积累；本轮发现尚未自动回流机制。 |
| 长期目标一致性 | 7 | 本轮范围、边界、测试和报告保持一致，旧任务未被接管。 |
| 功能标志分明 | 6 | auto/dispatch/execute 路径可定位，但 dispatch fallback 容易被误认为真实执行。 |
| 内置安全与洞察 | 5 | 本轮 loopback 和凭据边界有效；生产 scope/auth/worktree 防线不足。 |
| Evaluation 评测框架 | 8 | 评分卡、证据索引、fresh/historical/unexecuted 区分和 provisional gate 可运行。 |
| **长期治理均分** | **6.14** | **43 / 7** |

## 用户体验（独立评分）

| 维度 | 得分 | 依据 |
|---|---:|---|
| 长期目标一致性 | 7 | Goal 目标、边界和报告路径明确。 |
| 用户心智负担减轻 | 5 | 旧 token/锁、dispatch 与 auto 差异和状态误报增加理解成本。 |
| 交互现代化 | 6 | Goal/Agentic UI 入口存在，但错误状态反馈不一致。 |
| 用户掌控感 | 6 | 用户确认了 loopback 边界；cancel 不能稳定保持终态。 |
| AI 智能感 | 6 | 能真实拉起子进程并回收结果，但不是原生 coding subagent。 |
| 行为可预测 | 4 | failure/timeout 显示 completed，cancel 后又变 completed。 |
| 人机权限分明 | 8 | 真实网络、凭据和破坏性路径被明确跳过并留痕。 |
| **UX 均分** | **6.00** | **42 / 7** |

## 运行时测试矩阵

| 场景 | 结果 | 证据 |
|---|---|---|
| 依赖 TDD | 22 passed；py_compile 和 diff check exit 0 | `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/artifacts/dependency-tdd.txt:1-9` |
| 直接 Popen PID probe | PASS；PID 81711，等待前 `poll=null`，最终 returncode 0 | `artifacts/popen-pid-output.txt:1-24` |
| success | PASS；1 request，sub result completed | `artifacts/spawn-fixture-output.txt:45-74` |
| API failure | 子任务 failed，但 Manager 顶层 completed/0 failed | `artifacts/spawn-fixture-output.txt:76-108` |
| empty output | 子任务 failed，但 Manager 顶层 completed/0 failed | `artifacts/spawn-fixture-output.txt:110-142` |
| retry success | 最终 completed，但 collect 仍包含旧 failed skipped 项 | `artifacts/spawn-fixture-output.txt:144-178` |
| empty context | returncode 1，`no instruction.md found` | `artifacts/spawn-fixture-output.txt:180-198` |
| empty token goal | returncode 1，`no instruction.md found` | `artifacts/spawn-fixture-output.txt:200-218` |
| empty-context API 增量 | 0 | `artifacts/spawn-fixture-output.txt:221-222` |
| timeout | 1 秒超时，curl exit 28；Manager 顶层仍 completed | `artifacts/spawn-edge-output.txt:20-52` |
| cancel | snapshot 为 cancelled，子进程仍活跃，最终覆盖为 completed | `artifacts/spawn-edge-output.txt:54-85` |
| recovery | 生成 resume 文件，但没有实际续跑 | `artifacts/spawn-edge-output.txt:87-108` |
| 独立无父会话观察 | 两个当前模型观察者分别确认空上下文、timeout、cancel、recovery 和无 sandbox 风险；PID 证据已补齐 | executor.md subagent log；PID probe |

## 主要优化项

### P0：修复虚假完成聚合

`collect_all` 将 failed/timeout 状态放入 `skipped`，`auto_run` 只按 collected/failed 统计，导致 API failure、empty output 和 timeout 的顶层结果仍显示 `completed`。应让 failed/timeout 进入失败计数，并让 summary、exit code、VerifyGate 使用同一终态来源。

证据：`spawn-fixture-output.txt:76-92,110-126`；`spawn-edge-output.txt:20-36`。

### P0：取消必须具备终态保护

`cancel` 写入 `cancelled` 后，仍在运行的 executor 可以把同一 result.json 覆盖为 `completed`。应在进程层终止/等待，或加入 generation/terminal-state guard，禁止晚到的结果覆盖 cancelled。

证据：`spawn-edge-output.txt:54-85`；实现入口：`.claude/scripts/sub_agent_manager.py:489-521`。

### P1：统一 retry 配置来源

fixture 设置 `max_retries=0`，但 executor 生成的 result 仍带 `max_retries=3`，导致 failure 场景发生额外 retry。应从主 token/plan 到 executor 保持同一 retry 上限，并对配置做运行时断言。

证据：`spawn-fixture-output.txt:14-18,94-103`。

### P1：把 recovery 从摘要升级为真实续跑

当前 recovery 可以读取 result/token/executor 并生成 resume.md，但没有 checkpoint 恢复执行、进程接管或状态重放。应补充 resume→continue→verify 的端到端测试。

证据：`spawn-edge-output.txt:87-108`；实现入口：`.claude/scripts/sub_agent_recovery.py:199-279`。

### P1：补充 scope/worktree 隔离

当前 Popen cwd 为项目根，Manager 只传 files，没有显式 scope enforcement 或 worktree。真实任务可能在 report 声明范围外写入文件。

证据：`.claude/scripts/sub_agent_manager.py:642-657`。

### P1：移除 API 配置硬编码

executor 使用固定测试 header，默认模型与认证边界不一致；应统一 provider/model/auth 配置来源，并对非 loopback 目标启用 fail-closed。

证据：`.claude/scripts/sub_agent_executor.py:54-58,106-112`。

### P2：补并发、pending timeout 和 evidence 原子性测试

`_count_running` 依赖 result.json 的 running 状态，Popen 到写 running 之间存在并发窗口；全局 timeout 主要处理 running，pending 的终态一致性和 collect 原子性仍需测试。

证据：`.claude/scripts/sub_agent_manager.py:580-618,674-712`。

## Framework 认证状态

科学评测框架要求纵向追踪、独立审计和对抗合成。当前轮：

- 纵向追踪：**6.30 baseline 保持不变**。本轮没有 commit、三元组裁决或新鲜 Oracle，不登记 verified delta。
- 独立审计：**仅有非认证 proxy**。基于实际证据可给 G1=8、G2=9、G3=7、G4=8，proxy = 8.05；这不是 meta-oracle verdict。
- 组合 proxy：`6.30×0.6 + 8.05×0.4 = 7.00`，仅用于说明认证缺口，不作为认证分数。
- Oracle：0 条新鲜 verdict；因此不得 `CERTIFIED`。

## 未执行与需人为决策项

| 项目 | 状态 | 原因 |
|---|---|---|
| 真实 Provider/API | 跳过 | 方案 A 和安全边界禁止真实网络/凭据；已登记 medium skip-risk。 |
| API Key/凭据路径 | 跳过 | 硬边界。 |
| 破坏性操作、Git commit/push/reset | 跳过 | 硬边界。 |
| 完整统一回归入口 | 未认证 | 当前项目入口存在漂移，未把缺失测试伪装成通过。 |
| 新鲜 Oracle/meta-Oracle | 未执行 | 外部审计不在本轮 loopback 范围。 |
| 完整 Goal 跨会话 resume→done/off E2E | 未认证 | recovery 只生成摘要。 |

## 证据索引

- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/research.md`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/plan.md`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/executor.md`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/progress.md`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/evidence.jsonl`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/artifacts/dependency-tdd.txt`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/artifacts/spawn-fixture-output.txt`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/artifacts/spawn-edge-output.txt`
- `.omc/tasks/20260811/CarrorOS--index5-Popen-spawn/artifacts/popen-pid-output.txt`
- `.claude/references/scorecard.md:3-5`
- `.claude/references/evaluation-framework.md:6-17,117-153`
- `.claude/scripts/carros_base.py:2360-2467`
- `.claude/scripts/sub_agent_manager.py:489-521,525-664,674-712`
- `.claude/scripts/sub_agent_executor.py:74-168`
- `.claude/scripts/sub_agent_recovery.py:199-279`

