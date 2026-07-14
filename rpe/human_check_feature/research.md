# Research — human_check_feature

## 1. 需求理解

输入 PRD：`rpe/human_check_feature/prd.md`

目标是围绕 CarrorOS 原始 10 项目标建立人工审核验收计划。该计划不是自动判定 GA，而是给人类提供真实验收路径、正确表现、错误表现、证据要求和最终人工判定模板。

关键约束：

- AI 不能替用户做最终验收决策。
- 验收必须基于真实运行和磁盘证据，而不是 AI 自报。
- `ga_ready` 只有在人类完成真实验收且剩余 GA 条件闭合后才可考虑为 true。
- 本 RPE 包应服务于人工验收执行和跨会话恢复。

## 2. 现有治理约束

`AGENTS.md` 明确 CarrorOS 的核心优先级：验证、零信任、守护、文档、人本、增益、少。关键约束包括：

- 没通过验证等于没做：`AGENTS.md:14`
- 断言必须有证据：`AGENTS.md:15`
- 磁盘比 context 可靠：`AGENTS.md:17`
- 战略权留人类：`AGENTS.md:18`
- 完成标准要求 VerifyGate、lint、plan 文件闭合：`AGENTS.md:68`

这些约束与 PRD 中“最终验收由人类执行”一致。

## 3. 已有证据链路

### 3.1 Formal seal

`.claude/scripts/formal_seal.py` 已经提供 formal manifest 与 GA gate 汇总能力：

- `VERIFY_DIR` 指向 `.omc/metrics/runtime-verify`：`.claude/scripts/formal_seal.py:26`
- GA structured evidence 包含 CAS/L5/WATER gates：`.claude/scripts/formal_seal.py:30`
- GA observability 文件为 `.omc/metrics/ga/observability.json`：`.claude/scripts/formal_seal.py:38`
- GA behavioral validation 文件为 `.omc/metrics/runtime-verify/ga-behavioral-validation.json`：`.claude/scripts/formal_seal.py:39`
- `build_ga_gates()` 汇总 GA gate 状态：`.claude/scripts/formal_seal.py:160`
- `build_ga_behavioral_validations()` 汇总 behavioral validation 状态：`.claude/scripts/formal_seal.py:219`
- manifest 仍保持 `ga_ready: False`：`.claude/scripts/formal_seal.py:274`

结论：formal seal 是可复核证据入口，但不是人工验收的替代品。

### 3.2 GA behavioral validation

`.claude/scripts/ga_behavioral_validation.py` 已经覆盖五个自动行为验证场景：

- Long-session observability：`.claude/scripts/ga_behavioral_validation.py:110`
- Compact/L5 recovery：`.claude/scripts/ga_behavioral_validation.py:143`
- Unattended goal failure injection：`.claude/scripts/ga_behavioral_validation.py:172`
- Flywheel replay/promotion/rollback：`.claude/scripts/ga_behavioral_validation.py:198`
- Decision governance：后续函数在同文件中实现

该脚本定位为 deterministic behavioral validation，不等价于完整人工验收。它验证行为证据形状和 guardrail，而 PRD 要求人类真实观察 A/B/C/D/E 路径。

## 4. PRD 任务结构

PRD 将人工验收拆为五条路径：

| 路径 | 名称 | 覆盖目标 |
|---|---|---|
| A | Context / Compact / 文档恢复 / U 型注意力 / 工作流 | 1, 2, 3, 6, 8 |
| B | Goal / 无人模式 / Loop 硬化 | 7, 8, 9 |
| C | Flywheel / 自我学习 | 4, 3, 6 |
| D | L1/L2 分级与智能决策 | 5, 9, 10 |
| E | 双审判官与 Verify 优先级 | 8, 9, 10 |

每条路径都包含：

- 验收路径
- 人工观测点
- 正确表现
- 错误表现
- AC
- 停止条件或失败条件

## 5. 数据流

```text
rpe/human_check_feature/prd.md
  → research.md：需求理解、证据源、风险、边界
  → plan.md：RPE-A 至 RPE-F Step + AC + 回滚/停止条件
  → executor.md：人工执行时逐步记录 evidence block
  → state/progress.md：跨会话恢复状态
  → 人类执行 A/B/C/D/E 验收
  → 人类填写最终 verdict
```

## 6. 风险与缓解

| 风险 | 触发条件 | 缓解 |
|---|---|---|
| AI 替用户做验收结论 | 输出 PASS/FAIL 作为最终结论 | executor 只提供记录模板，最终 verdict 字段留给人类 |
| 把自动脚本绿灯误当 GA | 只跑 `ga_behavioral_validation.py` 就声称完成 | plan 明确区分自动行为验证和人工 L2 Proven |
| 验收过程不可恢复 | 没有 RPE state/progress | 已创建 `state/progress.md` |
| 验收证据分散 | 人工执行后找不到证据 | 每个 Step 要求 evidence_files 和 commands_observed |
| 危险操作越界 | 验收中涉及 push/delete/认证改口 | 每个 Step 加停止条件，危险操作不作为自动验收内容 |

## 7. 待确认问题

当前没有阻断性问题。进入 Phase 2 计划后，用户可决定：

- 是否立即执行 A/B/C/D/E 人工验收；
- 是否只执行一次综合强验收；
- 是否把验收结果提交到 repo。

## 8. Gate-R 自检

| Gate | 结果 | 依据 |
|---|---|---|
| R1 链路完整且可解释 | PASS | PRD → research/plan/executor/progress 链路明确 |
| R2 约束完整 | PASS | 明确人类验收、GA 边界、危险操作边界 |
| R3 风险可解释 | PASS | 风险表含触发条件与缓解 |
| R4 未决问题已处理 | PASS | 无阻断问题，剩余为用户执行选择 |
| R5 假设含证伪规则 | PASS | 每条路径在 PRD 中含错误表现 |
| R6 进度快照已核实 | PASS | `state/progress.md` 已创建 |
