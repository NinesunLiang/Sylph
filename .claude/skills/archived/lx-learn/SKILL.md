---
name: lx-learn
version: v1.0.0
description: "Skill 元技能 — 生成/提取/编辑/优化 skill。统一入口覆盖 lx-learner + lx-skillify，新增编辑和合并能力。"
when_to_use: >
  Use when user says 'learn', 'learn skill', '生成 skill', '创建 skill', '编辑 skill', '合并 skill',
  '提取 skill', '优化 skill', 'skillify', 'learner', '从对话中学习', 'from conversation',
  '/learn', or when you detect repeated workflow patterns. 统一入口，自动路由到对应模式。
argument-hint: >
  <模式>: <描述>
  - create: 创建新 skill
  - extract: 从对话提取
  - edit: 编辑已有 skill
  - merge: 合并多个 skill
  - optimize: 优化/重构 skill
harness_version: ">=6.3.0"
status: draft
role: "Skill 元技能 — 负责所有 skill 生命周期操作：创建、提取、编辑、合并、优化"
execution_mode: stepwise
triggers:
  - "/learn"
  - "learn"
  - "learn skill"
  - "生成 skill"
  - "创建 skill"
  - "编辑 skill"
  - "合并 skill"
  - "优化 skill"
  - "提取 skill"
  - "从对话中学习"
---
# lx-learn — Skill 元技能

> **统一 skill 生命周期管理。** 五种模式：create（生成）、extract（提取）、edit（编辑）、merge（合并）、optimize（优化）。适应性优化：高阶模型直接生成，低阶模型逐步引导。

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| target_resolver | `../../nodes/target_resolver.md` | 解析用户意图（路由到模式） |
| context_collector | `../../nodes/context_collector.md` | 收集已有技能注册表、模板、节点/Schema |
| explore | `../../nodes/explore.md` | 查重、参考已有技能、探索对话模式 |
| interactive_prompt | `../../nodes/interactive_prompt.md` | 收集用户输入（模式不明确时） |
| generator | `../../nodes/generator.md` | 生成/编辑 skill 内容 |
| scanner | `../../nodes/scanner.md` | 扫描对话日志检测重复模式 |
| auto_fixer | `../../nodes/auto_fixer.md` | 自动修复验证失败 |
| verifier | `../../nodes/verifier.md` | 验证生成/修改结果 |
| report_generator | `../../nodes/report_generator.md` | 输出模式报告 |
| behavior_rules | `../../nodes/behavior_rules.md` | 硬边界约束 |

| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |
| finding | `../../schemas/atomic/finding.yaml` | 发现问题 |
| scan_report | `../../schemas/atomic/scan_report.yaml` | 扫描报告 |
| severity | `../../schemas/atomic/severity.yaml` | 严重度 |
| context_summary | `../../schemas/atomic/context_summary.yaml` | 上下文摘要 |
| gate_result | `../../schemas/atomic/gate_result.yaml` | 门禁判定（如适用） |

### 引用的外部组件

| 组件 | 路径 | 用途 |
|------|------|------|
| 统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 输出统一格式 |
| 上下文守卫 | `../../task_sys/context_guard.md` | 长会话上下文总结 |
| SKILL.md 模板 | `../TEMPLATE.md` | 生成新 skill 的模板基准 |
| skill 生成提示模板 | `../../references/skill_generation_prompts.md` | 按类型生成规则 |
| lx-validate-skill | `../lx-validate-skill/SKILL.md` | 验证新 skill 合规 |

### 内部 references（按需加载）

| 文件 | 加载时机 |
|------|---------|
| `references/phase-create.md` | create 模式 |
| `references/phase-extract.md` | extract 模式 |
| `references/phase-edit.md` | edit 模式 |
| `references/phase-merge.md` | merge 模式 |
| `references/phase-optimize.md` | optimize 模式 |
| `references/adaptive-generation.md` | 适应性优化规则 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
                    ┌─> EXTRACT(skillify+learner)
                    |
INPUT -> ROUTE ----+-> CREATE (from description)
                    |
                    +-> EDIT (existing skill)
                    |
                    +-> MERGE (2+ skills -> 1)
                    |
                    +-> OPTIMIZE (refactor/clean)

