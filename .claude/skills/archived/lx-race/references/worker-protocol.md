# Worker 协议 — v2.0

> 版本: v2.0 | 哲学: #7(文档优先)、#4(验收)、#2(最小改动)
> 变更: 新增 checkpoint 写入、超时恢复、大文件预处理

## 环境变量

| 变量 | 说明 | 设置者 |
|------|------|--------|
| `RACE_PARENT_ID` | 父任务 ID | dispatch |
| `RACE_SUBTASK_ID` | 子任务 ID | dispatch |
| `RACE_SUBTASK_PATH` | 子任务工作目录（绝对路径） | dispatch |

## 执行模式（v2.0 新增）

Worker 可选择两种执行模式：

### 模式 A: 简单执行（v1.0 兼容）

直接执行 → 写 result.md → 更新 task-state.md

```
读 task.md → 执行 → 写 result.md → race-tool.py update <dir> done
```

### 模式 B: 分步骤执行 + Checkpoint（推荐 v2.0）

```
读 task.md → 按 executor.md 步骤逐条执行:
  1. 执行 step
  2. race-tool.py checkpoint <dir> <N> "<摘要>"
  3. race-tool.py update <dir> step_N_done
写 result.md
race-tool.py update <dir> done "任务完成"
```

## 完成契约

Worker 完成时：

### 模式 A（v1.0 兼容）

写入 `$RACE_SUBTASK_PATH/result.md`：

```markdown
# Task Result — {task_id}

## 执行摘要

{做了什么、关键发现、证据引用}

## 产出物

{文件列表或输出内容}
```

### 模式 B（v2.0，推荐）

写入 `$RACE_SUBTASK_PATH/result.md`（同上格式）

并保持 `executor.md` 中所有 step 标记为 `[x]`，含 checkpoint 记录。

## Checkpoint 格式

executor.md 中每个已完成 step 应包含：

```markdown
- [x] Step N: <步骤名>
  - checkpoint: ckpt-N
  - completed: {timestamp}
  - summary: <做了什么、关键发现、决策理由>
  - output: <产出物文件名，可选>
```

## 恢复契约

Worker 被重新派遣时：

1. 读 `task-state.md` 查看 `state` 和 `last_checkpoint`
2. 读 `executor.md` 查找最后一个 `[x]` step
3. 从下一个 `[ ]` step 继续执行
4. 对已完成 steps 做快速重验证（确认产出物完整）

```bash
# 查看恢复信息
race-tool.py recover <task_dir>
```

## 大文件预处理

当 task.md 的 context 引用大文件（>200 行）时：

1. main agent 会预处理生成 `extracted.md`
2. subagent 读 task.md 时看到 `@see extracted.md` 行
3. 优先读 extracted.md 代替原始文件

```bash
# 手动提取（subagent 也可自行调用）
race-tool.py extract <task_dir> [--source <path>]
```

## 失败约定

- 一个子任务失败不影响其他子任务
- 父任务最终状态由所有子任务聚合结果决定
- OMA Lock 在失败时不自动释放 → `posttool-write-lock.sh` 负责清理

## OMA Lock 协同

| 场景 | 保护机制 |
|------|---------|
| 两个 worker 同时写同一文件 | `pretool-write-lock.sh` 自动加锁 |
| worker A 不知 worker B 在做什么 | `race-tool.py status <batch_id>` 可见 |
| worker B 改了 A 依赖的文件 | 锁阻止同时写入，Race 标记依赖冲突 |
