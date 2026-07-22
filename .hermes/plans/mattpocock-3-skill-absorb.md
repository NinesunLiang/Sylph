# Matt Pocock 3 Skill 吸收方案 — CarrorOS Enhance

## 对齐分析

### 1. grill-with-docs → Enhance lx-goal Phase0 增强

| Matt 做法 | CarrorOS 现状 | 对齐 | 吸收方式 |
|:---------|:-------------|:----:|:--------|
| grill-me 然后自动写 ADR+词典 | Phase0 只澄清不写文档 | 部分 | **不重构**，加 Step7: 自动产出 ADR |
| ADR 条件: 难撤销/非直觉/真权衡 | 无 ADR 机制 | 兼容 | **条件一致接纳** |
| CONTEXT.md 结构 | kernel.md 已存在 | 不兼容 | **不照搬文件结构**，ADR 放 `.claude/references/adr/` |

**接纳**: 给 Enhance lx-goal Phase0 加"grill-with-docs"模式，Phase0 结束后自动产出 ADR（仅当符合 Matt 的三条件）。不重构 kernel.md 结构。

### 2. batch-grill-me → Enhance lx-goal Phase0 新模式

| Matt 做法 | CarrorOS 现状 | 对齐 | 吸收方式 |
|:---------|:-------------|:----:|:--------|
| 一轮问完所有前沿问题 | 一次一问逐分支 | 互补 | **新增 batch 模式**，高阶模型专用 |
| 设计树 + frontier 判定 | 决策链固定 | 兼容 | **接纳 frontier 算法**: 可问的先问，依赖未解的等下一轮 |
| sub-agent 查事实不同步阻塞 | 无此机制 | 兼容 | **接纳** — 高阶模型能做并行 |

**接纳**: Enhance lx-goal Phase0 支持两种模式——标准(一次一问)和 batch(一轮全部前沿)。新增 `--mode batch` 参数。高阶模型默认 batch 模式。

### 3. domain-modeling → 新建 lx-domain-modeling

| Matt 做法 | CarrorOS 现状 | 对齐 | 吸收方式 |
|:---------|:-------------|:----:|:--------|
| 主动挑战领域语言 | kernel.md 被动记录 | 互补 | **接纳** — 新增"语言挑战"意识 |
| ADR 三条件机制 | 无 | 兼容 | **接纳全盘** |
| ADR 放 docs/adr/ | `.claude/references/` | 不兼容 | **适配** → `.claude/references/adr/` |
| 每次解决立刻写 CONTEXT.md | kernel.md 不可自改 | 不兼容 | **不接纳** — kernel.md 冻结规则不可破 |

**接纳**: 新建 `lx-domain-modeling` skill，含语言挑战 + ADR 机制。ADR 写到 `.claude/references/adr/`。不写 kernel.md（冻结规则），ADR 只作为参考引用。

## 实施计划

### Step 1: lx-goal Enhance 增强（batch 模式 + grill-with-docs）

改 `.claude/skills/lx-goal/SKILL.md`:
- Phase0 支持 `--mode batch|standard` 
- Batch 模式: frontier 算法一轮全问
- Standard 模式: 维持现状（一次一问）
- 退出前加 Step7: 自动产出 ADR（条件满足时）

文件变化: 1 个文件

### Step 2: 新建 lx-domain-modeling

创建 `.claude/skills/lx-domain-modeling/SKILL.md`:
- 语言挑战规则
- ADR 三条件 + 模板
- ADR 放 `.claude/references/adr/`
- ADR-FORMAT.md 从 Matt 适配

参考: domain-modeling + writing-great-skills 的 ADR 理念

文件变化: SKILL.md + references/adr/ADR-FORMAT.md

### Step 3: 同步到 Base 版（仅兼容部分）

Base 只吸收:
- ADR 三条件机制（不吸收 ADR 自动产出）
- 不吸收 batch 模式（中低阶模型不适合）
- lx-domain-modeling 可简化版放在 Base

### 不接纳项（理由）
- CONTEXT.md → kernel.md 不可自改
- 多 CONTEXT 地图 → 单 kernel.md 足够
- 每次立即写 → kernel.md 冻结规则

## 风险

| 风险 | 缓解 |
|:----|:-----|
| ADR 文件膨胀超过 token 预算 | 按条件限制（三条件齐才写 ADR） |
| Batch 模式一次问太多 | 限制 frontier ≤ 5 问题/轮 |
| 语言挑战造成噪声 | 仅在明确矛盾时触发 |
