# lx-race — 文档驱动蜂群并行层

> 版本: v2.0 | 哲学: #7(文档优先)、#4(验收)、#2(最小改动)

## 核心变化 (v2.0)

- ❌ 旧: `race_manager.sh` + `.omc/race/` + `delegate_task` 直接对接
- ✅ 新: `race-tool.py` + `.omc/plan/{date}/{taskid}/` + 文档契约

## 四步流程

```
main agent: init → dispatch → delegate_task (循环) → report / collect
                                  ↑ (轮询 task-state.md)
subagent:   读 task.md → 执行 → 写 result.md → 更新 task-state.md
```

| Step | 命令 | 产出 |
|------|------|------|
| 1. init | `race-tool.py init <title>` | batch manifest.md |
| 2. dispatch | `race-tool.py dispatch <batch_id> --tasks <json>` | 子任务目录(task.md + state) |
| 3. execute | `delegate_task` 带路径 | subagent 写 result.md |
| 4. report | `race-tool.py report <batch_id>` | 汇总报告 |

## 命令参考

```
race-tool.py init <title> [--parallel N] [--desc "<desc>"]
race-tool.py dispatch <batch_id> --tasks '<json_array>'
race-tool.py status <batch_id>
race-tool.py collect <batch_id>
race-tool.py report <batch_id>
race-tool.py update <task_dir> <state> [message]
race-tool.py list [--limit N]
```

## 子任务目录结构

```
.omc/plan/{YYYYMMDD}/{batch_id}/
  manifest.md    — batch 元信息
  {taskid}/
    task.md       — goal + context + criteria
    executor.md   — 执行步骤
    result.md     — 产出
    task-state.md — 状态机
```

## 状态机

```
pending → running → done
                 → failed → retry(≤3) → running
                                → blocked(>3)
```

## 与 old race_manager.sh 关系

- `race_manager.sh` 保留（旧任务兼容），但新任务全部走 `race-tool.py`
- `.omc/race/` 路径逐步迁移到 `.omc/plan/{date}/`

## 参考文档

- `.claude/reference/race-subagent-protocol.md` — subagent 执行契约
- `.claude/scripts/race-tool.py` — 核心 CLI 工具（在 packages/ 下，link 到此处）
- `race-tool.py` 主要源码: `packages/carroros-gov/src/scripts/race-tool.py`
