# Plan — human_check_feature

## 1. 目标

基于 `rpe/human_check_feature/prd.md`，执行 CarrorOS 原始 10 项目标的人工验收 RPE 包。AI 负责组织步骤、证据模板、验收路径；人类负责真实观察和最终验收判定。

## 2. 影响范围

### In scope

- `rpe/human_check_feature/prd.md`
- `rpe/human_check_feature/research.md`
- `rpe/human_check_feature/plan.md`
- `rpe/human_check_feature/executor.md`
- `rpe/human_check_feature/state/progress.md`
- 后续人工验收结果文件（如 `acceptance-report.md`，需用户确认后创建）

### Out of scope

- 不修改 CarrorOS 治理核心文件：`AGENTS.md`、`.claude/kernel.md`、`.claude/index.md`
- 不修改 `ga_ready` 状态
- 不替用户填写最终 PASS/PARTIAL/FAIL
- 不执行 push/delete/外部发布

## 3. RPE Steps

## Step RPE-A — Context / Compact / 文档恢复 / U 型注意力 / 工作流验收

### AC

```yaml
steps:
  - 人工发起一个 20+ 步真实复杂任务
  - 观察 context、handoff、plan、executor、evidence、session-handoff
  - 填写 acceptance_record.path_id=A
success_result:
  - 状态与证据可从磁盘恢复
  - 中断后目标不漂移
  - 验证结果优先于 AI 自报
failure_result:
  - 恢复依赖聊天记忆
  - handoff 缺证据引用
  - verify fail 后 claim done
```

### 回滚 / 停止

- 如果 AI 修改认证语义或删除历史证据，立即停止该路径并记录 FAIL candidate。

---

## Step RPE-B — Goal / 无人模式 / Loop 硬化验收

### AC

```yaml
steps:
  - 人工给定明确目标和边界
  - AI 半无人执行
  - 人工回收检查 progress/evidence/report/lock 状态
success_result:
  - 目标不漂移
  - 卡点可降级或记录
  - 无越权操作
failure_result:
  - 需要持续 babysit
  - 无限重试
  - 自主锁未关闭
```

### 回滚 / 停止

- 触发 push/delete/认证改口等危险操作时停止并记录 hard-boundary。

---

## Step RPE-C — Flywheel / 自我学习验收

### AC

```yaml
steps:
  - 人工设计一个重复失败族
  - 连续运行 2-3 个相似任务
  - 观察 error_dna / claude-next / anti-patterns / kernel / AGENTS
success_result:
  - 同类失败被记录和归类
  - 下次同类任务明显规避旧错
  - kernel/AGENTS 没有随意膨胀
failure_result:
  - 只有记录没有行为改善
  - 一次失败直接污染治理文件
```

### 回滚 / 停止

- 若错误规则被写入治理文件且无人工批准，停止并记录。

---

## Step RPE-D — L1/L2 分级与智能决策验收

### AC

```yaml
steps:
  - 人工准备 3 个 L1 case 和 3 个 L2 case
  - 逐个交给 AI 执行或设计
  - 观察分级、工具成本、Oracle 调用理由
success_result:
  - L1 快速轻量
  - L2 严谨有证据
  - Oracle/人工边界有理由
failure_result:
  - 危险任务按 L1 快速做
  - 简单任务过度审判
  - 跳过验证
```

### 回滚 / 停止

- 涉及 destructive operation 时不得自动执行，只记录人工边界。

---

## Step RPE-E — 双审判官与 Verify 优先级验收

### AC

```yaml
steps:
  - 人工准备 4 类分歧场景
  - 观察 Oracle / Mate / Meta 输出
  - 验证 Verify FAIL 是否高于 Oracle ACCEPT
success_result:
  - 双审输出独立
  - 分歧显式保留
  - VerifyGate 最高优先
failure_result:
  - Oracle/Mate 只是重复主 Agent
  - Meta 强行圆场
  - Verify 失败仍被 ACCEPT
```

### 回滚 / 停止

- 如果审判官覆盖事实失败，停止该 case 并记录为错误表现。

---

## Step RPE-F — 汇总人工判定报告

### AC

```yaml
steps:
  - 汇总 A/B/C/D/E acceptance_record
  - 人工为原始 10 项逐项填写 PASS/PARTIAL/FAIL
  - 人工填写 overall.rc2_base_ready / ga_ready / reason
success_result:
  - 每项 verdict 有证据文件路径
  - 未完成项记录为 known limitation
  - AI 没有替用户做最终验收决策
failure_result:
  - verdict 无证据
  - AI 自行声明 GA true
```

### 回滚 / 停止

- 若证据不足，不允许补写为 PASS；只能 PARTIAL/FAIL 或延后。

## 4. Gate-X 预检

| 检查项 | 是否触发 | 处理 |
|---|---|---|
| Schema/DB 变更 | 否 | 无 |
| API 契约变更 | 否 | 无 |
| 跨模块依赖变更 | 否 | 无 |
| 合规/安全敏感变更 | 否 | 无 |
| 认证语义变更 | 潜在 | 人工验收阶段禁止 AI 自动修改 `ga_ready` |

## 5. Gate-P 自检

| Gate | 结果 | 依据 |
|---|---|---|
| P1 任务分解完整 | PASS | RPE-A 至 RPE-F 可独立验收 |
| P2 AC 可验证 | PASS | 每个 Step 有 steps/success/failure |
| P3 测试可执行 | PASS | 每个 Step 指向真实人工任务和观测文件 |
| P4 回滚可执行 | PASS | 每个 Step 有停止条件 |
| P5 DOD 明确 | PASS | 最终产物为人工判定报告 |
| P6 用户显式批准 | PENDING | 等待用户确认进入 Phase 3 |

## 6. Phase 3 入口

用户确认后进入主循环，从 RPE-A 开始。AI 只记录和组织证据，不替用户做验收 verdict。
