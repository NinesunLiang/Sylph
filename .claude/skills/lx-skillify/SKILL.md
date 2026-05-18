---
name: lx-skillify
version: v1.0.0
description: "将自然语言描述转化为生产级 lx-* skill。6 阶段管道：澄清 → 分析 → 生成 → 支撑文件 → 验证 → 注册。"
when_to_use: "Use when user says 'skillify', '创建 skill', '生成 skill', 'new skill', /skillify, or describes a skill they want created."
argument-hint: "[自然语言描述，例如：'创建一个审查 Dockerfile 的 skill，检查安全漏洞和最佳实践']"
paths:
  - ".claude/skills/lx-*/SKILL.md"
harness_version: ">=1.1.0"
status: draft
role: "Skill 自动生成器 — 6 阶段管道：澄清→分析→生成→支撑文件→验证→注册"
execution_mode: stepwise
triggers:
  - "/skillify"
  - "skillify"
  - "创建 skill"
  - "生成 skill"
  - "new skill"
---

# lx-skillify — 技能自动生成器

> **一次澄清 → 全自动生成 → 验证 → 注册。** 用户描述需求，系统产出通过 11 条规则验证的完整技能。

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| interactive_prompt | `../../nodes/interactive_prompt.md` | Phase 0 澄清窗口 — 收集范围、触发器、需求 |
| target_resolver | `../../nodes/target_resolver.md` | 解析用户描述，确定目标技能域 |
| context_collector | `../../nodes/context_collector.md` | 收集现有技能模式、TEMPLATE.md、feature-registry 快照 |
| explore | `../../nodes/explore.md` | 探索技能目录，找 1-2 个最相似参考技能 |
| generator | `../../nodes/generator.md` | 基于 TEMPLATE.md + 参考技能生成 SKILL.md |
| report_generator | `../../nodes/report_generator.md` | 生成最终创建报告 |
| behavior_rules | `../../nodes/behavior_rules.md` | 全程行为约束 |

### 引用的通用 Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | 验证最终判定 |
| finding | `../../schemas/atomic/finding.yaml` | 验证发现的问题项 |
| scan_report | `../../schemas/atomic/scan_report.yaml` | 验证报告 |
| severity | `../../schemas/atomic/severity.yaml` | 验证问题严重度分级 |
| context_summary | `../../schemas/atomic/context_summary.yaml` | 技能上下文收集 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途 |
|------|------|------|
| 统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各阶段输出格式统一 |

### 状态机
本 skill 使用**私有 6 阶段状态机**，不引用 `orchestrator.md`。原因：skill 创建是单向管道，每阶段有严格输出契约作为下一阶段输入，非审查循环或门禁链。

```
CLARIFY → ANALYZE → GENERATE → CREATE_FILES → VALIDATE → REGISTER → REPORT
  ↑         ↑                        ↓ (fail, <3 retries)        ↓
  └─ re-prompt (max 2)               └────→ back to GENERATE ─────┘
```

降级路由：
- VALIDATE fail (retry < 3) → GENERATE（修复违规项）
- VALIDATE fail (retry ≥ 3) → DONE/blocked（报告失败原因，等待人工）
- CLARIFY 信息不足 → re-prompt（最多 2 次），仍不足 → 带部分信息继续

### 私有节点
本 skill 无私有节点。所有生成逻辑由 AI 通过 SKILL.md 语义判断驱动；`scripts/` 中的脚本仅处理确定性操作。

### 边界声明（不做什么）
| 不做的操作 | 原因 | 推荐替代 |
|-----------|------|---------|
| git commit/push | 硬边界 — 用户必须审查后手动提交 | 用户审查后 `git add` + `git commit` |
| 修改已有技能 | 超出范围，仅创建新技能 | 手动编辑已有 SKILL.md |
| 删除/重命名文件 | 无根据的破坏性操作 | 仅创建操作 |
| 生成虚构节点/Schema 路径 | 必须通过 lx-validate-skill | Phase 4 阻断虚构引用 |
| 修改 OMC 配置 | 由 OMC 框架管理 | 仅更新 feature-registry.yaml + skills-catalog.md |

---

## 执行流程

### Phase 0: 澄清（CLARIFY）

加载 `@../../nodes/interactive_prompt.md`。一次性提问（遵循 lx-goal "一次问清"原则）：

