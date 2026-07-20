# CarrorOS — 项目故事

> 一个 AI 代理行为治理内核的诞生与演进

---

## 起源

CarrorOS 诞生于一个朴素的观察：AI 代理在软件项目中执行任务时，**缺乏系统性的行为约束和验证机制**。AI 说"做完了"，但谁检查？谁验证？谁为结果负责？

2026 年 7 月初，项目正式启动。设计源来自 `~/Desktop/重构3/round3/` 的一系列重构方案文档，CarrorOS 作为材料和对照组成立。最初的愿景并不是一个"操作系统"，而是一套**行为治理内核**——一套支配 AI 代理如何在项目中行动、思考、验证、归档的规则系统。

哲学根植于：**验证高于一切。没有证据的断言是噪音。**

## 关键里程碑

### 2026-07-06 — 重构版 CarrorOS 初始化

首个提交（`98623e5`）建立了项目骨架：
- **AGENTS.md** — 8 铁律 + 哲学 7 条 + 工作流模板
- **kernel.md** — 管理内核：冻结规则、学习飞轮、降级策略
- **index.md** — 渐进式披露路由表
- Hook 系统雏形：PreToolUse 门禁、compact/resume 机制

### 2026-07-07 — 核心机制落地

一周内密集建设，10 份设计文档全部完成：
- **双判官 Oracle 系统** — AI 裁决者验证另一个 AI 的输出（`oracle_agent.py`, `phase3_oracle.py`）
- **Compact/Resume** — 上下文压缩与恢复协议（`session-handoff.md`）
- **水位防线** — 可控预算水位 + 上下文水位两套体系
- **Hook 统一调度** — `hook-launcher.sh` 解决 CWD 依赖
- **证据收集环** — `tool_store.py` 工具结果落盘

### 2026-07-10 — 治理体系升级

大规模重构：
- Oracle 模型体系（同级模型 + 高级模型）
- Goal 状态机（目标驱动的自主执行）
- Sub-agent 系统（多代理协同）
- 审计日志 + Token 数据归档

### 2026-07-12 — v7.1.0 资产边界清理

关键重构完成：
- 运行时文件从 `.claude/` 迁移至 `.omc/`（资产边界明确化）
- 设计文档归档至 `.claude/references/design-docs/`
- 节点系统冷热分离（atoms hot/cold 分层）
- 引入 VERSION + CHANGELOG，版本管理规范化
- Base 模型适配（kernel.md + index.md 重写）

### 2026-07-14/15 — MVP 与评测体系

里程碑式进展：
- **GA 观测性门禁** — `ga_observability.py` 行为验证套件
- **Benchmark 框架** — 组件消融 A/B 评测（`ab_compare.py`）
- **CarrorOS Base 安装包** — `install.sh` 一键部署
- xsimplechat AI 分析集成 — 首轮 A/B 对比测试报告

### 2026-07-15/18 — RPE 缺陷修复与强化

人工验收 RPE A-E 全批次缺陷修复，十特性修复 3→10 全通过：
- Goal 模式硬化（无人值守断裂点修复）
- lx-rpe P0 修复
- Sol P0-SOL-1 复审收口（env override 双层锁 + 白名单收紧）

### 2026-07-19/20 — 评分冲刺 (v7.2.0)

四轮迭代（R0-R4）聚焦验证链完整性：
- **R0**: Hook matcher 扩展 + fail-closed 机制
- **R1**: Oracle 契约统一（僵尸双删、白名单语法门、fail-closed 降级）
- **R2**: 验证链修复（cmd_verify 接线 verify_gate、task-bound audit、双绑定）
- **R4**: 补缺冲刺（E1 edit-scope BLOCK、oracle FORCE 修复、secret-scan 门、幽灵路由清理）

评分：6.30 → 6.61 → 7.22 → **8.02（R4 终审）**，最低分从 4.0 升至 7.0。

## 当前状态

**版本：v7.2.0**

CarrorOS 已是一个功能完整的治理系统：
- **50+ Python 脚本** 支撑 10 大治理模块
- **6 个 CC Hook** 全自动执行，零人工干预工具调用门禁
- **L1/L2 双级治理** 按风险等级自动路由
- **Oracle 三模型体系**（静态/运行时/Meta）独立 Context 裁决
- **水位数控**：可控预算 40/70 + 上下文 50/70/80 四段防线
- **抗 Compact 设计**：全部状态在磁盘，不在对话 transcript
- **错误 DNA 自动学习**：失败模式归档 → 规则进化闭环

## 未来方向

- **Phase 3 Oracle** 双审判官独立 Context 裁决（已开始实验）
- **学习飞轮 Phase 2**：飞轮数据落地 `.omc/knowledge/`，自动模式提炼
- **更多平台支持**（Windows WSL 已验证，Linux 持续）
- **社区技能生态**：lx- 技能系统持续扩展
- **量化治理效率**：benchmark 持续追踪、ROI 可视化

---

*CarrorOS 不是传统意义上的操作系统。它是一个"看着机器的思维"——精确、绝对、不编造、不假设。*
