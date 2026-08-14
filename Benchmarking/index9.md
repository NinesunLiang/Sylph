---
type: benchmark-report
schema_version: carroros-governance-benchmark.v1
status: provisional-not-certified
report_index: 9
task_id: 独立评估-CarrorOS-真实-AI-治理效能执行本地无凭据黑盒-spawn-严格测-1db3c3bf
method: fresh-local-black-box-popen-loopback-plus-independent-scorecard-plus-regression
---

# CarrorOS 真实 AI 治理效能 Benchmark index9

## 1. 结论

本轮在空上下文下重新执行了本地真实 `SubAgentManager → subprocess.Popen → sub_agent_executor → loopback fixture Provider` 八场景矩阵，并运行 Goal 生命周期、SubAgent failure、execution boundary、compact isolation、task context isolation 与 aggregate 回归。

**结论：`PROVISIONAL / NOT_CERTIFIED`。**

本轮证明本地 worker 的启动、PID、成功、失败闭合、重试、超时、取消和空上下文失败边界；不证明真实外部 Provider、真实 Claude CLI coding session、process-group/worktree 隔离或 recovery continuation。评分是本报告的独立评估，不写入或替代 CarrorOS 的产品能力评分。

## 2. 评分摘要

| 维度 | 得分 | 口径 |
|---|---:|---|
| C1-C9 能力加权 | **7.20 / 10** | 756 / 105 |
| E1-E8 错误防护加权 | **6.55 / 10** | 720.5 / 110 |
| 24 项综合 proxy | **6.88 / 10** | (7.20 + 6.55) / 2 |
| 长期治理能力 | **6.57 / 10** | 7 项算术平均 |
| UX 独立 proxy | **6.43 / 10** | 7 项算术平均；不是人类 UX 研究 |

评分仅基于 fresh index9 证据、历史 index8 对照和未认证项降权；详细依据如下。

## 3. C1-C9 能力维度

| C | 指标 | 权重 | 得分 | 评估依据 |
|---|---|---:|---:|---|
| C1 | 指令清晰度 | 15 | 8 | Phase 0、ResearchGate、PlanGate 和显式 task-dir 使目标可追踪；S1/S2/S3/S4 均有结构化证据。 |
| C2 | 上下文完整度 | 15 | 7 | 空上下文明确失败为 `no instruction.md found`；任务 token/handoff 隔离有效，但恢复仍摘要化。 |
| C3 | 流程结构化 | 15 | 8 | CLARIFY→PLANNING→EXECUTING 门禁工作；本轮真实经历 PlanGate schema 修正和 VerifyGate evidence 修正。 |
| C4 | 输出规范化 | 10 | 7 | success/failure/empty/timeout/cancel 状态可区分；恢复结果仍是 summary-only，Pyright 对 task-local runner 有静态告警。 |
| C5 | 工具生命周期 | 10 | 8 | 8 场景均拉起真实 worker；PID、poll、retry generation=1、cancel child-wait 后终态均有 artifact。 |
| C6 | 知识密度 | 10 | 7 | fresh matrix、executor 证据、历史 index8 与独立 scorecard 可回溯；没有真实 Provider 证据。 |
| C7 | 关联编排 | 10 | 7 | Goal、runner、manager、worker、collector、regressions 连通；recovery 尚未真正续跑。 |
| C8 | 可维护性 | 10 | 7 | 本轮发现并修复 list-valued lock counter TypeError，focused 2 与 lifecycle 35 通过；计划/证据 schema 仍有较高门禁负担。 |
| C9 | 错误恢复 | 10 | 6 | 失败/重试/超时/取消可收敛；recovery `continuation_attempted=false`，因此不能认证完整恢复。 |

加权计算：`(8×15+7×15+8×15+7×10+8×10+7×10+7×10+7×10+6×10)/105 = 7.20`。

## 4. E1-E8 错误防护维度

| E | 指标 | 权重 | 得分 | 评估依据 |
|---|---|---:|---:|---|
| E1 | 目标漂移 | 20 | 6 | 显式 task-dir 隔离通过；collector parent identity 未完全证明。 |
| E2 | 幻觉输出 | 20 | 8 | loopback raw artifact、worker result 与独立报告分栏；未把未认证项宣称为通过。 |
| E3 | 虚假完成 | 15 | 7 | failure/empty/timeout/empty-context 不聚合为 completed；本轮 task-done TypeError 被真实暴露并修复。 |
| E4 | 惯性执行 | 12 | 7 | retry=1 真实产生 2 请求且 generation=1；未见无限重试。 |
| E5 | 症状混淆 | 10 | 7 | timeout、empty output、JSON parse failure 和 missing instruction 分别保留。 |
| E6 | 自我矛盾 | 13 | 6 | PlanGate/VerifyGate 多次暴露 schema 不一致，修复后证据可匹配；旧 runner 静态导入告警仍存在。 |
| E7 | 过度自信 | 10 | 7 | 报告保持 provisional；真实 Provider、CLI、recovery continuation 明确未认证。 |
| E8 | 上下文遗忘 | 10 | 6 | compact/session/task isolation 回归通过；recovery 仍无 resume→continue→verify 链。 |

加权计算：`(6×20+8×20+7×15+7×12+7×10+6×13+7×10+6×10)/110 = 6.55`。

## 5. 长期治理能力