**Q1**: "这个 skill 要检查/生成/管理什么？请尽可能具体描述目的。"
**Q2**: "触发词是什么？用户说哪些词应调用此技能？（如：'/lx-my-skill'、'审查我的代码'）"
**Q3**: "输出应该是什么格式？（报告/修复/验证/自动修复？）"
**Q4**: "是否需要确定性脚本（纯 Python 可执行逻辑）？还是纯 AI 判断即可？"

**输出**: 结构化 `skill_spec`:
```json
{
  "name": "lx-{name}",
  "description": "...",
  "triggers": ["/lx-{name}", "..."],
  "scope": "...",
  "needs_scripts": false,
  "needs_references": false,
  "output_type": "report|fix|verify|generate"
}
```

### Phase 1: 分析模式（ANALYZE）

加载 `@../../nodes/target_resolver.md` + `@../../nodes/context_collector.md` + `@../../nodes/explore.md`。

执行序列：
1. 读取 `.claude/skills/TEMPLATE.md` — 获取规范格式
2. 探索 `.claude/skills/` — 按 `description` 和 `when_to_use` 语义相似度找 1-2 个最相似参考技能
3. 读取参考技能的完整 SKILL.md — 学习其节点选择、Schema 引用、状态机模式
4. 列出 `.claude/nodes/` 中所有可用节点（19 个）
5. 列出 `.claude/schemas/atomic/` 中所有可用 Schema（9 个）
6. 读取 `.claude/task_sys/unified_delivery_schema.md`

**节点选择规则**（按技能类型自动匹配）：
| 技能类型 | 必选节点 | 可选节点 |
|---------|---------|---------|
| 审查类 | behavior_rules, scanner, report_generator | auto_fixer, verifier, gate_checker |
| 生成类 | behavior_rules, generator, report_generator | context_collector, target_resolver |
| 门禁类 | behavior_rules, gate_checker, report_generator | scanner |
| 工作流类 | behavior_rules, context_collector, report_generator | interactive_prompt, explore |

**输出**: `analysis_result`:
```json
{
  "target_name": "lx-{name}",
  "skill_type": "reviewer|generator|gate|workflow",
  "reference_skills": [{"name": "...", "path": "...", "key_patterns": ["..."]}],
  "selected_nodes": ["behavior_rules", "scanner", "..."],
  "selected_schemas": ["verdict", "finding", "..."],
  "template_structure": "完整 TEMPLATE.md 的节结构"
}
```

### Phase 2: 生成 SKILL.md（GENERATE）

加载 `@../../nodes/generator.md`。

**生成规则**（严格按顺序）：

1. **Frontmatter** — 所有必填字段：`name`, `version: v1.0.0`, `description`, `when_to_use`, `argument-hint`, `harness_version: ">=1.1.0"`, `status: draft`, `execution_mode: stepwise`, `triggers`
2. **## 原子化声明** — 5 个子表，每个引用路径必须是 Phase 1 验证过的真实路径
3. **### 状态机** — 根据技能类型选择状态机模式并说明原因
4. **### 私有节点** — "本 skill 无私有节点"
5. **### 边界声明** — 至少 1 条"不做什么"
6. **## 执行流程** — Step 0 到 Step N，每步加载对应节点
7. **## 降级策略** — 主路径 vs 降级路径表
8. **## 错误恢复与中止条件** — 场景 + 处理表

**内容约束**：
- SKILL.md ≤ 300 行（超过触发 validate_skill.py 警告）
- 所有 `@../../nodes/` 引用必须解析到真实文件
- 所有 `../../schemas/atomic/` 引用必须解析到真实文件

**输出**: 完整 SKILL.md 内容字符串。

### Phase 3: 创建支撑文件（CREATE_FILES）

若 `skill_spec.needs_scripts == true`：
```bash
mkdir -p .claude/skills/lx-{name}/scripts
```
创建 `scripts/{logic}.py` — 纯 Python，`#!/usr/bin/env python3`，必须调用 `sys.exit()`，遵循 stdin JSON / stdout JSON / exit code 2 协议。

若 `skill_spec.needs_references == true` 或生成内容含 >30 行结构化知识：
```bash
mkdir -p .claude/skills/lx-{name}/references
```
创建 `references/{knowledge}.md` — 在 SKILL.md 中显式声明加载时机。

