---
name: lx-ghost
version: v1.4.1
description: "幽灵模式 — 方向驱动的自主探索。Phase 0 穷尽澄清 → Oracle 自主计划审核 → 全自动探索 → 退出报告。"
when_to_use: "Use when user says 'ghost mode', '幽灵模式', '自主探索', 'lx-ghost', /lx-ghost"
argument-hint: "[方向描述] [轮询间隔秒数=600] [过期小时=3] [最小迭代数=0]"
harness_version: ">=6.3.0"
status: stable
role: "Direction-driven autonomous exploration — Oracle-gated single briefing, zero interruptions"
execution_mode: stepwise
triggers: ["/lx-ghost"]
---

# lx-ghost — 方向驱动自主探索

> **一次前置澄清 → 全自动探索 → 退出报告。人类在窗口期确认方向后离开，AI 自主探索直到过期或方向达成。**

## 原子化声明

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/ghost-phase0.md` | Phase 0 前置澄清 |
| `references/ghost-oracle-audit.md` | Phase 0.5 Oracle 审核 |
| `references/ghost-polling.md` | 全自动轮询 |

> 共享 OMA 能力 `@../references/oma/`: degradation-escalation · decision-chain · execution-workflow · skill-chaining
> 复用 lx-goal: `@../lx-goal/references/autonomous-execution.md` · `@../lx-goal/references/exit-report.md`

## 与 lx-goal 的区别

| | lx-goal | lx-ghost |
|---|---------|----------|
| 驱动方式 | 目标驱动（具体任务列表） | 方向驱动（开放探索） |
| 执行模式 | 逐项 task-done | 增量 poll 迭代 |
| 适用场景 | 可分解的具体目标 | 需持续探索改进的方向 |

## Ghost 专属

### Phase 0: 前置澄清 → `@references/ghost-phase0.md`
方向自检 → 穷举不确定项 → 探索计划 → 激活脚本 + CronCreate 轮询。

### Phase 0.5: Oracle 审核 → `@references/ghost-oracle-audit.md`
五维门禁（方向适配/歧义穷尽/硬边界/决策链/退出条件），独立 Oracle 对抗性审查。

### 全自动轮询 → `@references/ghost-polling.md`
每轮 poll 只做一步。方向漂移自检 + min_iterations 防过早收敛。

## 退出

退出协议 → `@../lx-goal/references/exit-report.md`。
```
完成探索 → 生成报告 → lx-ghost report → lx-ghost off
紧急绕过: lx-ghost off --force（留 ghost-exit-pending 桩）
```

## 哲学物化

| # | 哲学 | 物化 |
|---|------|------|
| #3 | 先守护 | gate 降级 warn-only，危险走裁决链 |
| #4 | 没验证=没做 | 每轮 poll 报告状态 |
| #6 | 0 信任 | Phase 0.5 Oracle 审核，硬边界不裁决不绕过 |
| #2 | 少量大增益 | 只做方向相关，min_iterations 拓宽防过早收敛 |

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| 主路径失败 | 输出当前探索摘要，手动保存 |
| 轮询间隔过长 | 手动触发 poll |
| Phase 0 Oracle 不可用 | 降级为 AI 自审 |
