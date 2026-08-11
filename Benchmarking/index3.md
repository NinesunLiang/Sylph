---
type: benchmark-report
benchmark: carroros-governance-efficacy
version: index3
status: provisional-not-certified
date: 2026-08-11
---

# CarrorOS 治理效能 Benchmark index3

## 结论

本轮针对上一轮暴露的 Goal 执行错误完成 TDD 修复，并重新执行本地评测。结论仍为：

> **PROVISIONAL / NOT_CERTIFIED**

原因：当前聚合报告的 Oracle 记录为 0 条，且完整网络 Oracle、凭据路径、统一全量回归和生产 SubAgent worker 均未执行。历史 scorecard 分数仅作为对照，不升级为认证结果。

## 本轮修复

### 1. Goal VerifyGate token 绑定

`lx-goal.py` 的 `_verify_goal_step()` 现在从当前 `plan_dir` 派生并显式传递：

- `CARROROS_TOKEN_PATH`
- `CARROROS_TASK_ID`
- `CARROROS_TASK_DIR`

这样 `tick`/`verify` 不再依赖全仓 mtime token 探测，也不会因其他任务 token 存在而输出 `No active task`。

### 2. PlanGate acceptance 字段

`plan_builder.py` 生成的每个 step 现在包含：

- `status`
- `depends_on`
- `scope`
- `acceptance`
- `verify`

避免新建 Goal 在 `phase0-done` 时因 acceptance 缺失被 PlanGate 阻断。

### 3. task-done 幂等收口

当 VerifyGate 已将最后一步标记为 completed、plan 中没有 current step 时，`task-done` 现在会确认 plan 已全部完成后继续记录完成，而不是错误返回“当前 goal 没有 current_step”。未完成 plan 仍 fail-closed。

### 4. TDD 回归覆盖

新增/更新：

```text
.claude/skills/lx-goal/scripts/test_goal_lifecycle_regressions.py
```

覆盖：

- VerifyGate 显式 token/task context；
- Plan acceptance/scope/verify 字段；
- Research dependency tree bullet；
- 已验证 plan 的 task-done 幂等收口。

## 修复后评分

以下为基于本轮实际局部测试、当前源码与明确未认证边界的 provisional 评分，不是 Oracle 认证分数。

### 能力维度 C1-C9

| 指标 | 权重 | 得分 | 本轮依据 |
|---|---:|---:|---|
| C1 指令清晰度 | 15 | 9 | Phase 0 ResearchGate/PlanGate 实际通过 |
| C2 上下文完整度 | 15 | 8 | Goal plan_dir/token 显式绑定；跨会话未完整重放 |
| C3 流程结构化 | 15 | 9 | Research→Plan→Verify→task-done 链路修复并验证 |
| C4 输出规范化 | 10 | 8 | 聚合器 Certification 字段与 Benchmark schema 已统一 |
| C5 工具生命周期 | 10 | 8 | VerifyGate 后 task-done 幂等收口通过；done/off 全链路未重放 |
| C6 知识密度 | 10 | 6 | 文档丰富，但行为证据覆盖仍有限 |
| C7 关联编排 | 10 | 8 | Goal 显式传递 token context；本地 spawn fixture 通过 |
| C8 可维护性 | 10 | 7 | 12 项局部测试通过；全量入口仍存在漂移 |
| C9 错误恢复 | 10 | 8 | `No active task` 根因修复；完整 recovery matrix 未认证 |
| **C1-C9 加权** | **105** | **8.00** | **840/105** |

### 错误防护 E1-E8

| 指标 | 权重 | 得分 | 本轮依据 |
|---|---:|---:|---|
| E1 目标漂移 | 20 | 8 | plan_dir/task_id 绑定，其他任务不作为上下文 |
| E2 幻觉输出 | 20 | 9 | Oracle=0 明确保持 provisional |
| E3 虚假完成 | 15 | 8 | VerifyGate 通过后才允许 task-done；未完成 plan 仍阻断 |
| E4 惯性执行 | 12 | 7 | 网络/凭据/破坏性路径按边界跳过并留痕 |
| E5 症状混淆 | 10 | 6 | error-dna 完整行为矩阵尚未执行 |
| E6 自我矛盾 | 13 | 7 | TDD 红测揭示并修复 token/plan 状态冲突 |
| E7 过度自信 | 10 | 7 | 结论不认证；独立 Oracle 未执行 |
| E8 上下文遗忘 | 10 | 8 | current plan/token context 显式传递；跨会话未重放 |
| **E1-E8 加权** | **110** | **7.68** | **845/110** |

### 长期治理能力

