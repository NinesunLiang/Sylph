# CarrorOS Enhance 优化方案 v2

## 背景

CarrorOS 分 Base（中低阶模型）和 Enhance（高阶模型）两版。Base 已稳定，现在启动 Enhance 优化。

## 优化项

### 1. lx-goal Enhance 增强版（P0）

**当前**: lx-goal v1.5.1（Phase0 HARD-GATE + 退出前验证，同 Base）

**Enhance 增强**:
- Phase0 保留**最小结构模板**：HARD-GATE 保留，但去除非必要的 spec 格式限制
- 方案对比改为**基于任务复杂度动态触发**：
  - 简单任务（单文件改动/配置修改/纯文档）→ 跳过方案对比
  - 复杂任务（跨文件重构/架构变更/新增功能）→ 强制 2-3 方案对比
  - 判断标准：
    - 文件数触发：涉及 3+ 文件修改 → 自动复杂
    - **定性触发（覆盖文件数规则）**：DB schema / 认证逻辑 / API 契约 / 安全敏感路径 → 任意修改都算复杂，不论文件数
- 退出前验证：TDD 式验收 + 同步运行 Base check-list（双保险）
  - **修改了测试文件时 TDD 强制**，不可降级到 checklist
  - **架构/安全变更时也强制 TDD**（即使没改测试文件），防止绕路
  - 未修改测试文件时，TDD 优先但可降级
- 加入 claude-next 数据采集点（每次执行后记录决策和上下文）

**风险与缓解**:
| 风险 | 缓解 |
|:----|:-----|
| 模板全去掉 → 设计漂移 | 保留最小模板：HARD-GATE + 任务复杂度判断 + AC 清单 |
| TDD 不可确定性执行 | TDD 优先，失败时降级回 Base check-list（双模式） |

### 2. Oracle 增强（P1）

**当前**: oracle_agent.py 用 DeepSeek-V4-Flash

**Enhance 增强**:
- Oracle 双审使用高阶模型（Opus/GPT），配置文件可选模型
- 加入架构建议模式 — 不仅 ACCEPT/REJECT，附加重构建议
- `_is_autonomous_mode()` 已支持无人模式

**风险**: 高阶模型 API 可能限流 → 降级到 Base 的 DeepSeek-V4-Flash Oracle

### 3. 飞轮系统（Flywheel）（P2）

**目标**: AI 越用越懂项目

**实现**:
- 每次任务完成后采集三数据：决策日志 → .error-dna → .claude-next.md → anti-patterns
- **写 kernel.md 必须有验证门禁**：采集→模型提炼→人工确认（HITL）→验证器→写入
- token 预算限制：.claude-next.md 不超过 2K tokens，.error-dna 不超过 1K tokens
- 升华管道：每日 cron → 高阶模型提炼 → 冲突检测 → HITL → kernel.md

**风险与缓解**:
| 风险 | 缓解 |
|:----|:-----|
| 反馈循环污染 kernel.md | HITL 门禁 + 验证器（禁止新写入含语法错误/矛盾）|
| 上下文膨胀 | 每数据源 token 预算硬上限 |
| 低频项目学习慢 | 每次任务执行后都采集，不依赖 cron |

### 4. AI 资产化管线（P3）

**实现**:
- 三数据源 + token 预算：
  - `.claude-next.md` ≤ 2K tokens（正向知识）
  - `.error-dna` ≤ 1K tokens（错误模式）
  - `anti-patterns` ≤ 1K tokens（无效模式）
- 每周 cron 聚合 → 高阶模型 review → 冲突检测 → HITL → kernel.md 升华
- 每月大清理：超预算数据归档到记忆宫殿

## 实施顺序与依赖

| Phase | 内容 | 依赖 | 工作量 | 关键交付 |
|:----:|:----|:----|:------:|:--------|
| **P0** | lx-goal Enhance 增强版 | Base lx-goal v1.5.1 | 小 | SKILL.md 增强版 |
| **P1** | Oracle 增强（高阶模型） | oracle_agent.py v2 | 中 | 模型配置 + 架构建议模式 |
| **P2** | 飞轮系统搭建 | P0 + P1 | 大 | 采集管线 + HITL 门禁 + 升华 cron |
| **P3** | AI 资产化管线 | P2 | 大 | token 预算 + 归档 + 宫殿同步 |

## 未采纳项（理由）

- **不使用外部 RAG/向量数据库**：纯 .md 文件系统，保持零依赖
- **不使用自动化全覆盖测试**：TDD 优先，降级到 check-list，保持务实

## 开放问题

1. P2 的 HITL 门禁是否需要 Boss 亲自审，还是可以自动化规则审？
2. Oracle 增强使用哪些高阶模型（Opus / GPT / 两者兼用）？
