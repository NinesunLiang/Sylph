# Carror OS 文档

> **版本**: v6.2.0 | **更新**: 2026-05-15

Carror OS 的文档按**概念层级**组织，从思想到实现到反馈闭环：

```
哲学 (Why)  →  规则 (What)  →  机制 (How)  →  数据投喂 (Feedback)
  思想层          骨架层          血肉层           血液养分层
```

---

## 1. 哲学 — 思想层

> Carror OS 为什么这样设计？决策时价值排序是什么？

| 文档 | 说明 |
|------|------|
| [philosophy/cn/worldview.md](philosophy/cn/worldview.md) | 世界观：AI、人、工具的关系 |
| [guides/cn/philosophy.md](guides/cn/philosophy.md) | 7 条哲学原则详解，优先级排序，冲突裁决规则 |
| [overview/cn/what-is-carror-os.md](overview/cn/what-is-carror-os.md) | 产品定义 + 核心价值主张 |
| [guides/cn/for-beginners.md](guides/cn/for-beginners.md) | 入门：哲学如何影响日常 AI 行为 |

## 2. 规则 — 骨架层

> Carror OS 的行为边界。哪些不可违背？决策权限如何分配？

| 文档 | 说明 |
|------|------|
| [`../source/harness-kit/AGENTS.md`](../source/harness-kit/AGENTS.md) | **铁律源头** — 8 条铁律 + 交互原则 + 软完成语禁令 + Oracle 终审要求 |
| [concepts/cn/gates.md](concepts/cn/gates.md) | 门禁体系：Gate / Guard / Monitor 分类与触发条件 |
| [concepts/cn/context-control.md](concepts/cn/context-control.md) | 上下文控制规则：甜点区 / 危险区 / 逃生通道 |
| [concepts/cn/workflow.md](concepts/cn/workflow.md) | 工作流分层 (L1-L4) + Oracle 终审触发条件 |
| [concepts/cn/audit-trail.md](concepts/cn/audit-trail.md) | 审计追踪规则：谁在什么时候做了什么决策 |

## 3. 机制 — 血肉层

> Carror OS 用什么手段执行规则？Hook / Skill / Script / Gate 如何协作？

| 文档 | 说明 |
|------|------|
| [guides/cn/hook-configuration.md](guides/cn/hook-configuration.md) | Hook 脚本体系（30+ hook）：注册、matcher、三方一致性 |
| [guides/cn/skills-catalog.md](guides/cn/skills-catalog.md) | 27 个 Skill 能力目录：触发词、能力边界、成熟度标注 |
| [technical/cn/mechanisms-deep-dive.md](technical/cn/mechanisms-deep-dive.md) | 机制深度解析：Hook 执行时序、降级链、模式检测 |
| [technical/cn/skill-atomization-guide.md](technical/cn/skill-atomization-guide.md) | Skill 三层架构规范：SKILL.md / scripts/ / references/ |
| [technical/cn/scoring-framework.md](technical/cn/scoring-framework.md) | C/E/G/U 四维评分框架 |
| [pipeline-orchestration.md](pipeline-orchestration.md) | OMA 管线编排：hier → split → gov → rpe → dev |
| [governance/cn/features.md](governance/cn/features.md) | 版本功能矩阵 |

## 4. 数据投喂 — 血液养分层

> 系统如何从运行中学习？错误如何反哺规则？

| 文档 | 说明 |
|------|------|
| [`../.claude/claude-next.md`](../.claude/claude-next.md) | **AI 学习笔记** — R / DG / DF / ED 经验积累，每条背后是一次生产事故 |
| [`../.omc/state/error-dna/`](../.omc/state/) | **Error-DNA** — 逃逸检测 + 免疫系统，从"收集失败"到"检测成功逃逸" |
| [`../.omc/state/dogfood/`](../.omc/state/dogfood/) | **狗粮记录** — 结构化 YAML，每次狗粮会话的完整复盘 |
| [dogfooding/cn/flywheel-first-turn.md](dogfooding/cn/flywheel-first-turn.md) | 狗粮反馈循环协议：发现问题 → 修复 → 加机制 → 传播 → 验证 |
| [dogfooding/cn/dogfood-permission-gate-self-dos.md](dogfooding/cn/dogfood-permission-gate-self-dos.md) | 狗粮案例：permission-gate 自毁事故全记录 |
| [acceptance/cn/hooks-production-acceptance-20260505.md](acceptance/cn/hooks-production-acceptance-20260505.md) | 验收证据：Hook 生产验证通过报告 |
| [reference/cn/feedback-questions.md](reference/cn/feedback-questions.md) | 反馈问题模板 |
| [internal/cn/EVIDENCE-BANK.md](internal/cn/EVIDENCE-BANK.md) | 证据银行 |
| [internal/cn/DOGFOODING-LOG.md](internal/cn/DOGFOODING-LOG.md) | 狗粮运行日志 |

---

## 其他目录

| 目录 | 用途 | 受众 |
|------|------|------|
| [marketing/](marketing/) | 宣发、社区投稿、品牌哲学 | 外部用户、社区、媒体 |
| [story/](story/) | 世界观叙事（15 篇故事） | 想理解产品哲学故事的读者 |
| [technical/](technical/) | 架构分析、技术评估、跨平台 | 开发者、技术决策者 |
| [governance/](governance/) | 版本说明、迁移指南、测试策略 | 用户、贡献者 |
| [internal/](internal/) | 审计记录、评分报告、内部模板 | 仅内部使用 |
| [tests/](tests/) | 验收测试手册 | QA、Dogfooding |

---

## 阅读路径

**首次接触**：`1.哲学 → overview → guides/cn/for-beginners.md`  
**想理解规则**：`2.规则 → AGENTS.md → concepts/cn/gates.md`  
**想了解实现**：`3.机制 → guides/cn/hook-configuration.md → guides/cn/skills-catalog.md`  
**想理解学习闭环**：`4.数据投喂 → dogfooding/flywheel-first-turn → claude-next.md`

> 大多数文档提供 **cn/**（中文）和 **us/**（英文）双语版本。部分文档（story, philosophy guide）仅中文，英文持续补充中。

> **注意**: story/us/ 英文故事译本尚未完成。story 系列目前仅提供中文版。