| 维度 | 得分 | 评估依据 |
|---|---:|---|
| 抗衰减防线 | 7 | fresh 重跑复现 index8 主要结论，且修复了锁计数器类型边界。 |
| AI 赋能的全流程自动化 | 7 | Goal 生命周期、Popen、retry、collect 和回归链可运行；外部 Provider/recovery 未认证。 |
| 学习笔记积累 | 7 | index1-index8 历史基线、本轮 raw artifact、executor error evidence 可回流。 |
| 长期目标一致性 | 6 | task-dir 隔离有效；多重计划/证据格式导致执行摩擦。 |
| 功能标志分明 | 7 | Goal、spawn、aggregate、独立评分和未认证边界清晰。 |
| 内置安全与洞察 | 6 | 无凭据、无外网、无 git 写操作；仍缺完整 worker identity/process-group 证明。 |
| Evaluation 评测框架 | 7 | C/E scorecard、fresh/historical/unexecuted 分栏和回归证据存在。 |
| **平均** | **6.57** | 独立 proxy |

## 6. 用户体验（独立 proxy）

本组不是人类参与者研究，而是依据 CLI 行为、门禁反馈、证据负担和可预测性评估。

| 维度 | 得分 | 评估依据 |
|---|---:|---|
| 长期目标一致性 | 6 | task-dir 清晰，但完成步骤需理解多层 evidence/schema 契约。 |
| 用户心智负担减轻 | 5 | 本轮真实遇到三类计划/证据格式门禁和一次 lock counter 崩溃。 |
| 交互现代化 | 6 | Agentic Goal CLI 和 Markdown 证据具备基础，但主要仍是 CLI。 |
| 用户掌控感 | 8 | 范围、硬边界、未认证 Provider/CLI、跳过项均明确。 |
| ai 智能感 | 7 | 能拉起真实 worker、重试并保留失败结果；不夸大外部能力。 |
| 行为可预测 | 6 | spawn 终态稳定；task-done 的类型错误已修复，recovery 行为仍不完整。 |
| 人机权限分明 | 8 | 凭据、外网、远程和破坏性操作未执行。 |
| **平均** | **6.43** | 仅独立 proxy |

## 7. Fresh spawn matrix

Artifact：`.omc/tasks/20260812/独立评估-CarrorOS-真实-AI-治理效能执行本地无凭据黑盒-spawn-严格测-1db3c3bf/artifacts/spawn-matrix/run-20260812T030614Z/spawn-matrix-output.json`

| 场景 | 结果 | 证据结论 |
|---|---|---|
| success | completed | 1 loopback request，真实 worker PID，poll=0 |
| API failure | has_failures | failure 保留，未聚合 completed；fixture 返回 500 后出现 JSON parse failure |
| empty output | has_failures | `empty agent output`，未聚合 completed |
| retry | completed | 2 requests，generation=1，最终 completed |
| timeout | has_failures | `timeout` failure 保留，未聚合 completed |
| cancel | cancelled | cancel snapshot 与 child wait 后均保持 cancelled |
| empty context | failed | `no instruction.md found`，无 Provider 请求 |
| recovery | summary-only | resume 文件生成，但 `continuation_attempted=false` |

## 8. 本轮过程错误与机制修复

| 编号 | 事件 | 根因 | 处理与验证 |
|---|---|---|---|
| E9-001 | 首次 PlanGate 拒绝 | 缺少严格 `Phase` / step schema | 补齐 Phase、scope、acceptance、verify，PlanGate 通过 |
| E9-002 | VerifyGate 拒绝 | executor checklist 与 evidence 字段未完成 | 补齐 checklist、E3 evidence 和 assertion 对齐，S1/S2/S3/S4 VERIFIED |
| E9-003 | `task-done` TypeError | `_update_lock_counter` 将 list-valued `completed_tasks` 与 int 相加 | 新增 list-field regression；修复 `.claude/skills/lx-goal/scripts/lx-goal.py`，focused 2 passed、Goal lifecycle 35 passed |
| E9-004 | 静态诊断告警 | task-local runner 的动态 sys.path 与 HTTP fixture 属性未被 Pyright 推断 | 记录为质量告警；不影响运行时 matrix，未扩展范围修复 |

## 9. 认证边界与未执行项

- 未访问真实外部 Provider、真实 Claude CLI coding session、凭据、外网或远程服务。
- 未执行 git commit、push、rebase、reset、删除或其他破坏性操作。
- 未认证 process-group/worktree 隔离、真实 Provider schema、recovery continuation、跨机器行为和人类 UX 研究。
- 历史 `.omc` lock sidecar 未被删除或接管；仅通过 token 内容、task-dir、状态字段交叉判断。

## 10. 验证证据

- Fresh matrix：exit 0，8/8 场景，`findings=[recovery_summary_only]`。
- Focused lock-counter regression：2 passed，33 deselected。
- Goal lifecycle regression：35 passed。
- Cross-module governance regressions：53 passed。
- 本轮唯一代码修复：`lx-goal.py` list-valued lock field guard + `test_goal_lifecycle_regressions.py` regression。

## 11. 独立评分声明

本 index9 的分数是独立 benchmark proxy，用于评估 CarrorOS 在当前本地、无凭据测试边界内的实际治理效能；它不修改、不回写、不替代 CarrorOS 的 C/E 能力定义或产品自身评分。由于真实 Provider、真实 CLI 和 recovery continuation 未执行，报告保持 `PROVISIONAL / NOT_CERTIFIED`。

## 12. 退出阶段新增阻断

- `lx-goal.py report` 输出 `VERIFIED: 所有计划步骤已完成（6 项完成）`，且最终回归为 88 passed。
- 随后公开 `lx-goal.py done --task-dir <task_dir>` 仍报 `Invalid transition: EXECUTING -> ARCHIVING (allowed: ['VERIFYING'])`；canonical token 的 `stats.done` 仍为 `1/6`，说明 `cmd_task_done` 的 mode-file/runtime completed_tasks 与 canonical token stats 没有统一提交边界。
- 本轮不手改 token、不删除锁、不绕过 GoalMachine；因此任务锁保留，以上是未修复的退出门禁缺陷，不能将本次状态称为 ARCHIVED。
