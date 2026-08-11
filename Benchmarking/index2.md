---
type: benchmark-report
benchmark: carroros-governance-efficacy
version: index2
status: provisional-not-certified
date: 2026-08-11
---

# CarrorOS 治理效能 Benchmark index2

## 结论

本轮按当前 Goal 任务自身的 `plan_dir` 和 token 执行，未读取其他 active token 作为任务状态。结果为：

> **PROVISIONAL / NOT_CERTIFIED**

本轮完成安全本地测试和真实本地空上下文 spawn fixture；未执行网络 Oracle、凭据路径、破坏性回归入口或 CI 安装。Oracle 新鲜 verdict 不足，因此不把历史分数升级为认证分数。

## 评分结果

| 维度 | 本轮分数 | 证据等级 | 判定 |
|---|---:|---|---|
| C1-C9 AI 能力加权 | 7.71 | 当前局部测试 + 历史运行时对照 | provisional |
| E1-E8 错误防护加权 | 7.68 | 当前聚合门禁 + 历史运行时对照 | provisional |
| 长期治理均分 | 7.71 | 当前源码审查 + 历史对照 | provisional |
| UX 独立均分 | 6.57 | 历史独立外评，仅作对照 | observation only |
| 24 项总加权 | 7.67 | 当前报告对照，未有新鲜 Oracle | 未达 8.6 |

### C1-C9 能力维度

| 指标 | 得分 | 当前评估依据 |
|---|---:|---|
| C1 指令清晰度 | 9 | Phase 0 ResearchGate/PlanGate 已实际通过；完整回归入口仍缺失 |
| C2 上下文完整度 | 8 | 当前 Goal 绑定 plan_dir/token；跨会话完整闭环未重放 |
| C3 流程结构化 | 9 | ResearchGate→PlanGate→执行链实际通过；GoalMachine E2E 不完整 |
| C4 输出规范化 | 7 | 聚合器新增 Certification 状态；独立 score schema 尚未建立 |
| C5 工具生命周期 | 8 | 当前 Goal 激活和门禁通过；done/off 全生命周期未在本轮完成 |
| C6 知识密度 | 6 | 评测框架和报告材料丰富，行为断言覆盖不足 |
| C7 关联编排 | 7 | 本地 spawn fixture 真实执行通过；生产 worker 未执行 |
| C8 可维护性 | 6 | 仍存在回归脚本与现役测试树漂移 |
| C9 错误恢复 | 8 | success/failure/timeout fixture 通过；完整 recovery matrix 未认证 |

### E1-E8 错误防护维度

| 指标 | 得分 | 当前评估依据 |
|---|---:|---|
| E1 目标漂移 | 8 | 本轮 task_id/plan_dir 自绑定；完整并发生命周期未测 |
| E2 幻觉输出 | 9 | 报告明确区分当前与历史证据，并禁止 Oracle=0 认证 |
| E3 虚假完成 | 8 | PlanGate 真实阻断 placeholder；完整 VerifyGate 回归未执行 |
| E4 惯性执行 | 7 | 高风险/网络路径按边界跳过并留痕 |
| E5 症状混淆 | 6 | 缺少完整 error-dna 行为矩阵 |
| E6 自我矛盾 | 7 | 当前 evidence 记录实际输出；仓库仍有历史状态漂移 |
| E7 过度自信 | 7 | 结论保持 provisional；未执行独立 Oracle 复核 |
| E8 上下文遗忘 | 8 | 当前 plan/research/evidence 已绑定；跨会话恢复未重放 |

### 长期治理能力

| 维度 | 得分 | 依据 |
|---|---:|---|
| 抗衰减防线 | 9 | 有 handoff/PreCompact 机制材料；本轮未做完整重启实验 |
| AI 赋能的全流程自动化 | 7 | Goal 门禁自动推进；全量回归入口不可安全重放 |
| 学习笔记积累 | 5 | 资产存在，但行为验证和知识沉淀关联不足 |
| 长期目标一致性 | 8 | 当前目标、范围和报告一致；历史任务污染已隔离 |
| 功能标志分明 | 8 | 当前任务 scope 与报告路径明确 |
| 内置安全与洞察 | 7 | 网络、凭据和硬边界被跳过并记录 |
| Evaluation 评测框架 | 9 | 指标体系和聚合门禁存在；新鲜 Oracle verdict 缺失 |

