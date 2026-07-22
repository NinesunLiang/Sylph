# CarrorOS Enhance 优化方案 v1

## 背景

CarrorOS 分 Base（中低阶模型）和 Enhance（高阶模型）两版。Base 已稳定，现在启动 Enhance 优化。

依据 Base/Enhance 差异文档（`~/Desktop/CarrorOS-Base-Enhance-差异.md`）：

| 维度 | Base | Enhance |
|:----|:----|:---------|
| 目标模型 | DeepSeek-V4-Flash、Qwen3.7-Plus 等 | Opus、GPT、Grok 等 |
| 核心理念 | 路径正确 → 约束 | 路径正确 + 增强 |
| 实现方式 | superpowers 式严格路由 + spec 文档 | grill-me 式调研 + TDD（不设 spec） |
| 不适配 | 飞轮等需高模型能力的功能 | — |
| 独有目标 | — | AI 资产化（数据下沉 + 升华） |

## 优化项

### 1. lx-goal Enhance 增强版

**当前**: lx-goal v1.5.1 已有 Phase0 HARD-GATE + 退出前验证（和 Base 相同）

**Enhance 增强**:
- Phase0 去掉 spec 文档模板限制，改为 grill-me 式自由对话调研
- 不再要求 2-3 方案对比（高阶模型自己能判断何时需要）
- 退出前验证从 check-list 改为 TDD 式验收（先写测试再验证）
- 加入 claude-next 数据采集点（每次执行后记录决策和上下文）

**收益**: 高阶模型不受文档模板束缚，发挥更强能力。TDD 验收比 check-list 更严格。

### 2. 飞轮系统（Flywheel）

**当前**: Base 未实现。飞轮需要高模型能力来做数据升华。

**Enhance 实现**:
- 每次任务完成后采集：决策日志 → 错误模式 → 优化建议
- `.error-dna` 自动记录失败模式（error type → root cause → fix → prevent）
- `.claude-next.md` 自动更新（新学到的项目知识）
- `anti-patterns` 自动记录（什么方式在这个项目里不 work）
- **升华管道**: 每日 cron 汇总 → 高阶模型提炼 → 下沉到 kernel.md

**收益**: AI 越用越懂项目。高阶模型的分析能力使数据有价值。

### 3. AI 资产化管线

**当前**: 零散记录，无系统化

**Enhance 实现**:
- 三数据源：`.claude-next.md`（正向知识）/ `.error-dna`（错误知识）/ `anti-patterns`（无效模式）
- 每日 cron 聚合 → 高阶模型 review → 冲突检测 → 写入 kernel.md（升华）
- 每月大清理：老数据归档，新摘要写入宫殿

**收益**: AI 在项目中每天学习，不再每次都从零开始。

### 4. Oracle 增强

**当前**: Base 版 Oracle 用 DeepSeek-V4-Flash 做审核

**Enhance 增强**:
- Oracle 双审使用高阶模型（Opus/GPT）做更深层分析
- 加入架构建议模式（不仅 AC/REJECT，还给出重构建议）
- `_is_autonomous_mode()` 已支持无人模式信号

**收益**: 高阶模型的审核更深入，能发现中低阶模型无法察觉的问题。

## 实施顺序

| Phase | 内容 | 依赖 | 工作量 |
|:----:|:----|:----|:------:|
| **P0** | lx-goal Enhance 增强版 | 当前 Base lx-goal | 小 |
| **P1** | Oracle 增强（高阶模型） | 当前 oracle_agent.py | 中 |
| **P2** | 飞轮系统搭建 | P0 + P1 | 大 |
| **P3** | AI 资产化管线 | P2 | 大 |

## 问题

1. 飞轮的数据升华频率？每日 / 每次执行 / 每周？
2. Oracle 增强使用哪些高阶模型？Opus / GPT / 两者都？
3. lx-goal Enhance 版是否保留 Base 的 HARD-GATE 机制？
