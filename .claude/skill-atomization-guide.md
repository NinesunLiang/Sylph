# Skill 原子化架构指南

> **Carror OS — AI Native Developer Operating System**
>
> 版本: v6.1.9 | 最后更新: 2026-05-11

---

## 概述

本指南定义 lx-skills-v5 体系中的 Skill 原子化架构规范。所有 Skill 必须遵循此架构分层，确保可复用性、可维护性和跨 Skill 一致性。

---

## 一、三层架构规范

每个 Skill 遵循严格的**三层目录结构**：

```
skills/lx-{name}/
├── SKILL.md         ← 第一层：AI 判断层（必需）
├── scripts/         ← 第二层：确定性执行层（有固定逻辑时创建）
│   └── xxx.py       ← 纯 Python，exit code，JSON 输出
└── references/      ← 第三层：按需知识层（有大块结构化知识时创建）
    └── xxx.md       ← SKILL.md 写死加载时机
```

### 第一层：AI 判断层（SKILL.md）

- 包含 `name` / `description` / `when_to_use` 等元数据
- 声明本 skill 使用的通用节点、引用 Schema、状态机类型
- 编写可执行的 Step 流程，每个 Step 可读性优先
- 需要 AI 语义理解才能执行 → 留在 SKILL.md

### 第二层：确定性执行层（scripts/）

- 步骤固定、无需 AI 判断 → 放入 scripts/
- 纯 Python 实现，不允许 Node.js/Go 等运行时依赖
- 遵守 stdin JSON / stdout JSON / exit code 2 协议
- 退出码 `0` = 正常放行，`2` = 阻断/失败，`1` = 系统错误

### 第三层：按需知识层（references/）

- 大块结构化知识（>30 行）、按阶段加载 → references/
- 由 SKILL.md 显式控制加载时机，不自动注入

---

## 二、通用节点体系

Skill 通过复用 `.claude/nodes/` 下的通用节点来组装工作流，避免重复实现相同逻辑。

### 当前通用节点

| 节点 | 用途 |
|------|------|
| `target_resolver.md` | 从参数/git diff 解析扫描/审查目标 |
| `context_collector.md` | 收集项目框架/版本/惯例上下文 |
| `scanner.md` | 按规则集执行扫描 |
| `auto_fixer.md` | 自动修复 P0/P1 问题 |
| `verifier.md` | 修复后 re-scan 验证 |
| `gate_checker.md` | Gate 判定 |
| `report_generator.md` | 报告生成 |
| `behavior_rules.md` | 行为约束规则 |
| `interactive_prompt.md` | 引导式问答 |
| `orchestrator.md` | 多步骤编排 |
| `execute_node.md` | Step 执行节点 |
| `generator.md` | 内容生成节点 |
| `a_terminal.md` | A 终端（验收标准生成） |
| `b_terminal.md` | B 终端（验收执行） |

### 引用路径规范

从 `skills/lx-{name}/SKILL.md` 中引用：
- 通用节点：`../../nodes/{node_name}.md`
- 通用 Schema：`../../schemas/atomic/{schema_name}.yaml`
- task_sys 组件：`../../task_sys/{component}.md`

---

## 三、Schema 体系

`schemas/` 按四类目录组织：

| 目录 | 用途 |
|------|------|
| `atomic/` | 被 3+ Skill 复用的原子 Schema |
| `contract/` | 状态机契约（参考文档，非强制） |
| `input/` | 任务驱动输入 Schema |
| `output/` | 输出格式注册表 |

### 原子 Schema 清单

| Schema | 描述 |
|--------|------|
| `scan_target.yaml` | 扫描/审查/验证目标定义 |
| `severity.yaml` | 问题严重度分级 (P0-P3) |
| `finding.yaml` | 单个问题/发现项 |
| `scan_report.yaml` | 扫描/审查/验证报告 |
| `fix_record.yaml` | 修复记录 |
| `gate_result.yaml` | Gate 判定结果 |
| `context_summary.yaml` | 上下文收集摘要 |
| `verdict.yaml` | 最终判定（所有 Skill 通用） |

---

## 四、状态机类型

Skill 应声明其状态机类型，并说明是否引用 `orchestrator.md`：

| 类型 | 描述 | 示例 |
|------|------|------|
| **门禁型** | Gate 链 | lx-pre-commit, lx-pre-push |
| **私有 X 阶段** | 不引用 orchestrator.md | 需说明原因 |

---

## 五、原子化原则

### 1. 单一职责

每个 Skill 只做一件事，并且做好。如果一个 SKILL.md 包含多个不相关的领域逻辑，应拆分为多个 Skill。

### 2. Node 复用优先

发现两个 Skill 中有相同逻辑段 → 提取为通用节点放入 `.claude/nodes/`，而不是在两个 SKILL.md 中重复。

### 3. Node 独立性

每个节点可独立加载，不依赖执行顺序。节点的输入输出通过明确声明的 Schema 契约定义。

### 4. 零消费者清理

`registry.yaml` 中标注的零消费者 Schema/节点应被删除，保持体系精简。

### 5. 引用路径

所有跨 SKILL.md 的引用使用相对路径，确保文件移动后仍可解析：
- Skill → nodes: `../../nodes/{name}.md`
- Skill → schemas: `../../schemas/{category}/{name}.yaml`
- Skill → task_sys: `../../task_sys/{name}.md`

---

## 六、Skill 元数据规范

每个 SKILL.md 必须包含以下元数据（YAML frontmatter）：

```yaml
---
name: lx-{name}
version: v{version}
description: "{一句话描述技能范围}"
when_to_use: "{触发场景说明}"
argument-hint: "[参数提示]"
paths:
  - "*.{ext}"
harness_version: ">=1.1.0"
---
```

---

## 七、创建新 Skill 的流程

1. 复制 `.claude/skills/TEMPLATE.md` 到 `skills/lx-{name}/SKILL.md`
2. 替换所有 `{name}`、`{description}` 等占位符
3. 声明使用的通用节点（从现有 13 个节点中选取）
4. 声明引用的 Schema（从 `schemas/registry.yaml` 选择）
5. 编写本 Skill 私有的规则/检查集
6. 如有固定逻辑 → 按需创建 `scripts/xxx.py`
7. 如有大块知识 → 按需创建 `references/xxx.md`
8. 声明边界（不做什么），明确不越界
9. 在 `schemas/registry.yaml` 中注册本 Skill 为 Schema 消费者

---

## 八、Node 创建/升级原则

- 提取通用节点时，同时更新 `schemas/registry.yaml` 的消费者列表
- 新增节点需更新本文件「通用节点」清单
- 节点接口变更必须同步更新所有消费者 SKILL.md
- 销毁节点需确认零消费者
