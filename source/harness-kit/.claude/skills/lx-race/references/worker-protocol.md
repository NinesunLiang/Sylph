# Worker 协议

## 环境变量

| 变量 | 说明 | 设置者 |
|------|------|--------|
| `RACE_PARENT_ID` | 父任务 ID | dispatch |
| `RACE_SUBTASK_ID` | 子任务 ID | dispatch |
| `RACE_SUBTASK_PATH` | 子任务工作目录（绝对路径） | dispatch |

## 完成契约

Worker 完成后**必须**写入 `$RACE_SUBTASK_PATH/result.json`：

```json
{
  "race_id": "<parent>/<subtask>",
  "status": "completed",
  "completed_at": "2026-05-04T12:00:00Z",
  "output": "执行摘要，关键结果，证据引用"
}
```

## 失败约定

- 一个子任务失败不影响其他子任务
- 父任务最终状态由所有子任务聚合结果决定
- OMA Lock 在失败时不自动释放 → `posttool-write-lock.sh` 负责清理

## OMA Lock 协同

| 场景 | 保护机制 |
|------|---------|
| 两个 worker 同时写同一文件 | `pretool-write-lock.sh` 自动加锁 |
| worker A 不知 worker B 在做什么 | `race_manager.sh status --all` 可见 |
| worker B 改了 A 依赖的文件 | 锁阻止同时写入，Race 标记依赖冲突 |