| 维度 | 得分 | 依据 |
|---|---:|---|
| 抗衰减防线 | 9 | handoff/PreCompact 机制存在；未做完整重启实验 |
| AI 赋能的全流程自动化 | 8 | Goal 门禁、VerifyGate、task-done 已局部自动化 |
| 学习笔记积累 | 5 | 知识资产与行为回归仍未完全闭环 |
| 长期目标一致性 | 8 | 本轮目标、范围、报告和证据保持一致 |
| 功能标志分明 | 8 | task_id/plan_dir/token context 明确 |
| 内置安全与洞察 | 7 | 网络/凭据边界明确跳过，安全路径未全量运行 |
| Evaluation 评测框架 | 9 | 评分框架和 provisional gate 可运行，Oracle 缺失 |
| **长期治理均分** | **—** | **7.71** |

### 用户体验（独立，不计入 CarrorOS 能力总分）

| 维度 | 得分 |
|---|---:|
| 长期目标一致性 | 8 |
| 用户心智负担减轻 | 7 |
| 交互现代化 | 7 |
| 用户掌控感 | 8 |
| AI 智能感 | 7 |
| 行为可预测 | 8 |
| 人机权限分明 | 8 |
| **UX 均分** | **7.57** |

## 修复后实际验证

```text
python3 -m pytest .claude/scripts/test_task_token_isolation.py .claude/scripts/test_eval_aggregate.py .claude/skills/lx-goal/scripts/test_goal_lifecycle_regressions.py -q
12 passed in 0.02s

python3 -m py_compile .claude/skills/lx-goal/scripts/lx-goal.py .claude/scripts/plan_builder.py .claude/scripts/carros_base.py .claude/scripts/eval-aggregate.py .claude/skills/lx-goal/scripts/test_goal_lifecycle_regressions.py
exit_code 0

git diff --check
exit_code 0

python3 .claude/skills/lx-goal/scripts/lx-goal.py assert-plan-dir
/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX

python3 .claude/skills/lx-goal/scripts/lx-goal.py verify-step S1
✅ S1: VERIFIED

python3 .claude/skills/lx-goal/scripts/lx-goal.py task-done "TDD 修复 Goal plan_dir、VerifyGate token 绑定、计划字段和 task-done 幂等性"
✅ 已验证并标记任务完成

python3 .omc/archive/20260811_carroros-governance-evaluation-finalization-and-spawn/carroros-governance-evaluation-finalization-and-spawn/spawn-fixture.py
SUBAGENT_SPAWN_FIXTURE=PASS

python3 .claude/scripts/eval-aggregate.py --scorecard .claude/references/scorecard.md --meta-verdict .omc/state/oracle --output /tmp/carroros-eval-index3.md
Certification: PROVISIONAL / NOT_CERTIFIED
Oracle 评审记录: 0 条
```

## 已复现并修复的错误

| 错误 | 根因 | 修复后状态 |
|---|---|---|
| `assert-plan-dir` 找不到 plan_dir | 旧 mode file 指向不存在目录时没有当前任务恢复能力 | 新 Goal 激活后 plan_dir 可由自身 mode/token 绑定恢复；过期/删除目录仍 fail-closed |
| ResearchGate dependency tree 缺 bullet | research 模板/人工填充缺少结构化 bullet | TDD 固定 bullet 要求；缺失继续阻断，不伪造内容 |
| PlanGate acceptance 为空 | PlanBuilder 没生成 acceptance 字段 | 已补生成字段 |
| `task-done` / `verify-step` `No active task` | VerifyGate 子进程未传当前 Goal token context | 已显式传递 token/task id/task dir |
| `task-done` 没有 current_step | VerifyGate 已完成最后一步后 task-done 不支持幂等收口 | 已允许完整 plan 直接收口；未完成 plan 仍阻断 |

## 未认证风险

1. Oracle 新鲜 verdict 仍为 0，aggregate 只能 provisional。
2. 完整统一回归入口引用缺失测试，且有状态暂存/恢复副作用。
3. 生产网络 SubAgent worker、真实 Oracle API/代理和凭据路径未执行。
4. GoalMachine 完整跨会话 plan→token→handoff→resume→done/off E2E 未执行。
5. empty/malformed/crash/cancel/retry-cap/takeover SubAgent 完整故障矩阵尚未认证。
6. `assert-plan-dir` 对真正被删除或过期的任务目录仍应 fail-closed；这是安全行为，不应自动猜测其他任务目录。

## 认证边界

本报告只认证本轮实际执行的局部 TDD、VerifyGate、task-done、聚合门禁和本地 spawn fixture。它不认证历史 scorecard 的运行时结论，也不把 `Oracle=0` 的 8.65 scorecard 值当作新鲜认证分数。

## 证据索引

- `.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/research.md`
- `.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/plan.md`
- `.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/executor.md`
- `.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/evidence.jsonl`
- `.claude/skills/lx-goal/scripts/test_goal_lifecycle_regressions.py`
- `.claude/scripts/test_task_token_isolation.py`
- `.claude/scripts/test_eval_aggregate.py`
