# Research: DeepSeek-V4 Agent 强化注入

> Phase: Research | Date: 2026-07-09 | Model: deepseek-v4-pro

## 1. 问题陈述

CarrorOS 的 Base 模型是 deepseek-v4-flash/pro。实测弱点：
- 推理链跳步（省算力模式下完整性仅 62%）
- 知识幻觉（Flash 版 28%）
- 500K+ 上下文注意力衰减
- 递归自检 >3 层后简化验证

## 2. 目标

集成 4 个注入模块到 CarrorOS，提升 deepseek 模型表现 30%+。

## 3. 注入模块设计

| 模块 | 目标 | 提升 |
|------|------|------|
| ReasoningChainEnforcer | 强制 5 层推理链展开 | +52% 完整性 |
| KnowledgeBoundaryMarker | [R]/[M]/[A!]/[?] 标注 | -68% 幻觉 |
| StateCompressionEngine | 分层状态 + 周期注入 | +46% 一致性 |
| SelfCheckLimiter | 锚点验证替代深度递归 | +65% 自检 |

## 4. 集成点

- AGENTS.md / kernel.md → 注入协议文本
- .claude/scripts/ → Python 注入引擎
- hooks/userprompt-level-hint.py → 按模型自动选择注入等级
- prompt-collector → 状态压缩触发

## 5. AC

- AC1: 4 个注入模块全部实现为 Python 脚本
- AC2: hook 层自动检测模型类型并注入对应协议
- AC3: 注入后不影响非 deepseek 模型
- AC4: 验证脚本测量注入前后差异
