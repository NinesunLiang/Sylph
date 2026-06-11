# lx-race — 文档驱动蜂群并行层

> 版本: v2.1 | 哲学: #7(文档优先)、#4(验收)、#2(最小改动)

## 核心变化 (v2.1)

- ❌ 旧: subagent 执行全在"脑子里"，无中间文件
- ✅ 新: subagent 每完成一步写 checkpoint + 大文件预处理 + 超时自动恢复

## 四步流程

```
main agent: init → dispatch → [extract] → delegate_task (循环) → report / collect
                                  ↑ (轮询 task-state.md，含超时检测)
subagent:   读 task.md → 逐步骤执行 + checkpoint → 写 result.md → 更新 task-state.md
```

| Step | 命令 | 产出 |
|------|------|------|
| 1. init | `race-tool.py init <title>` | batch manifest.md |
| 2. dispatch | `race-tool.py dispatch <batch_id> --tasks <json> [--steps N]` | 子任务目录(task.md + executor.md + task-state.md) |
| 3. extract | `race-tool.py extract <task_dir> [--source <path>]` | extracted.md（大文件预处理，可选） |
| 4. execute | `delegate_task` 带路径 | subagent → checkpoint + result.md |
| 5. collect | `race-tool.py collect <batch_id>` | 收集所有结果 |
| 6. report | `race-tool.py report <batch_id>` | 汇总报告 |

## 命令参考

```
race-tool.py init <title> [--parallel N] [--desc "<desc>"]
race-tool.py dispatch <batch_id> --tasks '<json_array>' [--steps N]
race-tool.py status <batch_id>
race-tool.py collect <batch_id>
race-tool.py report <batch_id>
race-tool.py update <task_dir> <state> [message]
race-tool.py list [--limit N]

# v2.1 新增命令
race-tool.py extract <task_dir> [--chunk-size N] [--source <path>] [--mode raw|summary]
race-tool.py checkpoint <task_dir> <step_num> <message>
race-tool.py checkpoint <task_dir> --rollback <step_num>
race-tool.py recover <task_dir>
race-tool.py timeout-check <batch_id> [--timeout <seconds>]
```

## 子任务目录结构

```
.omc/plan/{YYYYMMDD}/{batch_id}/
  manifest.md    — batch 元信息
  {taskid}/
    task.md       — goal + context + criteria
    executor.md   — 执行步骤 + checkpoint 记录
    result.md     — 最终产出
    task-state.md — 状态机（含 retry_count / last_checkpoint）
    extracted.md  — 大文件 chunk 摘要 [可选]
```

## 状态机 (v2.0)

```
pending → running → step_1_done → step_2_done → ... → done
                   → failed → retry(≤3) → running
                                  → blocked(>3)
```

## Checkpoint 机制

subagent 每完成一个 step：

```bash
race-tool.py checkpoint <task_dir> <N> "<简述完成了什么>"
race-tool.py update <task_dir> step_N_done
```

executor.md 中格式：

```
- [x] Step 2: 执行主逻辑
  - checkpoint: ckpt-2
  - completed: 2026-06-10 14:35:00
  - summary: 完成 src/core.py 中 3 处修改
```

## 超时恢复

Main agent 轮询中检测超时，自动触发 failed → retry → running。

Subagent 重启后通过 `race-tool.py recover <dir>` 查看恢复点，从下一个未完成 step 继续。

## 与 old race_manager.sh 关系

- `race_manager.sh` 保留（旧任务兼容），但新任务全部走 `race-tool.py`
- `.omc/race/` 路径逐步迁移到 `.omc/plan/{date}/`

## 参考文档

- `.claude/reference/race-subagent-protocol.md` — subagent 执行契约 v2.0
- `.claude/reference/race-tool-fix-v2-design.md` — 三项修复技术方案
- `.claude/scripts/race-tool.py` — 核心 CLI 工具（在 packages/ 下，link 到此处）
- `race-tool.py` 主要源码: `packages/carroros-gov/src/scripts/race-tool.py`