### 用户体验（独立，不计入 CarrorOS 能力总分）

| 维度 | 得分 |
|---|---:|
| 长期目标一致性 | 8 |
| 用户心智负担减轻 | 7 |
| 交互现代化 | 7 |
| 用户掌控感 | 8 |
| AI 智能感 | 7 |
| 行为可预测 | 7 |
| 人机权限分明 | 8 |

## 本轮真实 spawn 测试

执行：

```text
python3 .omc/archive/20260811_carroros-governance-evaluation-finalization-and-spawn/carroros-governance-evaluation-finalization-and-spawn/spawn-fixture.py
```

实际输出：

```text
SUBAGENT_SPAWN_FIXTURE=PASS
success: completed
missing_instruction: failed / no instruction.md found
timeout: timeout
```

该 fixture 实际启动本地 `claude` CLI 子进程并验证成功、缺 instruction、超时分支；它不是静态伪造。生产网络 worker、代理、凭据相关路径未执行。

## 四项优化状态

### P0：Oracle verdict 与 aggregate 门禁

已完成局部修复：`.claude/scripts/eval-aggregate.py` 在 scorecard 存在但 Oracle verdict 为空时输出 `PROVISIONAL / NOT_CERTIFIED`；有可解析 verdict 才显示 `CERTIFIED`。`test_eval_aggregate.py` 覆盖两条路径。

### P1：plan/token/handoff/GoalMachine 生命周期

本轮确认 ResearchGate/PlanGate 实际通过并绑定当前任务；完整 plan→token→handoff→resume→done/off E2E 仍未认证，GoalMachine 依赖与现役状态链存在缺口。

### P1：SubAgent failure recovery

真实本地 fixture 覆盖 success、missing instruction、timeout；empty、malformed、crash、cancel、retry-cap、takeover 尚未形成完整可认证矩阵。

### P2：评分报告 schema

聚合报告已增加 Certification 和认证条件；本 Benchmark 报告统一记录分数、证据等级、命令、风险和未认证项。独立 score_report schema 尚未建立。

## 实际验证证据

```text
python3 -m pytest .claude/scripts/test_task_token_isolation.py .claude/scripts/test_eval_aggregate.py -q
8 passed in 0.02s

python3 -m py_compile .claude/scripts/carros_base.py .claude/scripts/eval-aggregate.py .claude/scripts/test_task_token_isolation.py .claude/scripts/test_eval_aggregate.py
exit_code 0

git diff --check
exit_code 0

python3 .omc/archive/20260811_carroros-governance-evaluation-finalization-and-spawn/carroros-governance-evaluation-finalization-and-spawn/spawn-fixture.py
SUBAGENT_SPAWN_FIXTURE=PASS
```

`.claude/hooks/tests/test_pkg_c_lifecycle.py` 本轮未执行：当前仓库该路径不存在；历史 worktree 路径不能作为当前证据。`bash scripts/run-regression.sh` 未执行：入口引用缺失测试且有状态暂存/恢复副作用。

## 未认证风险

1. 当前无新鲜 Oracle verdict，所有 aggregate 只能 provisional。
2. 完整统一回归入口存在路径漂移，不能声明全量回归通过。
3. GoalMachine 生命周期缺少当前仓库内完整 E2E。
4. SubAgent failure recovery 完整矩阵尚未实现/验证。
5. 网络、凭据、CI 安装和破坏性状态入口按边界跳过。

## 证据索引

- `.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/research.md`
- `.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/plan.md`
- `.omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/evidence.jsonl`
- `.claude/scripts/eval-aggregate.py`
- `.claude/scripts/test_eval_aggregate.py`
- `.claude/scripts/test_task_token_isolation.py`
