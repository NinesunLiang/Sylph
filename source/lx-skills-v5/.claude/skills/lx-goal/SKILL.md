---
name: lx-goal
version: v1.2.0
description: "目标模式 — 一次前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。"
when_to_use: "Use when user says 'goal mode', 'lx-goal', '无人值守', '自主执行', /lx-goal"
model: sonnet
argument-hint: "[目标描述] [过期小时=6]"
harness_version: ">=1.4.0"
status: stable
role: "Goal-driven autonomous execution — single briefing, zero interruptions, final report"
execution_mode: stepwise
triggers:
  - "/lx-goal"
---

# lx-goal — 目标驱动自主执行

> **一次前置澄清 → 全自动执行 → 退出报告。人类在窗口期回答所有问题后离开，AI 不再请求任何交互。**

## 执行模型

```
人类窗口期（Phase 0）        AI 全自动执行（Phase 1→N）       人类回归（退出报告）
澄清所有不确定项              不暂停 · 不提问 · 不问人          结构化报告待审阅
确认目标+边界+资源             遇到卡点 → 分类处理 → 继续        已完成 / 已跳过 / 需人类
人说"开始" → 进入全自动       AI 自主决策直到完成或过期         人类按卡点清单逐项处理
```

## 子任务执行引擎路由

Goal mode 拆解出子任务后，自动选择执行引擎：

```
子任务列表
  │
  ├─ 全部独立 + 同构 + 简单 → lx-race（并行多 agent 同时认领）
  │
  ├─ 有依赖 + 高复杂度 + 根因不明 → lx-stepwise（串行逐步攻坚）
  │
  └─ 混合 → 独立简单任务 spawn race，复杂任务走 stepwise
```

| 引擎 | 触发条件 | 模式 |
|------|---------|------|
| **lx-race** | 子任务无相互依赖、同类操作（如批量改 5 个文件）、每项独立可验证 | 并行快处理 |
| **lx-stepwise** | 子任务有依赖链、根因不明、跨模块修改（>3 文件）、之前修复失败过 | 串行深攻坚 |

> 路由决策在 Phase 0.3（输出执行计划）时完成，写入 executor.md。

## 自主决策框架

无人值守时，所有决策按以下层级执行，不可越级：

```
Philosophy（7 条哲学原则，不可违背）
  → Iron Rules（8 条铁律，不可违背）
    → Existing Practices（claude-next.md / kernel.md / 项目惯例）
      → AI 自主判断（通用工程最佳实践）
```

## 危险操作裁决链

执行中遇到高风险操作时，按三级链条裁决：

**Level 1: AGENTS.md 裁决** — Philosophy → Iron Rules → Existing Practices。有明确答案 → 执行并记录依据。无覆盖 → Level 2。

**Level 2: Oracle 第三方审核** — Oracle agent 独立审核，裁决留痕。可执行 → [Oracle: approved]。应跳过 → skip-risk [Oracle: rejected]。不确定 → Level 3。

**Level 3: 人类裁决（最后手段）** — 记录为 blocked_human，附全部裁决记录。继续其他任务不阻塞。

## 卡点分类处理矩阵

| 卡点类型 | 判定标准 | 处理方式 |
|---------|---------|---------|
| 可跳过 | 不阻断目标，有替代路径 | skip-risk 记录，继续 |
| 可绕行 | 可换方案达成目标 | 自动降级到备选方案 |
| 危险操作 | 远程推送/权限操作/破坏性命令 | 走三级裁决链 |
| 真阻断 | 核心路径被堵死 | 记录 blocked，继续其他 |
| 需人类 | 裁决链三级均无法确定 | 记录 blocked_human，继续其他 |

---

## Phase 0: 前置澄清窗口（唯一的人类交互）

### Step 0.1: 解析目标

有完整目标描述 → 直接进入 Step 0.2。无参数 → 问一句话目标。

### Step 0.2: AI 主动扫描不确定项

扫描维度：范围边界、外部依赖、能力缺口、风险点、执行顺序、验收条件。

### Step 0.3: 输出执行计划 + 不确定项清单

展示：子任务列表（含验收条件、依赖）、所有 Q 项一次性列出、已识别风险及策略。回复 "开始" 激活。

### Step 0.4: 激活

人类确认后立即激活。从此不再询问任何问题。

---

## Phase 1→N: 全自动执行

### 核心铁律

1. **不暂停** — 不等待人类输入
2. **不提问** — 歧义按决策框架判断
3. **不中断** — 卡点处理后继续
4. **只记录** — 风险和阻断写入 skipped_risks

### 常见场景自主处理

| 场景 | 自主处理 |
|------|---------|
| 修复范围超预期 | 评估仍在目标内 → 继续，否则 skip-risk |
| 需安装依赖 | 能自动装则装，需管理员权限 → skip-risk |
| 远程推送 | commit 照常，push → 走裁决链 |
| Context Guard 阻断 | 创建 override 文件，改用 Bash |
| Permission Gate 拦截 | 走三级裁决链 |
| 发现无关问题 | 记入附带发现，不偏离主线 |
| 子任务冲突 | Philosophy #2 选择更高价值路径 |
| 上下文超阈值 | compact 或全用 Bash 替代 Edit |

---

## 退出报告

完成后自动生成报告 + 关闭模式。包含：已完成 + 已跳过 + Oracle 裁决记录 + 阻断项 + 附带发现。

---

## 哲学

| # | 哲学 | 物化 |
|---|------|------|
| #3 | 先守护 | gate 降级 warn-only，危险操作走裁决链 |
| #4 | 没验证=没做 | task-done 附证据，Oracle 裁决留痕 |
| #6 | 0 信任 | 风险记录 skipped_risks，Oracle 独立审核 |
| #7 | 文档优先 | 退出报告结构化，裁决可追溯 |
