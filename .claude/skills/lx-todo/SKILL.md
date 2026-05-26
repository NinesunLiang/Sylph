---
name: lx-todo
version: v4.0.0
description: "轻量开发模式：捕获 → 分拣 → 执行 → 验证 → 关闭。5 步单终端闭环，≤3 文件变更。"
complexity: beginner
when_to_use: "Use when user says 'todo', 'quick fix', 'small bug', /lx-todo"
argument-hint: "add 🐛 P1 <desc> | do [#id] | next | list | review"
harness_version: ">=6.3.0"
status: mature
role: "Lightweight single-terminal fix-verify-close workflow"
execution_mode: stepwise
triggers:
  - "/lx-todo"
---

# lx-todo — 轻量开发模式

## 原子化声明

| 脚本 | 用途 |
|------|------|
| `scripts/todo_queue.py` | todo-queue.md 读写 |

| 节点 | 路径 |
|------|------|
| behavior_rules | `../../nodes/behavior_rules.md` |
| interactive_prompt | `../../nodes/interactive_prompt.md` |

| Schema | 路径 |
|--------|------|
| task_input / acceptance_report / verdict | `../../schemas/` |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/execution-types.md` | execution types 阶段 |
| `references/queue-format.md` | queue format 阶段 |
| `references/steps-capture-triage.md` | steps capture triage 阶段 |
| `references/steps-close-review.md` | steps close review 阶段 |
| `references/steps-execute-verify.md` | steps execute verify 阶段 |
| `references/upgrade-protocol.md` | upgrade protocol 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
need_clarification → executing → [Capture → Triage → Execute → Verify → Close] → done
```

## 角色与边界

- **做什么**：5 步闭环，处理 ≤3 文件 bug/feature/refactor/docs
- **不做什么**：>3 文件 → 升级 lx-task-spec；需设计 → 升级 lx-rpe

## 子命令路由

| 子命令 | 动作 | 示例 |
|--------|------|------|
| `add` | 捕获 → Step 0 | `/lx-todo add 🐛 P1 nil panic` |
| `do #N` | 处理指定项 → Step 1 | `/lx-todo do #3` |
| `next` | 最高优先级 → Step 1 | `/lx-todo next` |
| `list` | 显示所有 | `/lx-todo list` |
| `review` | 批次回顾 → Step 5 | `/lx-todo review` |
| **无参数** | = `next` | `/lx-todo` |

## 执行步骤

### Step 0-1: 捕获 + 分拣 → `@references/steps-capture-triage.md`

捕获四要素（类型/优先级/描述/来源）→ 30 秒分拣决策（≤3 文件 → Todo，>3 → 升级）。

### Step 2-3: 执行 + 验证 → `@references/steps-execute-verify.md`

按类型分流执行 → go test + /lx-pre-commit 门禁。blocked 2 次 → 升级。

### Step 4-5: 关闭 + 回顾 → `@references/steps-close-review.md`

git add + commit → todo-queue.md 更新。批次回顾统计 + 告警 + 模式发现。

## 升级协议 → `@references/upgrade-protocol.md`

超限（>3 文件 / 2 次失败）→ 升级 lx-task-spec。

## 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| todo_queue.py 失败 | 脚本操作 | 直接读写 todo-queue.md |
| go build 失败 >2 次 | 修复 | 升级 lx-task-spec |
| lx-pre-commit 不可用 | 调用 skill | 手动 go build && go test |
| 变更 >3 文件 | 继续 | 升级 lx-task-spec |

## 跨 Skill 联动

| 方向 | Skill | 触发 |
|------|-------|------|
| 内部调用 | `/lx-pre-commit` | Step 3 质量门禁 |
| 上游 | `/lx-code-review` | P2/P3 非阻塞项 → 自动 add |
| 下游 | `lx-task-spec` | 升级的 todo 项 |

> 文件格式 → `@references/queue-format.md` | 执行类型 → `@references/execution-types.md`
