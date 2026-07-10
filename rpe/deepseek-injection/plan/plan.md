# Plan: DeepSeek-V4 Agent 强化注入

> Phase: Plan | Date: 2026-07-09

## Goal

集成 4 个注入模块，提升 deepseek 模型在 CarrorOS 上的表现。

## Scope

- `.claude/scripts/deepseek_inject.py` — 注入引擎
- `.claude/hooks/userprompt-level-hint.py` — 按模型路由注入
- `.claude/kernel.md` — 注入协议文本

## Steps

### S1: 实现核心注入引擎
- ReasoningChainEnforcer
- KnowledgeBoundaryMarker  
- SelfCheckLimiter
- 输出: `.claude/scripts/deepseek_inject.py`

### S2: 实现状态压缩引擎
- StateCompressionEngine
- 积分到 prompt-collector hook
- 输出: `.claude/scripts/state_compress.py`

### S3: Hook 层集成
- 修改 userprompt-level-hint.py：检测 deepseek 模型 → 注入协议
- 修改 prompt-collector：触发状态压缩
- 输出: 修改 2 个 hook 文件

### S4: 验证
- 对比测试注入前后效果
- 验证非 deepseek 模型不受影响
