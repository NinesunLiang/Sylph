# workflows/ — 工作流定义与基础设施

> 存放具体工作流定义和通用工作流基础设施 hook。

## 基础设施（hooks/）

| 文件 | 用途 |
|------|------|
| `checkpoint.py` | 工作流检查点 |
| `pretool-workflow-gate.py` | 工作流前置门禁 |
| `session-inject.py` | 会话注入 |
| `state-recovery.py` | 状态恢复 |

这些基础设施来自原 `workflow-standard/`，`2026-07-23` 合并至此。

## 工作流定义

| 工作流 | 文件 | 说明 |
|--------|------|------|
| `front-stepwise/` | `origin.md` | 前端步进式开发工作流 |
| `frontend-overnight/` | `README.md`, `SOP.md`, `intake.md` 等 | 前端隔夜自动工作流 |
