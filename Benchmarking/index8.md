---
type: benchmark-report
schema_version: carroros-governance-benchmark.v1
status: provisional-not-certified
report_index: 8
task_id: carroros-governance-index8-final-20260812
method: fresh-local-black-box-popen-loopback-plus-independent-observers-plus-targeted-regression
---

# CarrorOS 真实 AI 治理效能 Benchmark index8

## 1. 结论

本轮完成了本地真实 `SubAgentManager → subprocess.Popen → sub_agent_executor → loopback fake Provider` 八场景矩阵、三份独立无父会话观察、Goal 生命周期与 task isolation 回归、SubAgent failure matrix 和 aggregate readiness。

**最终状态：`PROVISIONAL / NOT_CERTIFIED`。**

本轮没有访问真实外部 Provider、凭据、外网、真实 Claude CLI coding session 或破坏性 Git 入口。spawn 证据证明本地 worker 生命周期和失败终态，但不证明生产 Provider、worktree/process-group 隔离或真正 recovery continuation。

## 2. 评分摘要

| 维度 | 得分 | 口径 |
|---|---:|---|
| C1-C9 能力加权 | **7.10 / 10** | 745 / 105 |
| E1-E8 错误防护加权 | **6.45 / 10** | 709 / 110 |
| 24 项综合 proxy | **6.78 / 10** | (7.10 + 6.45) / 2 |
| 长期治理能力 | **6.43 / 10** | 7 项算术平均 |
| UX 独立 proxy | **6.29 / 10** | 7 项算术平均，不是人类 UX 研究 |

评分明细：`.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/scorecard-index8.md`。
Aggregate：`.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/eval-report-index8.md`。

## 3. C1-C9 能力维度

| C | 指标 | 权重 | 得分 | 依据 |
|---|---|---:|---:|---|
| C1 | 指令清晰度 | 15 | 8 | research/plan/ResearchGate/PlanGate 与 task-dir 契约可追踪 |
| C2 | 上下文完整度 | 15 | 7 | explicit task token 与 session isolation 通过；recovery 仍摘要化 |
| C3 | 流程结构化 | 15 | 8 | CLARIFY→PLANNING→EXECUTING 门禁与 34 项 lifecycle 回归通过 |
| C4 | 输出规范化 | 10 | 7 | failure/empty/timeout/cancel 终态统一；报告/旧入口仍有漂移 |
| C5 | 工具生命周期 | 10 | 7 | 真实 PID、retry、cancel、late terminal guard 有证据 |
| C6 | 知识密度 | 10 | 7 | fresh matrix、observer、research、scorecard 和历史对照齐全 |
| C7 | 关联编排 | 10 | 7 | manager/executor/retry/collect/aggregate 连通；recovery 未续跑 |
| C8 | 可维护性 | 10 | 6 | 测试契约曾与 task-token-only 迁移漂移，stale hook 增加维护成本 |
| C9 | 错误恢复 | 10 | 6 | failure/retry/timeout/cancel 可收敛；recovery `continuation_attempted=false` |

## 4. E1-E8 错误防护维度

| E | 指标 | 权重 | 得分 | 依据 |
|---|---|---:|---:|---|
| E1 | 目标漂移 | 20 | 6 | task-dir isolation 通过；collector parent identity 尚未完整证明 |
| E2 | 幻觉输出 | 20 | 8 | 独立 observer 与 fresh artifact 分栏；报告保持 provisional |
| E3 | 虚假完成 | 15 | 6 | worker failure 不再 completed；off/report 与 collector 仍有残余边界 |
| E4 | 惯性执行 | 12 | 7 | max_retries=1 产生第二请求，generation=1 |
| E5 | 症状混淆 | 10 | 7 | timeout、empty、API parse failure 原因保留在 result |
| E6 | 自我矛盾 | 13 | 5 | 状态快照覆盖、测试契约漂移和文档编辑 churn 均曾真实发生 |
| E7 | 过度自信 | 10 | 6 | Oracle 缺失、回归入口 drift、Goal E2E 缺失时 aggregate 保持未认证 |
| E8 | 上下文遗忘 | 10 | 6 | compact/task isolation 通过；recovery 仍没有 resume→continue→verify |

## 5. 长期治理能力

| 维度 | 得分 | 依据 |
|---|---:|---|
| 抗衰减防线 | 6 | task token、handoff、compact isolation 存在；旧入口与 hook 状态仍会漂移 |
| AI 赋能的全流程自动化 | 6 | Popen、retry、collect、aggregate 可运行；Provider/recovery 未认证 |
| 学习笔记积累 | 7 | history benchmark、research、evidence、observer artifact 可回流 |
| 长期目标一致性 | 6 | 新 task 可隔离旧快照；跨任务迁移仍增加成本 |
| 功能标志分明 | 7 | Goal、Stepwise、aggregate、document gate 边界可定位 |
| 内置安全与洞察 | 6 | hard boundary、allowed-state gate、conflict aggregate 有效；collector identity 未完备 |
| Evaluation 评测框架 | 7 | C/E scorecard、readiness、fresh/historical/unexecuted 分栏存在 |
| **平均** | **6.43** |  |

## 6. 用户体验（独立 proxy）

本组不是人类参与者研究；它基于独立 observer、CLI 行为和证据负担的 proxy。

