# Phase 0.5: Oracle 自主计划审核

> **哲学 #6（0信任）物化：AI 自判"不需要问人"不可信。独立 Oracle 对抗性审查自主计划。**

## 触发条件

所有 ghost 激活均强制执行。Oracle critic agent（opus），独立上下文，不共享主会话。

## 五维门禁

| # | 维度 | 检查内容 | 常见盲区 |
|---|------|---------|---------|
| D1 | **方向适配** | ghost vs goal 选择是否正确？有无 GL-01 方向漂移风险？ | 修复清单误用 ghost 模式 |
| D2 | **歧义穷尽** | Phase 0 是否有未覆盖的歧义？AI 自判"不需要问"是否合理？ | 技术决策误判为用户偏好 |
| D3 | **硬边界完整** | 任务触及面是否可能触碰未声明的禁区？ | 间接引用敏感文件 |
| D4 | **决策链覆盖** | autonomous-decision-chain 矩阵是否覆盖该任务场景？ | 新颖场景矩阵缺失 |
| D5 | **退出条件** | 成功/失败信号是否可验证？min_iterations 是否合理？ | 主观成功标准不可测 |

## 裁决协议

- `[Oracle: ACCEPT]` → 进入 Step 0.5 激活
- `[Oracle: REVISE]` → AI 按 Oracle 反馈调整计划 → 重新提交 Oracle（最多 2 轮）
- `[Oracle: REJECT]` → 阻断激活，向人类报告 Oracle 驳回理由 + AI 原计划差异

## 留痕

Oracle 裁决写入 `.omc/state/oracle-verdicts.md`
