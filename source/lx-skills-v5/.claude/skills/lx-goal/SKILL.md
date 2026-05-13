---
name: lx-goal
version: v1.1.0
description: "目标模式 — 目标驱动的自主执行。给 AI 一个具体目标，AI 执行到完，完成后输出报告。"
when_to_use: "Use when user says 'goal mode', '目标模式', 'lx-goal', '无人值守', '自主执行', /lx-goal"
model: sonnet
argument-hint: "[目标描述] [过期小时=6]"
harness_version: ">=1.1.0"
role: "Goal-driven autonomous execution mode with task tracking and reporting"
execution_mode: stepwise
triggers:
  - "/lx-goal"
---

# lx-goal — 目标驱动自主执行

> **一次确认 → 全自动执行**：AI 出执行计划 → 用户确认 1 次（方向策略）→ 之后全权执行到完，不请求任何中间确认。
> 遇到风险记录到 `skipped_risks` 继续执行，不暂停。全部完成后自动 report + off。

## 立即执行（本 skill 加载后立刻执行）

本 skill 加载时立即检查调用参数：

**有参数** → 执行以下完整流程：

### Step 1: 分解 + 1 次人工确认
检测用户消息中是否有步骤列表标记：

```
checklist:  - [ ] / - [] / * [ ] / []
编号列表:  1. / 1) / 第一、第二 / Step 1 / Phase 1
├─ 有 → 跳过 AI 分解，直接使用用户的列表作为子任务
└─ 无 → AI 将目标拆解为可验证子任务列表
```

子任务每项必须包含验收条件、依赖关系、预估复杂度。
**输出方案后等待用户确认。** 确认通过后进入全自动执行阶段。

```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh on "参数1" [参数2]
```

### Step 2: 全自动执行（确认后不再停顿）
从无依赖子任务开始，逐项实现，**全程不再请求用户确认**：

- 每完成一项用 task-done 标记
- 遇到危险操作 → skip-risk 记录，**不中断，继续执行**
- 遇到歧义 → 自行决策，记录到 skipped_risks，**不暂停问人**
- 遇到失败 → 自动重试（最多 3 次），超过才升级用户

```bash
# 每完成一项
bash .claude/skills/lx-goal/scripts/lx-goal.sh task-done "子任务 N: 完成了什么"
# 跳过风险（不中断执行）
bash .claude/skills/lx-goal/scripts/lx-goal.sh skip-risk "跳过: 原因"
```

### Step 3: 自动完成
所有子任务完成后**自动**输出报告 + 关闭：
```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh report
bash .claude/skills/lx-goal/scripts/lx-goal.sh off
```

**无参数** → 先问用户目标，然后从 Step 1 开始。

---

## 执行流程（全自动执行阶段）

确认后全自动执行，不暂停、不请求确认：

### 1. 逐项执行
从无依赖子任务开始逐项实现，每完成一项标记一次：
```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh task-done "子任务 A: 已完成"
```

### 2. 遇到风险
危险操作自动记录到 skipped_risks，**不中断**继续执行：
```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh skip-risk "跳过: rm -rf /tmp/cache"
```

### 3. 失败时自动重试
```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh retry
```
最多 3 次，超过升级用户。

### 4. 完成报告 + 自动关闭
所有子任务完成后自动输出报告 + 关闭模式：
```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh report
bash .claude/skills/lx-goal/scripts/lx-goal.sh off
```

---

## 脚本引用

完整子命令参见 `.claude/scripts/lx-goal.sh`（直接运行查看帮助）。

| 子命令 | 作用 |
|--------|------|
| `on "目标" [小时]` | 激活目标模式 |
| `off` | 关闭 |
| `status` | 查看状态 |
| `task-done "描述"` | 标记任务完成 |
| `skip-risk "描述"` | 记录跳过的风险 |
| `retry` | 重试计数+1 |
| `report` | 生成执行报告 |
| `poll` | 轮询入口 |
| `set <key> <value>` | 修改 JSON 字段 |

---

## 哲学

| # | 哲学 | 物化 |
|---|------|------|
| #3 | 先守护 | gate 降级为 warn-only，不硬阻断 |
| #4 | 没验证=没做 | task-done 逐项确认 + report |
| #6 | 0 信任 | 危险操作记录 skipped_risks |
| #7 | 文档优先 | 完成时自动生成报告 |

---

## 错误恢复

| 场景 | 处理 |
|------|------|
| 目标不明确 | 暂停，让用户补充 |
| 修复阻塞（3 次） | `skip-risk` 记录后继续 |
| 与 ghost 冲突 | 先关另一个再开 |
