# 06 Fallback / Downgrade — 降级场景

## Goal

验证 L2 Enhance 场景下，当 **Oracle 不可用** 等核心能力缺失时，系统能否正确识别降级条件并优雅降级到 **L1 Base** 模式，保证基础功能不受影响。

## Context

| 属性 | 值 |
|---|---|
| 场景编号 | 06 |
| 场景名称 | fallback_downgrade |
| 启动层 | L2 Enhance（预期 → L1 Base） |
| 降级触发条件 | Oracle 不可用 / Multi-Judge 不可用 / 复杂水位不可用 / 学习飞轮不可用 |
| 预期最终层 | L1 Base |
| 验证导向 | 降级正确性 + 功能完整性 + 零中断 |

## Expected Files

| 文件 | 说明 |
|---|---|
| `plan.md` | 降级场景 plan，含降级条件与触发配置 |
| `executor.md` | 执行记录，含触发降级时的环境探测日志 |
| `handoff.md` | 若涉及跨系统交接，记录 L2→L1 交接内容 |
| `audit.md` | 最终审计记录，含降级判定依据 |
| `verify.log` | 验证过程日志 |

## Expected Plan Steps

```
S1: 环境探测 — 检测 Oracle / Multi-Judge / 水位模块可用性
S2: 能力评估 — 判断缺失能力是否影响 L2 Enhance 运行
S3: 降级决策 — 执行降级判定，触发 fallback 流程
S4: L1 Base 启动 — 使用 L1 Base 工作流（Plan → Step → Verify → Archive）
S5: 功能验证 — 确认 L1 Base 基础功能完备，无中断
S6: 审计归档 — 记录降级原因、时间、证据链
```

## Required Evidence

- [ ] 环境探测日志 — 证明 Oracle 等模块不可用（命令输出截图/日志片段）
- [ ] 降级触发记录 — plan.md 中降级条件被显式标记
- [ ] L1 Base 工作流使用记录 — 显示 Plan → Step → Verify → Archive 链路
- [ ] 功能验证通过记录 — `verify.log` 中 VERIFIED 标记
- [ ] 零中断证明 — 审计记录中无意外错误或数据丢失

## Expected Final Status

```
STATUS: COMPLETED
FINAL_LAYER: L1 Base
DOWNGRADE_TRIGGER: Oracle unavailable
FUNCTIONAL_INTEGRITY: PASS
```

## Trigger Conditions（降级触发条件清单）

以下任一条件满足时触发 L2→L1 降级：

| 条件编号 | 条件 | 严重等级 |
|---|---|---|
| TC-01 | Oracle（LLM API）不可达或超时 | Critical |
| TC-02 | Multi-Judge 模块返回 `UNAVAILABLE` | Critical |
| TC-03 | 复杂水位检测模块缺失或报错 | High |
| TC-04 | 学习飞轮（Feedback Loop）未初始化或数据损坏 | High |
| TC-05 | 安全令牌/凭据缺失导致无法认证 Oracle | Critical |

## Verification Checklist

- [ ] L2 Enhance 检测到 Oracle 不可用后是否正确进入降级？
- [ ] 降级过程中是否有数据丢失或状态损坏？
- [ ] L1 Base 是否能独立完成基础工作流（无 Oracle 依赖）？
- [ ] 降级日志是否完整记录触发条件与决策链条？
- [ ] 恢复后是否可重新进入 L2 Enhance（恢复测试）？

## Notes

- 降级应是 **优雅的（graceful）**，非硬中断
- 需要模拟 Oracle API 不可用场景（如断网/超时/返回错误）
- L1 Base 必须零依赖 Oracle / Multi-Judge / 水位模块
- 审计记录应包含时间戳，以便分析降级链路
