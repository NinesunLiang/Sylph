# Session Handoff

> 由 context_engine compact-write 于首次使用时自动更新
> AGENTS.md 已 @ 引用本文件，启动时自动加载

## Task
- id: (none)
- level: L1_BASE
- status: no_active_task

## Progress
- verified: 0/0
- current_step: (none)

## Resume Rules
- 磁盘状态文件是最终真相源（token / plan / executor）
- session-handoff 只是恢复摘要，不是完成证据
- 不要标记任何 step 完成不经过 VerifyGate
