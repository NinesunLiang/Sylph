---
type: benchmark-report
benchmark: carroros-governance-efficacy
version: index1
status: provisional-not-certified
date: 2026-08-11
---

# CarrorOS 治理效能 Benchmark index1

## 结论

本轮完成了四项优化的**可验证门禁补强与重新评测**，但结果仍为：

> **PROVISIONAL / NOT_CERTIFIED**

原因是当前仓库没有可用的完整统一回归入口，真实网络 SubAgent/Oracle 路径按边界未执行，且认证聚合要求至少存在一条可解析 Oracle verdict；本轮只验证本地 fixture 和聚合器门禁，未伪造 Oracle 结果。

## 评分结果

| 维度 | 优化前对照 | 本轮评分 | 证据等级 | 结论 |
|---|---:|---:|---|---|
| C1-C9 AI 能力加权 | 7.71 | 7.71 | 历史运行时 + 本轮静态/局部测试 | provisional |
| E1-E8 错误防护加权 | 7.68 | 7.68 | 历史运行时 + 本轮聚合门禁 | provisional |
| 长期治理均分 | 7.71 | 7.71 | 历史报告与当前源码 | provisional |
| UX 独立均分 | 6.57 | 6.57 | 历史独立外评 | observation only |
| 24 项总加权 | 7.67 | 7.67 | scorecard 对照，未完成新鲜 Oracle 审计 | 未达 8.6 |

### 能力维度 C1-C9

| 指标 | 分数 | 当前依据 |
|---|---:|---|
| C1 指令清晰度 | 9 | 规则与 gate 文档存在，现役全量回归缺失 |
| C2 上下文完整度 | 8 | handoff/SSOT 设计存在，完整生命周期未重放 |
| C3 流程结构化 | 9 | Goal 分阶段结构存在，GoalMachine 依赖缺失需补测 |
| C4 输出规范化 | 7 | 本轮聚合报告新增认证字段 |
| C5 工具生命周期 | 8 | 历史生命周期证据，本轮未重放跨会话闭环 |
| C6 知识密度 | 6 | 评测材料多，行为断言与报告证据仍不完全闭合 |
| C7 关联编排 | 7 | 本地 fixture 通过，生产网络 worker 未执行 |
| C8 可维护性 | 6 | 回归脚本与实际测试树存在漂移 |
| C9 错误恢复 | 8 | 本地成功/缺 instruction/timeout fixture 通过，故障矩阵不完整 |

### 错误防护 E1-E8

| 指标 | 分数 |
|---|---:|
| E1 目标漂移 | 8 |
| E2 幻觉输出 | 9 |
| E3 虚假完成 | 8 |
| E4 惯性执行 | 7 |
| E5 症状混淆 | 6 |
| E6 自我矛盾 | 7 |
| E7 过度自信 | 7 |
| E8 上下文遗忘 | 8 |

### 长期治理与 UX

长期治理：抗衰减防线 9、全流程自动化 7、学习笔记积累 5、长期目标一致性 8、功能标志分明 8、内置安全与洞察 7、Evaluation 框架 9。

UX：长期目标一致性 8、心智负担减轻 7、交互现代化 7、用户掌控感 8、AI 智能感 7、行为可预测 7、人机权限分明 8。

## 四项优化验证

### P0：Oracle verdict 与 aggregate 门禁

已修改 `.claude/scripts/eval-aggregate.py`：

- 有 scorecard 但没有 Oracle verdict 时，报告明确 `PROVISIONAL / NOT_CERTIFIED`；
- 有可解析 scorecard 和 verdict 时才显示 `CERTIFIED`；
- 新增 `test_eval_aggregate.py` 覆盖 Oracle=0 与有效 verdict 两条路径。

### P1：plan/token/handoff/GoalMachine 生命周期

本轮未声称完整修复。当前证据显示 handoff/lifecycle 局部测试存在，但 GoalMachine 依赖和 plan→token→handoff→resume→done/off 端到端验证仍不完整，因此该项只按 provisional 评分。

### P1：SubAgent failure recovery

本地 spawn fixture 已验证：

- loopback 成功：completed；
- 缺 instruction：failed；
- 延迟：timeout；
- 输出：`SUBAGENT_SPAWN_FIXTURE=PASS`。

empty、malformed、crash、cancel、retry-cap、takeover 的完整矩阵仍未认证；真实网络 worker 未执行。

### P2：统一评分报告 schema

本轮聚合报告增加认证状态和认证条件；本 Benchmark 报告统一记录评分、证据等级、命令、风险与未认证项。独立 score_report schema 尚未建立，因此不把 schema 完整性标为完成。

## 可复现命令与结果

```text
python3 -m pytest .claude/scripts/test_task_token_isolation.py .claude/scripts/test_eval_aggregate.py -q
# 实际结果：8 passed in 0.02s

python3 -m py_compile .claude/scripts/carros_base.py .claude/scripts/eval-aggregate.py .claude/scripts/test_task_token_isolation.py .claude/scripts/test_eval_aggregate.py
# 实际结果：exit_code 0

git diff --check
# 实际结果：exit_code 0

python3 .omc/archive/20260811_carroros-governance-evaluation-finalization-and-spawn/carroros-governance-evaluation-finalization-and-spawn/spawn-fixture.py
# 实际结果：SUBAGENT_SPAWN_FIXTURE=PASS
```

`bash scripts/run-regression.sh` 未执行：当前引用的多数测试入口不存在，并且脚本有状态暂存/恢复副作用。网络 Oracle、凭据路径、CI 依赖安装和完整 manager worker 未执行。

## 未认证风险

1. Oracle 新鲜 verdict 不足，不能认证 24 项总分。
2. 完整统一回归入口缺失或路径漂移。
3. GoalMachine 生命周期没有当前仓库内的完整 E2E 证据。
4. SubAgent failure recovery 完整矩阵尚未实现/验证。
5. 现有 `.omc/session-handoff.md`、`AGENTS.md` 和 `state/` 有运行时或既有修改，本轮未覆盖、回滚或删除。

## 证据索引

- `.claude/scripts/eval-aggregate.py`
- `.claude/scripts/test_eval_aggregate.py`
- `.claude/scripts/test_task_token_isolation.py`
- `.omc/tasks/20260811/unnamed/evidence.jsonl`
- `.omc/state/eval-report.md`
- `.claude/references/evaluation-framework.md`
