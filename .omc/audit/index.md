# audit/ — 审计日志

> 按日分片的 JSONL 审计日志（`YYYY-MM-DD.jsonl`）。
> 由 pretool/posttool gate hook 写入。

## AI 使用守则

> **只写不读** — 审计日志由 hook 自动追加，AI 不应直接写入。
> **只读不修** — 如需排查问题，按日 `@.omc/audit/{date}.jsonl` 查看，不修改内容。

## 记录格式

每条 JSONL 行包含：

| 字段 | 说明 |
|------|------|
| `timestamp` | 事件时间（ISO 8601） |
| `event_type` | 事件类型（scope_violation, gate_block, warn 等） |
| `actor` | 触发源（如 `hook:pretool-gate`） |
| `decision` | 判定结果（ALLOW / WARN / BLOCK） |
| `reason` | 判定原因 |
| `path` / `scope` | 关联文件或范围 |

## 使用

- 审计日志作为运行时记录，不参与决策逻辑
- 后续可接入外部审计系统消费 JSONL