**产出目录结构**：
```
.claude/skills/lx-{name}/
  SKILL.md          ← Phase 2 产物
  scripts/          ← 条件创建（可为空目录）
  references/       ← 条件创建（可为空目录）
```

### Phase 4: 验证（VALIDATE）

确定性验证链（通过 `scripts/verify_and_register.py` 执行）：

```bash
# 步骤 4a：结构验证（11 条规则）
bash .claude/scripts/validate-skill.sh lx-{name}

# 步骤 4b：引用完整性验证
python3 .claude/scripts/validate_skill_refs.py
```

**验证门禁**：
- 任一验证失败 → 解析违规项 → 回到 Phase 2 修复 → 重新验证
- 最多 3 轮生成-验证循环
- 第 3 轮仍失败 → 标记 `blocked`，输出违规详情，等待人工介入

**输出**: `validation_result`:
```json
{
  "passed": true,
  "rounds": 2,
  "violations_fixed": ["R2: missing harness_version", "R4: missing 降级策略"],
  "warnings": ["SKILL.md 310 行，超过 300 行建议"]
}
```

### Phase 5: 注册（REGISTER）

加载 `@../../nodes/context_collector.md`。通过 `scripts/verify_and_register.py` 执行：

1. 读取 `.claude/feature-registry.yaml`
2. 在 `skills:` 段追加条目
3. 读取 `docs/guides/cn/skills-catalog.md`
4. 在合适的分类下追加行

**注册格式**：
```yaml
- name: lx-{name}
  type: {reviewer|workflow|gate|tester|orchestrator|analyzer}
  category: {quality|workflow|security|test|debug|infrastructure|automation}
  description: "{一句话描述，<80 字符}"
  enabled_by_default: true
```

### Phase 6: 报告（REPORT）

加载 `@../../nodes/report_generator.md`。

```
## /skillify 完成报告 ✅

### 创建内容
- 技能: lx-{name}
- SKILL.md: .claude/skills/lx-{name}/SKILL.md ({N} 行)
- 脚本: {列表或"无"}
- 引用: {列表或"无"}

### 验证结果
- 结构检查: {通过/失败} ({N} 违规已修复, {M} 警告)
- 引用检查: {通过/失败}
- 生成轮次: {N}

### 注册
- feature-registry.yaml: 已更新
- skills-catalog.md: 已更新

### 下一步
1. 审查 SKILL.md 内容
2. 手动 git add .claude/skills/lx-{name}/
3. 或用 /lx-{name} 立即测试
```

---

## 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 用户描述过于模糊 | 重新提问（最多 2 次） | 基于已有信息生成，标注"部分信息不足" |
| 找不到相似参考技能 | 使用 TEMPLATE.md 默认模式 | 手动指定参考技能名 |
| 验证失败（第 1-2 轮） | 自动修复违规项 → 重新验证 | 标记需要人工修复的违规项 |
| 验证失败（第 3 轮） | 停止，报告失败原因 | 输出违规详情 + 建议修复方向 |
| 注册时 feature-registry.yaml 不存在 | 报错 | 创建最小有效 registry 文件 |
| 技能名已被占用 | 提示冲突 | 建议替代名称（加后缀或变体） |
| lx-validate-skill 不可用 | 跳过自动验证 | 手动逐项检查 11 条规则 |

## 错误恢复与中止条件

| 场景 | 动作 |
|------|------|
| Phase 1 探索不到技能目录 | 报错 — 确认 `.claude/skills/` 存在 |
| Phase 2 生成内容引用虚构路径 | Phase 4 阻断 — 回 Phase 2 修复 |
| Phase 4 验证脚本不存在 | 降级 — AI 手动逐项检查 |
| Phase 5 注册文件被锁 | 等待锁释放 → 重试（最多 3 次） |
| 用户在 Phase 0 后中止 | 保留已收集的 skill_spec，下次可恢复 |

---

## 与 lx-goal 集成

Phase 1-5 设计为在 lx-goal 无人值守模式下运行：
- Phase 0 作为"人类窗口期"一次性完成
- 确认后 lx-goal 激活，Phase 1-6 无中断执行
- 验证失败自动循环修复（max 3）
- git commit 为硬边界 — 技能产出后不提交，留给用户审查
