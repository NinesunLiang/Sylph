---
name: lx-ghost
version: v1.2.0
description: "幽灵模式 — 方向驱动的自主探索。一次前置澄清 → 全自动探索 → 退出报告。人类离开后 AI 自主探索修复。"
when_to_use: "Use when user says 'ghost mode', '幽灵模式', '自主探索', 'lx-ghost', /lx-ghost"
model: sonnet
argument-hint: "[方向描述] [轮询间隔秒数=600] [过期小时=3]"
harness_version: ">=1.1.0"
status: stable
role: "Direction-driven autonomous exploration — single briefing, zero interruptions"
execution_mode: stepwise
triggers:
  - "/lx-ghost"
---

# lx-ghost — 方向驱动自主探索

> **一次前置澄清 → 全自动探索 → 退出报告。人类在窗口期确认方向后离开，AI 自主探索直到过期或方向达成。**

## 与 lx-goal 的区别

| | lx-goal | lx-ghost |
|---|---------|----------|
| 驱动方式 | 目标驱动（具体任务列表） | 方向驱动（开放探索） |
| 执行模式 | 逐项 task-done | 增量 poll 迭代 |
| 适用场景 | 可分解的具体目标 | 需持续探索改进的方向 |
| 每步粒度 | 子任务级 | 单步操作级 |

## 自主决策框架

与 lx-goal 共享同一框架：Philosophy → Iron Rules → Existing Practices → AI 自主判断。

## 危险操作裁决链

**Level 1: AGENTS.md 裁决** → **Level 2: Oracle 第三方审核（留痕）** → **Level 3: 人类裁决（最后手段）**

---

## Phase 0: 前置澄清窗口（唯一的人类交互）

### Step 0.1: 方向自检

AI 检查方向适合性：
- "探索/扫描/修复/迭代" 等增量关键词 → ghost mode
- "分析/报告/评估/阅读" 等一次性关键词 → 建议 goal mode
- 区分不清 → 向人类说明理由，推荐模式

### Step 0.2: 扫描不确定项

范围边界、外部依赖、能力缺口、风险点、探索范围、成功信号。

### Step 0.3: 输出探索计划 + 不确定项清单

展示：探索方向、每轮操作粒度（一步一操作）、预计轮询间隔、已识别风险、Q 项。回复 "开始" 激活。

### Step 0.4: 激活

人类确认后激活，开始轮询。从此不再询问任何问题。

---

## 全自动轮询

间隔默认 600s，最小 30s，不可为 0。

每轮 poll 全自动：
1. 读 lx-ghost.json 确认方向
2. 方向漂移自检 → 偏离则修正，完全漂移则停用
3. **每轮只做一步** — 不并行 agent，不做大规模分析
4. 危险 → 走裁决链；歧义 → 自主判断
5. 更新状态

### Ghost + 执行引擎路由

Ghost 的增量 poll 天然适合 stepwise 模式。但发现可并行子任务时，可调用 race：

```
每轮 poll
  │
  ├─ 发现独立同构子任务（如"批量改 5 个文件的 import"）
  │     → 临时 spawn lx-race 并行处理 → 收集结果 → 继续下一轮 poll
  │
  └─ 单步操作（探索/修复/验证）
        → lx-stepwise 模式：隔离 → 定位 → 方案 → 修复 → 加固
```

> 每轮 poll 默认 stepwise 串行。只有当前轮明确发现可并行的独立子任务时才 spawn race。

---

## 常见场景自主处理

| 场景 | 自主处理 |
|------|---------|
| 方向漂移 | skip-risk 记录，修正方向 |
| 修复阻塞（3 次） | skip-risk，换方向继续 |
| Context Guard 阻断 | override + Bash |
| Permission Gate 拦截 | 走三级裁决链 |
| 发现范围外问题 | 记入附带发现 |
| 令牌过高 | 增加间隔或提前关闭 |

---

## 退出

自动过期 → 探索摘要 + 关闭。手动：`bash .claude/skills/lx-ghost/scripts/lx-ghost.sh off`

---

## 哲学

| # | 哲学 | 物化 |
|---|------|------|
| #3 | 先守护 | gate 降级 warn-only，危险走裁决链 |
| #4 | 没验证=没做 | 每轮 poll 报告状态 |
| #6 | 0 信任 | 危险记录 skipped_risks，Oracle 审核 |
| #2 | 少量大增益 | 只做方向相关的事 |
