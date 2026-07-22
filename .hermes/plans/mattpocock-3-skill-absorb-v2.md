# Matt Pocock 3 Skill 吸收方案 v2 — CarrorOS Enhance

## 设计原则

1. **不破内核冻结** — kernel.md 不可自改
2. **不增治理复杂度** — 吸收物必须低于当期治理模板的认知负载
3. **只做 Enhance 专有** — 不兼容 Base 的不下放
4. **三条件门禁** — ADR 产出条件：难撤销 + 非直觉 + 真权衡

---

## 1. batch-grill-me → lx-goal Phase0 batch 模式

### 场景
高阶模型（Opus/GPT）在 Phase0 澄清时，用 batch 模式一轮问完所有前沿问题，而不是逐条沟通。

### 实现

lx-goal 新增 `--mode batch` 参数：

```
Phase0 入口:
  standard（默认）: 一次一问，逐分支 — 同 Base
  batch（Enhance） : 前沿算法，一轮多问
```

**batch 模式规则**:
1. 构建设计树：每个决策标记依赖关系
2. 每轮 frontier = 所有依赖已解决的决策
3. 每轮最多 5 个问题，按依赖关系排序，每个问题附带"为什么问这个"
4. sub-agent 查事实不同步阻塞 — 但产出结论前必须等待所有 sub-agent 返回（sync barrier）
5. 用户回答后再轮询下一轮
6. frontier 为空时完成

### 关键改动
- lx-goal SKILL.md Phase0 入口新增模式判断
- 不涉及 hooks/scripts 改动（纯 prompt 模式切换）

---

## 2. grill-with-docs → Phase0 自动 ADR 产出

### 场景
Phase0 完成后，自动判断本次澄清有没有值得记录的架构决策。

### 实现

在 Phase0 末尾（自审后、激活前）新增 ADR 检查：

```
phase0_done → 判断本次有无 ADR 需求 → 
  有三条件之一 → 写 .claude/references/adr/NNNN-title.md
  无 → 静默跳过
```

**ADR 三条件**（三个全是才写）:
1. **难撤销** — 改了之后后悔成本高
2. **非直觉** — 未来读者会问"为什么这么干"
3. **真权衡** — 有明确的替代方案并做了选择

**ADR 自动索引**:
`.claude/references/adr/INDEX.md` 自动更新：
```markdown
# ADR Index
- 0001-event-sourced-orders.md — 事件溯源 vs 状态机, 2026-07-22
- 0002-postgres-for-write-model.md — PG vs DynamoDB, 2026-07-22
```

**启动加载**:
`index.md` 增加一条：
```
@.claude/references/adr/INDEX.md  <!-- 架构决策记录，自动加载 -->
```

不修改 kernel.md。ADR INDEX 通过 index.md 引用链加载。

### 关键改动
- lx-goal SKILL.md Phase0 新增 Step 7.5 ADR check
- `.claude/references/adr/INDEX.md` 自动更新机制
- `index.md` 加一行引用
- 新增 `.claude/references/adr/ADR-FORMAT.md` 模板

---

## 3. domain-modeling → 新建 lx-domain-modeling

### 场景
Enhance 版需要主动管理和打磨领域语言，而不是被动记录。

### 实现

**.claude/skills/lx-domain-modeling/SKILL.md**:

核心 3 条规则：

**规则 1: 语言挑战 — 触发算子**
当发现以下情况时必须触发：
- 一词多义：同一个名词在不同 context 下解释不同
- 多词一义：不同组件/模块指代同一个实体
- 与 kernel.md 冲突：当前用语与 kernel.md 定义的术语不同

**规则 2: ADR 记录 — 三条件门禁**
仅当三个条件都满足时写 ADR（同 grill-with-docs）。ADR 放 `.claude/references/adr/`。

**规则 3: 不做的事**
- 不修改 kernel.md
- 不创建 CONTEXT.md（用 kernel.md + index.md 替代）
- 不是 spec 文档，只记录领域语言决策

### 引用关系
`index.md` 新增：
```
@.claude/skills/lx-domain-modeling  <!-- 领域语言管理，Enhance 专有 -->
```

---

## 不接纳项汇总

| 不接纳 | 理由 |
|:-------|:-----|
| CONTEXT.md 文件结构 | CarrorOS 用 kernel.md，冻结规则不可破 |
| 每次解决立刻写 kernel.md | 冻结规则 |
| Batch 模式给 Base | 中低阶模型不适合 |
| multi-context MAP | 单个 kernel.md 足够 |
| docs/adr/ 目录 | 用 `.claude/references/adr/` |

---

## 实施步骤

| Step | 内容 | 文件 | 工作量 |
|:----:|:----|:----|:------:|
| 1 | lx-goal SKILL.md 新增 batch 模式 Phase0 | `.claude/skills/lx-goal/SKILL.md` | 小 |
| 2 | lx-goal SKILL.md 新增 ADR check step | `.claude/skills/lx-goal/SKILL.md` | 小 |
| 3 | ADR 模板 | `.claude/references/adr/ADR-FORMAT.md` | 小 |
| 4 | index.md 加载 ADR INDEX | `.claude/index.md` | 极小 |
| 5 | 新建 lx-domain-modeling | `.claude/skills/lx-domain-modeling/SKILL.md` | 中 |
| 6 | 同步到 Base | 仅 domain-modeling 简化版 | 小 |

## 风险与缓解

| 风险 | 缓解 |
|:----|:-----|
| ADR 写后不读 | index.md 加载 + 启动自动索引 |
| Batch 模式问题发散 | frontier ≤ 5 + 按依赖排序 + 说明意图 |
| ADR 膨胀超 token 预算 | 三条件门禁 + ADR INDEX 只保持标题摘要 |
| 语言挑战噪声 | 仅触发算子（一词多义/多词一义/冲突）激活 |
