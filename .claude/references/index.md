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
| `SOUL.md` | 英文哲学版（SUPERSEDED 指针，唯一真相源为 `philosophy.md`） |
| `SUBAGENT.md` | SubAgent 契约 |
| `anti-patterns.md` | 已知反模式库（飞轮自动补充） |
| `current-task-architecture.md` | 任务架构基线（2026-07-28） |
| `evaluation-framework.md` | 评分框架（C1-C9/E1-E8/治理/UX） |
| `fallback-matrix.md` | 降级矩阵 |
| `feature-registry.yaml` | 功能注册表 |
| `gate-rules.yaml` | Gate 规则 |
| `invariants.md` | 12 条系统不变量 [内部自检，非行业标准] |
| `oracle-spec.md` | Oracle 门禁规格 |
| `philosophy.md` | 决策链哲学 |
| `skill-atomization-guide.md` | Skill 原子化指南 |

## ADR

| 编号 | 标题 | 摘要 |
|------|------|------|
| 0001 | `.omc/` 作为 AI 唯一写入域 | AI 读取 `.claude/`，写入 `.omc/`，实现读写分离与审计 |
| 0002 | Token + Lock 双层任务生命周期 | `token.json` 存元数据 + lock 文件保并发安全，零外部依赖 |
| 0003 | VerifyGate 证据等级体系 | E3(exit=0) > E2(assert) > E1(confirm) > E0(rejected)，防虚假完成 |
| 0004 | Oracle 双模型对抗审核 | Oracle-D(静态) + Oracle-V(动态) 独立运行后交叉校验 |
| 0005 | Goal 模式自主执行 + skip-risk 安全阀 | L1 硬边界/L2 跳过记录/L3 人工审批，7 步闭环执行 |

新增架构决策时在 `adr/` 下创建文件并按模板格式填写。
