# 0002. Token + Lock 双层任务生命周期

**日期**: 2026-07-24 (last revised: 2026-07-26)
**来源**: task-architecture/orchestrator.md, 任务编排设计

## 上下文

AI 在执行长任务时需要跨会话跟踪任务的生命周期。会话可能因为超时、紧凑（compact）、手动停止或崩溃而中断。需要一个机制来：

1. 知道某个任务已启动但未完成
2. 防止同一任务被两个会话同时执行
3. 在紧凑事件后恢复任务状态
4. 不引入外部基础设施依赖

## 决策

实施两层架构：

**Token 层**（`.omc/tokens/YYYYMMDD/{task_name}.json`）：
- 轻量 JSON 文件，存储任务元数据：`status`、`phase`、`session`、`task`、`scope`
- 按日期分目录存储（`tokens/20260721/`），每日一个子目录
- 生命周期阶段：`active`（执行中）、`off`（已关闭）、`goal`/`ghost`/`idle`（模式）
- 锁文件：同目录 `{task_name}.json.lock`，与 token 文件并列
- token 选择器（SSOT）：`task_ssot.latest_active_token()` 按日期+状态筛选活跃 token
- 紧凑事件后通过 token 恢复任务状态（session、step、scope）

**Lock 层**（`.omc/tokens/YYYYMMDD/{task_name}.json.lock`）：
- 纯锁文件，包含当前 PID 和启动时间戳
- 进程退出时自动释放（操作系统级清理）
- 进程启动时检查锁文件是否存在且持有者存活 → 存活着拒绝，否则清理旧锁

Token 通过 task_ssot（单一真相源，`.claude/scripts/lib/task_ssot.py`）访问，SSOT 负责选择最新活跃 token。

## 替代方案

- **单文件 `.omc/token.json`**（已废弃）— 最初设计的路径，v2 重构后改为按日期分目录存储，避免紧凑事件写入时脏读。不再使用 `.omc/token.json`。
- **数据库依赖** — 使用 SQLite 或 Redis 存储任务生命周期。优点是 ACID 保证；缺点是为一个 CLI 工具引入持久层太重，增加部署复杂度，违反 "zero external deps" 原则。
- **仅锁文件** — 只有 lock 没有 token。优点是简单；缺点是会话之间无法传递任务元数据，紧凑后完全丢失上下文。
- **Git branch 状态** — 通过 git branch 和 commit message 追踪状态。优点是天然分布式；缺点是 git 操作昂贵，频繁创建分支污染仓库，紧凑/变基场景不稳定。

## 理由

1. **紧凑安全** — 紧凑事件只影响当前会话上下文，而 token 在磁盘上独立存在。紧凑后读取 token 即可恢复。
2. **并发安全** — Lock 文件 + PID 验证防止两个会话同时写同一任务。
3. **零外部依赖** — 纯文件系统机制，不需要数据库、Redis 或任何第三方组件。
4. **轻量高效** — Token JSON 通常 < 1KB，读取成本极低。
5. **可审计** — Token 阶段变化写入 `.omc/audit/`，记录完整生命周期。
6. **SSOT 去中心化** — `task_ssot.py` 作为唯一真相源，hook 不再自实现 token 选择器。

## 后果

- 每个任务启动时需先获取锁（阻塞或失败）
- 按日期分目录存储后，旧任务自动切换到 `archive/tokens/`（跨天已完成任务自动归档）
- 需要在 `.omc/.gitignore` 中排除 lock 文件（不提交）
- 需要在进程启动/退出时清理 stale lock（警惕孤儿锁）
- SSOT VALID_MODES = {"idle", "goal", "ghost"}，与实际 token phase 字段（如 "off"）通过 `reconcile_handoff()` 在写入时对齐
- 已废弃的 `.omc/state/token.json` 通过 `_clean_stale_state_token()` 自动清理