| 维度 | 得分 | 依据 |
|---|---:|---|
| 长期目标一致性 | 6 | explicit task-dir 清晰，但 stale task 迁移造成中断 |
| 用户心智负担减轻 | 5 | 多层 Gate/evidence/旧入口漂移仍增加负担 |
| 交互现代化 | 6 | Agentic/Goal CLI 与结构化报告具备基础，仍主要是 CLI/Markdown |
| 用户掌控感 | 7 | skip-risk、未认证项、硬边界和新 task 选择均可见 |
| ai 智能感 | 7 | 能真实拉起 worker、重试并保留失败证据；非真实 Provider |
| 行为可预测 | 5 | 本轮暴露 stale terminal-inertia、state snapshot 和 parser 误读 |
| 人机权限分明 | 8 | 凭据、外网、破坏性操作明确未执行 |
| **平均** | **6.29** | 仅 proxy |

## 7. Fresh spawn matrix

Fresh source artifact：`.omc/tasks/20260811/独立评估-CarrorOS-真实-AI-治理效能执行本地真实-Popenworker-a2fcd8aa/artifacts/spawn-matrix/run-20260811T183227Z/spawn-matrix-output.json`；新 Goal task 复制为 `artifacts/spawn-matrix-output-index8.json`，未修改内容。

| 场景 | 结果 | 证据结论 |
|---|---|---|
| success | completed | 1 loopback request，真实 worker PID |
| API failure | has_failures | worker failure 保留，未聚合 completed |
| empty output | has_failures | empty output 转 failed |
| retry | completed | 2 requests，generation=1，最终完成 |
| timeout | has_failures | timeout 原因保留，未聚合 completed |
| cancel | cancelled | cancel snapshot 与 child wait 后均保持 cancelled |
| empty context | failed | `no instruction.md found`，无 Provider 请求 |
| recovery | summary-only | resume 文件生成，但 `continuation_attempted=false` |

独立观察摘要：`.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/independent-observations.md`。

## 8. 本轮机制修复

1. Goal CLI 增加显式 `--task-dir` 绑定，避免无上下文扫描其他任务。
2. `phase0-done` / `plan-done` 在 GoalMachine 转换后重新读取 canonical token，避免旧快照把新状态覆盖回 CLARIFY/PLANNING。
3. Goal document gate 实际校验 `allowed_states`，阻止 PLANNING 状态 collect 或 executor write。
4. `cmd_set` 拒绝任意 token 字段改写，生命周期状态只由专用命令和 GoalMachine 负责。
5. `eval-aggregate` 对 fresh Oracle 的 FAIL/BLOCKED 与 PASS 冲突 fail-closed。
6. 生命周期测试迁移到 task-token-only 契约；修复日期硬编码和 `lib` 模块缓存造成的测试漂移。

## 9. 过程错误与处理

| 编号 | 事件 | 处理/影响 |
|---|---|---|
| E8-001 | 中间版本 `MODE_FILE/AUTONOMOUS_SIGNAL=None` 导致 assert-plan-dir AttributeError | 红测锁定；当前路径改为显式 task-dir，不恢复旧 sidecar |
| E8-002 | CLI 未绑定 `--task-dir` | 增加绑定器，green |
| E8-003 | ResearchGate 拒绝编号依赖树 | 改为 bullet，green |
| E8-004 | phase0/plan 状态被旧快照覆盖 | 红绿回归并修复 canonical reread |
| E8-005 | aggregate parser 从表头读出 105/110 | 增加明确 summary 行后重跑，7.10/6.45 正确解析 |
| E8-006 | stale terminal-inertia 将旧 index7 视为当前终端 | 未绕过；用户裁决新建 `carroros-governance-index8-final-20260812`，旧 task 保留快照 |
| E8-007 | 长脚本 Write 超过 8KB | 改用已读历史 runner 复制到 task-local，再重跑 fresh matrix |
| E8-008 | task 文档频繁 Edit 触发 E6 CONTENT_FLIP/EDIT_REPEAT | 作为治理可维护性和 UX 负担纳入评分 |

## 10. 未认证项与下一步

- fresh Oracle/meta-Oracle verdict：未执行；aggregate 明确 `oracle.missing`。
- canonical `scripts/run-regression.sh`：入口 drift 且含状态移动/删除路径，未执行。
- 真实外部 Provider、凭据、外网、CI 安装和真实 Claude CLI session：按用户边界跳过。
- recovery 仍未实现真实 resume→continue→verify。
- worker process-group、worktree/scope、crash stderr/returncode 和非 loopback fail-closed 未完成生产级证明。
- `cmd_off` 已要求 active Goal 先进入 VERIFYING，但 unresolved high-risk/blocked-human 仍需在 close path 机械阻断。
- collector 现在拒绝未允许的 Goal state，但 parent token/step/generation identity 仍需更完整校验。
- aggregate readiness 仍提示 regression entrypoint drift 与 Goal E2E 缺失。

本轮因此不满足 24 项全部 ≥8 或加权 ≥8.6 的认证门槛，不能标记 CERTIFIED。

## 11. Evidence index

- `.omc/tasks/20260812/carroros-governance-index8-final-20260812/research.md`
- `.omc/tasks/20260812/carroros-governance-index8-final-20260812/plan.md`
- `.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/scorecard-index8.md`
- `.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/eval-report-index8.md`
- `.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/eval-report-index8.readiness.json`
- `.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/spawn-matrix-output-index8.json`
- `.omc/tasks/20260812/carroros-governance-index8-final-20260812/artifacts/independent-observations.md`
- `.claude/skills/lx-goal/scripts/test_goal_lifecycle_regressions.py` — 34 passed
- `.claude/skills/lx-goal/scripts/test_goal_task_context_isolation.py` — included in 19 isolation passed
- `.claude/scripts/test_task_token_isolation.py` — included in 19 isolation passed
- `.claude/scripts/test_compact_session_isolation.py` — included in 19 isolation passed
- `.claude/scripts/test_sub_agent_failure_matrix.py` — 16 passed
- `.claude/scripts/test_eval_aggregate.py` — 6 passed