每种模式内部遵循自身子状态机（见对应 references）。
```

### 子状态机

**CREATE**: `CLARIFY -> ANALYZE -> GENERATE -> CREATE_FILES -> VALIDATE -> REPORT`
**EXTRACT**: `DETECT -> PROPOSE -> GENERATE -> VALIDATE -> DOCUMENT -> REPORT`
**EDIT**: `LOAD -> ANALYZE_CHANGE -> EDIT -> VALIDATE -> REPORT`
**MERGE**: `LOAD_ALL -> ANALYZE_OVERLAP -> DESIGN_MERGE -> GENERATE_MERGE -> VALIDATE -> REPORT`
**OPTIMIZE**: `LOAD -> ANALYZE_ISSUES -> OPTIMIZE -> VALIDATE -> REPORT`

## 适应性优化

> 本 skill 根据当前模型能力自动调整生成策略。

| 模型类型 | 策略 |
|----------|------|
| 高阶模型（gpt-5.5+ / deepseek-v4-pro / gemini 3+ / sonnet 5+） | 一次性生成完整的 SKILL.md（含原子化声明、边界声明、完整执行流程）。理解抽象意图，减少澄清轮次。 |
| 中阶模型 | 分步生成：先 frontmatter -> 再主体执行流程 -> 最后边界声明。每步可审阅修改。 |
| 低阶模型 | 严格按 TEMPLATE.md 填空式生成。逐段询问用户确认。 |

优先级规则：**正确性 > 自动生成**。高阶模型仍应验证生成结果。

## 边界声明

| 不做的操作 | 原因 | 推荐替代 |
|-----------|------|---------|
| git commit/push | 硬边界 | 用户手动执行 |
| 删除技能目录 | 破坏性操作 | 移到 `archived/` |
| 修改非 skill 文件 | 超出范围 | 手动操作 |
| 虚构不存在的节点/Schema | 破坏架构 | 指定已有节点 |
| 从对话推断凭据/密钥 | DLP 安全 | 交给 lx-varlock |
| 自动生效（需用户确认） | 每次操作都必须用户批准 | - |

## 通用执行流程

### Step 0: 路由到模式

检测用户意图 -> 路由到 5 种模式之一：

1. **CREATE**: 用户说"生成/创建 skill" + 自然语言描述
2. **EXTRACT**: 用户说"从对话中学习/提取" 或 AI 检测到重复模式（3+ 次）
3. **EDIT**: 用户说"修改/编辑已有 skill"
4. **MERGE**: 用户说"合并 skill" 或检测到高重叠（需要确认）
5. **OPTIMIZE**: 用户说"优化/重构/清理 skill"

**路由规则**：
- 用户明确指定模式 -> 直接进入
- 仅说 "skill/learn" -> 交互式询问
- 从对话自动触发 -> 检查置信度 >=5 才建议

### CREATE 模式

#### Phase 1: 澄清（CLARIFY）

加载 `@references/phase-create.md`。

4 问澄清窗口：
1. Skill 做什么？（一句话描述）
2. 输入输出是什么？
3. 适用文件类型 / 场景？
4. 需要哪些节点和 Schema？

高阶模型：减少到 1-2 问，从描述中自动推断。

#### Phase 2: 分析（ANALYZE）

探索已有技能 -> 参考技能选择 -> 节点/Schema 选择。
加载 `@../../references/skill_generation_prompts.md` 按类型选择生成规则。

#### Phase 3: 生成（GENERATE）

加载 `@../TEMPLATE.md` 模板基准。
按模板生成 SKILL.md（<=300行）。

#### Phase 4: 创建文件（CREATE_FILES）

按 TEMPLATE.md 三层规范创建目录结构：
- `scripts/`（有固定逻辑时创建）
- `references/`（有大块知识时创建）

#### Phase 5: 验证（VALIDATE）

```
python3 ../lx-validate-skill/scripts/validate_skill.py lx-{name}
```

通过 -> Phase 6。失败 max3 轮 -> 暂停输出详情。

#### Phase 6: 报告（REPORT）

输出创建报告（skill 位置、文件结构、验证结果、注册信息）。

### EXTRACT 模式

加载 `@references/phase-extract.md`。

#### Phase 1: 检测（DETECT）

扫描对话上下文 -> 模式评分（0-10）。
- 重复模式 3+ 次 -> 置信度评分
- 评分 >=5 -> 可提取

#### Phase 2: 提议（PROPOSE）

查重 -> 展示证据 -> 用户确认。

#### Phase 3-5: 生成 -> 验证 -> 文档

同 CREATE 模式的 Phase 3-5，但附加 conversation_provenance 文档。

#### Phase 6: 报告

输出提取报告（模式证据、生成 skill、验证结果、来源文档）。

### EDIT 模式

加载 `@references/phase-edit.md`。

#### Phase 1: 加载（LOAD）

读取已有 skill 的 SKILL.md -> 展示当前结构。

#### Phase 2: 分析变更（ANALYZE_CHANGE）

理解用户修改请求 -> 评估变更影响。

#### Phase 3: 编辑（EDIT）

按请求修改 SKILL.md（保持 frontmatter / 原子化声明 / 执行流程完整）。

#### Phase 4: 验证

```
python3 ../lx-validate-skill/scripts/validate_skill.py lx-{name}
```

通过 -> Phase 5。失败 -> 回 Phase 3（max 2 轮）。

#### Phase 5: 报告

输出编辑报告（变更摘要、新旧对比、验证结果）。

### MERGE 模式

加载 `@references/phase-merge.md`。

#### Phase 1: 加载所有（LOAD_ALL）

读取要合并的多个 SKILL.md。

#### Phase 2: 分析重叠（ANALYZE_OVERLAP）

对比各 skill 的：触发词、执行流程、边界声明、节点引用。

#### Phase 3: 设计合并方案（DESIGN_MERGE）

输出合并方案：保留哪些、删除哪些、重命名哪些。

#### Phase 4-6: 生成 -> 验证 -> 报告

同 CREATE 模式 Phase 3-6。

### OPTIMIZE 模式

加载 `@references/phase-optimize.md`。

#### Phase 1: 加载（LOAD）

读取目标 skill 的完整内容。

#### Phase 2: 分析问题（ANALYZE_ISSUES）

检查：frontmatter 完整性、节点引用完整性、边界声明、执行流程一致性、冗余内容。

#### Phase 3: 优化（OPTIMIZE）

按分析结果优化：补充缺失、删除冗余、重构流程。

#### Phase 4-5: 验证 -> 报告

同 EDIT 模式 Phase 4-5。

## 错误恢复与中止条件

| 场景 | 处理 |
|------|------|
| 模式无法确定 | 交互式询问用户 |
| 无目标文件（edit/merge） | "不存在"报告 |
| 验证失败 max 轮次 | 暂停，请求人工介入 |
| 技能名冲突 | 提示冲突，建议替代名 |
| 从对话提取置信度 <5 | 标记附带发现，建议手动 create |
| 合并时无法自动决策 | 暂停，展示方案给用户选择 |
| optimize 无改进空间 | "已是最优"报告 |
