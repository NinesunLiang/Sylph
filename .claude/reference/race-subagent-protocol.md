# Race Subagent Protocol — 文档驱动并行执行契约

> 版本: v1.0 | 哲学: #7(文档优先)、#4(验收)、#2(最小改动)

## 核心原理

main agent 和 subagent **不直接消息对接**，通过 `.omc/plan/` 下的文件交换任务状态。

```
main agent: 写 task.md → delegate_task(path) → 轮询 task-state.md → 收 result.md
subagent:   读 task.md → 写 result.md → 更新 task-state.md
```

## 目录结构

```
.omc/plan/{YYYYMMDD}/{taskid}_{time}/
  manifest.md    — batch 元信息（main 写）
  task.md        — 任务描述（main 写）
  executor.md    — 执行步骤（subagent 写）
  result.md      — 产出物（subagent 写）
  task-state.md  — 状态机文件（subagent 更新）
```

## 状态机

```
pending → running → done
                 → failed → retry(≤3) → running
                                → blocked(>3)
```

## Subagent 执行契约

1. **读入**: 读 `task.md` 获取 goal + context + criteria
2. **执行**: 执行任务
3. **产出**: 写入 `result.md`
4. **状态**: 更新 `task-state.md` 为 `done`
5. **失败**: 写入 `result.md` 说明原因 → 更新 `task-state.md` 为 `failed`
6. **重试**: `failed` → `retry` → `running`（由 main agent 触发）

## Main agent 轮询契约

```
while state in (pending, running):
  sleep(POLL_INTERVAL)
  read task-state.md
  if elapsed > TIMEOUT → 标记 failed, 重试或上报

重试次数 ≤ 3 → 超限标记 blocked, 跳过
```

## 集成 delegate_task

```
task_dir = race-tool.py dispatch <batch_id> --tasks [...]

delegate_task(
  goal=f"请处理任务目录中的 task.md，完成后更新 task-state.md",
  context=f"任务目录: {task_dir}",
  toolsets=["terminal", "file"],
)
```

## 三域边界

| 模式 | 文档量 | 并行度 | 使用场景 |
|:---|:---:|:---:|:---|
| race | 1 个 task.md | N 并行 | 同构独立子任务 |
| stepwise | 多文件依赖系统 | 串行 | 复杂分析链 |
| RPE | 完整评审包 | 深度单线 | 正式审批/发布 |
