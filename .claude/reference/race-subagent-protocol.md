# Race Subagent Protocol — v3.0

> 版本: v3.0 | 哲学: #7(文档优先)、#4(验收)、#2(最小改动)
> 变更: v3.0 — 新增 recover / timeout-check / depends_on / retry_count/step；废弃 race_manager.sh

## 核心原理

main agent 和 subagent **不直接消息对接**，通过 `.omc/plan/` 下的文件交换任务状态。

```
main agent: 写 task.md → delegate_task(path) → 轮询 task-state.md → 收 result.md
subagent:   读 task.md → 逐步骤执行并写 checkpoint → 写 result.md → 更新 task-state.md
```

## 目录结构

```
.omc/plan/{YYYYMMDD}/{batch_id}/
  manifest.md    — batch 元信息（main 写）
  {taskid}/
    task.md       — 任务描述（main 写）
    executor.md   — 执行步骤 + checkpoint（subagent 动态更新）
    result.md     — 最终产出物（subagent 写）
    task-state.md — 状态机文件（subagent 更新）
    extracted.md  — 大文件 chunk 摘要 [可选，extract 命令生成]
```

## 状态机

```
pending → running → step_1_done → step_2_done → ... → done
                   → failed → retry(≤3) → running
                                  → blocked(>3)
```

## Subagent 执行契约

1. **读入**: 读 `task.md` 获取 goal + context + criteria
   - 若 `extracted.md` 存在，优先读取代替原始大文件（参考 `@see extracted.md`）
2. **检查恢复**: 读 `task-state.md` 检查 `last_checkpoint`
   - 若有 checkpoint → 读 `executor.md` 定位最后完成的 step
   - 从下一个 `[ ]` step 开始，跳过已完成 step
3. **逐步骤执行**:
   - 对每个 step:
     a. 执行 step 内容
     b. 写入产出物（推荐：分析笔记、patch 文件等）
     c. 调用: `race-tool.py checkpoint <task_dir> <N> "<产出摘要>"`
     d. 更新: `race-tool.py update <task_dir> step_N_done`
4. **最终产出**: 写入 `result.md`（最终结果 + 证据引用）
5. **完成**: `race-tool.py update <task_dir> done "任务完成"`
6. **失败**: 写入 `result.md`（原因）→ `race-tool.py update <task_dir> failed "<原因>"`
7. **重试**: `failed → retry → running`（由 main agent 触发）

## executor.md checkpoint 格式

```markdown
- [x] Step N: <步骤名>
  - checkpoint: ckpt-N
  - completed: 2026-06-10 14:35:00
  - summary: <已完成的内容、关键发现、决策理由>
  - output: <产出物文件名，可选>
```

## Main agent 轮询契约

```
DEFAULT_TIMEOUT = 600  # 10 分钟

start = now()
while state in (pending, running, step_1_done, ..., step_N_done):
    sleep(POLL_INTERVAL)
    if elapsed > timeout:
        retry_count += 1
        if retry_count ≤ MAX_RETRY:
            race-tool.py update <task_dir> failed "timeout after {elapsed}s"
            race-tool.py update <task_dir> retry "auto-retry #{retry_count}"
            race-tool.py update <task_dir> running "restart from checkpoint"
        else:
            race-tool.py update <task_dir> blocked "exceeded max retries"
            break
```

## 大文件预处理

Main agent 在 dispatch 后调用：

```bash
race-tool.py extract <task_dir> [--chunk-size 300] [--source <path>]
```

- 自动检测 task.md context 中引用的大文件（行数 > 200）
- 按 chunk-size 分块写入 `extracted.md`
- 在 task.md 末尾追加 `@see extracted.md` 行

## 向后兼容

- **旧 subagent（v1.0）** 不写 checkpoint：仍然 `running → done` 直接跳变
- **旧 executor.md 格式** 不修改，新 subagent 可选使用 checkpoint
- **缺少 extracted.md** 不影响执行，subagent 自行读取原始文件
- **旧 batch 文件** 完全兼容，不需要迁移

## 集成 delegate_task

```
task_dir = race-tool.py dispatch <batch_id> --tasks '[...]'

# 对大文件预处理（可选）
race-tool.py extract <task_dir> --source <path>

delegate_task(
  goal=f"请处理任务目录中的 task.md，完成后更新 task-state.md",
  context=f"任务目录: {task_dir}",
  toolsets=["terminal", "file"],
)
```

## 三域边界

| 模式 | 文档量 | 并行度 | checkpoint | extract |
|:---|:---:|:---:|:---:|:---:|
| race | 1 个 task.md | N 并行 | ✅ | ✅ |
| stepwise | 多文件依赖系统 | 串行 | ✅ | ⚠ 可选 |
| RPE | 完整评审包 | 深度单线 | ❌ | ❌ |
