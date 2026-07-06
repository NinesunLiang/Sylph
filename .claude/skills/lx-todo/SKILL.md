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
nodes:
  - behavior_rules           # 自洽检查 + 范围冻结
  - interactive_prompt       # 无参数时引导
  - auto_fixer               # P0/P1 自动修复
  - verifier                 # 修复验证
  - report_generator         # review 报告
schemas:
  - atomic/finding           # 问题发现
  - atomic/fix_record        # 修复记录
  - atomic/verdict           # 最终判定
  - output/acceptance_report # 验收报告
---
# lx-todo — 轻量开发模式

## 原子化声明（本文件修改时验证是否违反 lx-validate-skill R8/R9）

### 通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| behavior_rules | `../../nodes/behavior_rules.md` | 自洽检查 + 范围冻结 + 3 轮上限 |
| interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |
| auto_fixer | `../../nodes/auto_fixer.md` | P0/P1 自动修复 |
| verifier | `../../nodes/verifier.md` | 修复后 re-scan 验证 |
| report_generator | `../../nodes/report_generator.md` | review 报告生成 |

### Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| finding | `../../schemas/atomic/finding.yaml` | 问题发现 |
| fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录 |
| verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |
| acceptance_report | `../../schemas/output/acceptance_report.yaml` | 验收报告 |

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `scripts/todo_queue.py` | 任务队列管理 | Step 1-5 全流程 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/queue-format.md` | 首次查看/操作队列时 |
| `references/steps-capture-triage.md` | Step 1-2 捕获分拣阶段 |
| `references/steps-execute-verify.md` | Step 3-4 执行验证阶段 |
| `references/steps-close-review.md` | Step 5 关闭审查阶段 |
| `references/execution-types.md` | 选择执行方式时 |
| `references/upgrade-protocol.md` | 任务超出 ≤3 文件范围时升级路由 |

---

**VERIFIED: lx-todo add|do|next|list|review|close**

> 轻量开发模式。≤3 文件、单终端、不开 subagent。

## 一句话定位

轻量级 todo 工具。复杂任务（>3 文件 / 跨域重构 / 高难度 bug）→ 路由到 lx-goal / lx-stepwise / lx-race。

## 💡 完整流程（5 步闭环）

```
捕获 → 分拣 → 执行 → 验证 → 关闭
```

### Step 1: 捕获（register bug / feature）

```
/lx-todo add 🐛 P1 用户登录时 OAuth 回调 500
/lx-todo add ✨ P2 添加日志级别动态配置
```

### Step 2: 分拣（triage）

```
/lx-todo list       # 查看队列
/lx-todo do <ID>    # 认领任务 → 进入 Step 3
/lx-todo next       # 自动认领最高优先级
```

### Step 3: 执行（fix — 单终端）

- 读取目标文件
- 修改（`../../nodes/auto_fixer.md` 可为 P0 执行自动修复）
- 运行测试

### Step 4: 验证（verify — 参考 `../../nodes/verifier.md`）

- `../../nodes/verifier.md` 修复后 re-scan
- 手动验证逻辑

### Step 5: 关闭（close — review 报告）

```
/lx-todo review     # 审查当前 diff
/lx-todo close      # 确认关闭
```

## 升级协议（当任务超出 todo 范围时）

| 特征 | 升级路径 |
|:-----|:---------|
| >3 文件修改 | → lx-goal |
| 跨域重构 | → lx-goal → lx-stepwise |
| 根因不明 bug | → lx-goal → lx-stepwise |
| 3+ 独立子任务 | → lx-goal → lx-race |
| 涉及架构决策 | → lx-goal → Oracle |

升级时保持 todo_id 在 plan.md 中的引用关系。

## 快速命令表

```
add 🐛 <P1-3> <desc>   → Step 1
add ✨ <P1-3> <desc>   → Step 1
list                    → Step 2
do <ID>                 → Step 2 → 3
next                    → Step 2 → 3
review                  → Step 4 → 5
close                   → Step 5
```

## 故障恢复

- 任务修改中断 — `do <ID>` 会读取 `state/` 下的日志，尽可能恢复上下文
- 日志路径: `.omc/todo/tasks/<YYYYMMDD>/<ID>_<slug>/` + `state/progress.md`
