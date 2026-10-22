# references/ — 公共资源文档

> 存放 CarrorOS 设计文档、架构决策、模板、规则等可复用资源。
> subdir 索引由各子目录的 `INDEX.md` 管理。

## 目录结构

| 目录 | 用途 | 入口 |
|------|------|------|
| `adr/` | 架构决策记录 | `INDEX.md` |
| `archived/` | 已归档旧文档 | `loading_matrix.md`, `mechanism_evals.md`, `design-docs/`（历史迭代，ADR0017） |
| `design-docs/` | 设计文档（分阶段编号，大编号优先） | `13-headless-lightweight-actions.md`（当前活文档）；历史归档于 `archived/design-docs/` |
| `templates/` | 模板（handoff-capsule, stepwise-cards 等） | 直接引用 |

## 独立文件

| 文件 | 用途 |
|------|------|
| `ai_self_decision.md` | 打断路由：不可逆/越权/架构调整先告知再打断，其余自决 |
| `anti-patterns.md` | 已知反模式库（飞轮自动补充，≤40 行防膨胀闸） |
| `current-task-architecture.md` | 任务架构基线（2026-07-28） |
| `evaluation-framework.md` | 评分框架（C1-C9/E1-E8/治理/UX） |
| `feature-registry.yaml` | 功能注册表 |
| `gate-rules.yaml` | Gate 规则（pre_action_gate.py 数据驱动配置） |
| `governance-philosophy.md` | 治理哲学：疏导 + 兜底原则（门分类为 2026-08-30 时点快照） |
| `headless-permissions.md` | Headless 权限契约（apply_permissions.py 工作流） |
| `invariants.md` | 16 条系统不变量 [内部自检，非行业标准] |
| `oracle-spec.md` | Oracle 门禁规格 |
| `philosophy.md` | 裁决链落地实体映射 + 禁止事项（裁决链原文 = AGENTS.md §灵魂） |
| `redirect-mechanism.md` | REDIRECT 机制规格 |
| `runbook.md` | 运维手册 |
| `sandbox-long-task-pattern.md` | 沙箱内长任务模式（分批 / 后台 / 轮询） |
| `scorecard.md` | 评分对账卡（/lx-goal 循环对账真相源） |
| `skill-atomization-guide.md` | Skill 原子化指南 |

## ADR

以 `adr/INDEX.md` 为单一真源（当前 15 条，0001-0020 缺 0007-0011，编号以 INDEX.md 为准不写死）；本表不再复述条目清单，防双源漂移。新增架构决策时在 `adr/` 下创建文件并登记 `INDEX.md`。
