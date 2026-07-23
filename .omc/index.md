# .omc/ — 运行时任务状态

> 删除此目录不影响后续使用 CarrorOS。
> 所有文件由 hook 和脚本在运行时生成。

## AI 使用守则

> **不要全量加载** `.omc/` 下的文件。先读本 index.md 了解目录结构，
> 再根据需求 `@.omc/{子目录}/index.md` 按需深入。
>
> **不要手动编辑** 运行时状态文件（state/, tokens/ 中的 `.json` 文件）。
> 它们由 hook 和 carros_base.py 管理。
>
> **不要修改审计日志**（audit/ 中的 `.jsonl` 文件为只写记录）。

## 子目录

| 目录 | 用途 |
|------|------|
| `tokens/` | 运行时令牌，每任务一个 `.json`，含步骤状态和锁 |
| `tasks/` | 运行时任务文档系统，按日期/任务名分目录，含 plan/executor/handoff |
| `state/` | 运行时状态文件 — lifecycle / hud / snapshots / 证据缓存 / retry-budget |
| `plans/` | 运行时历史计划文档 |
| `archive/` | 已归档任务和令牌（`carros_base.py archive`） |
| `audit/` | 审计日志 JSONL（pretool/posttool 门禁记录） |
| `knowledge/` | 升华管道数据（`sublimation-log.jsonl` + `claude-next.md`） |
| `metrics/` | 基准测试数据（bench/ga/phase0 报告） |

## 根文件

| 文件 | 用途 |
|------|------|
| `session-handoff.md` | 会话交接摘要（compact 前自动写入，新会话注入恢复） |
| `scheduled_tasks.json` | CC 调度任务状态 |
| `.prompt-ring.json` | 最近 20 轮用户 prompt ring |
