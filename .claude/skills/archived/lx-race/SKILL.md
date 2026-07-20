---
name: lx-race
description: "蜂群协调层 — 快速并行处理简单同构任务。goal/ghost 自动路由至此。"
complexity: intermediate
version: v1.0.0
harness_version: ">=6.3.0"
status: stable
when_to_use: "任务有多个独立同构子任务可并行执行；goal/ghost 自动路由；/lx-race 手动调用"
role: "Swarm coordinator — sub-task registration, dispatch, collection, conflict resolution"
execution_mode: race
triggers:
  - "/lx-race"
nodes:
  - target_resolver         # 解析子任务目标
  - mode_selector           # 模式确认(≥3独立同构→race)
  - execute_node            # 子任务执行(降级+3轮上限)
  - verifier                # 汇总验证
  - report_generator        # 汇总报告
schemas:
  - atomic/scan_target
  - atomic/verdict
---
# lx-race — 文档驱动蜂群并行层

版本: v2.1 | 哲学: #7(文档优先)、#4(验收)、#2(最小改动)

## 四步流程

```
main agent: init → dispatch → [extract] → delegate_task (循环) → report / collect
subagent:   读 task.md → 逐步骤执行 + checkpoint → 写 result.md → 更新 task-state.md
```

| Step | 命令 | 产出 |
|------|------|------|
| 1. init | `race-tool.py init <title>` | batch manifest.md |
| 2. dispatch | `race-tool.py dispatch <batch_id> --tasks <json>` | 子任务目录 |
| 3. extract | `race-tool.py extract <task_dir> [--source <path>]` | extracted.md（可选） |
| 4. execute | `delegate_task` 带路径 | subagent → result.md |
| 5. collect | `race-tool.py collect <batch_id>` | 收集结果 |
| 6. report | `race-tool.py report <batch_id>` | 汇总报告 |

## 命令参考

```
race-tool.py init <title> [--parallel N] [--desc "<desc>"]
race-tool.py dispatch <batch_id> --tasks '<json_array>' [--steps N]
race-tool.py status <batch_id>
race-tool.py collect <batch_id>
race-tool.py report <batch_id>
race-tool.py update <task_dir> <state> [message]
race-tool.py extract <task_dir> [--chunk-size N] [--source <path>]
race-tool.py checkpoint <task_dir> <step_num> <message>
race-tool.py recover <task_dir>
```

## 子任务目录结构

```
.omc/plan/{YYYYMMDD}/{batch_id}/
  manifest.md       — batch 元信息
  {taskid}/
    task.md         — goal + context + criteria
    executor.md     — 执行步骤 + checkpoint
    result.md       — 最终产出
    task-state.md   — 状态机
    extracted.md    — 大文件摘要 [可选]
```

## 状态机

```
pending → running → step_1_done → step_2_done → ... → done
                   → failed → retry(≤3) → running
                                  → blocked(>3)
```

## 超时恢复

Main agent 轮询检测到超时 → 触发 retry。Subagent 重启后用 `race-tool.py recover <dir>` 从断点继续。

## 参考

- `.claude/reference/race-subagent-protocol.md` — subagent 执行契约
- `.claude/scripts/race-tool.py` — 核心 CLI 工具
- `packages/carroros-gov/src/scripts/race-tool.py` — 源码
