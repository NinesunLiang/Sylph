# Plan: Trigger History

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: 冷却窗口 (Redis Lua 原子操作)

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/trigger-history/cooldown.ts`, `src/alert-engine/trigger-history/cooldown.lua` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/alert-engine/trigger-history/` |

**验收标准：**
- [ ] Redis Lua 原子 GET+SET 冷却检查 (一读一写原子完成)
- [ ] 5 分钟 TTL 精确到秒
- [ ] 并发请求不绕过冷却 (原子保证)
- [ ] Redis 不可用 → 降级放过 (宁可多发, 不可漏发告警)

**边界/错误：**
- 冷却中 → 返回 {action: "cooldown", remaining_sec}
- 未冷却 → 设置冷却 + 返回 pass
- Redis Lua EVAL 失败 (脚本错误) → 降级放过 + 审计日志
- 冷 key 不存在 → 视为首次触发 (上次冷却已过期)
- cooldown.lua 脚本内容不可包含 eval 关键字 (kernel.md §禁止行为)

### Task 2: 事件消费 + 发布

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/trigger-history/event-consumer.ts`, `src/alert-engine/trigger-history/event-publisher.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/alert-engine/trigger-history/` |

**验收标准：**
- [ ] AlertConditionMet 正确消费 (来自 Price/Advanced Eval)
- [ ] AlertTriggered 完整载荷发布 (含 user_id, channels, ISO8601 timestamp)
- [ ] 回表查询: alerts 表获取 user_id + channels
- [ ] 事件发射延迟 < 1 秒
- [ ] 发布失败 → 重试 3 次 (1s 间隔), 第 3 次 → 死信队列

**边界/错误：**
- AlertConditionMet 中 alert_id 不存在 → LOG_WARNING + 跳过 (告警已被删除)
- 回表查询 alerts 返回空 → LOG_ERROR + 舍弃事件
- channels 为空 → 仍发布, 由 Dispatcher 处理
- 死信队列 → 审计日志 + 人工干预入口
- delivery_id 格式: `trg_{uuid_v4_short}`

### Task 3: 历史记录 + 过期 + 清理

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/trigger-history/history-store.ts`, `src/alert-engine/trigger-history/expiration.ts`, `src/alert-engine/trigger-history/cleanup.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/alert-engine/trigger-history/` |

**验收标准：**
- [ ] AlertHistory CR: 写入 (INSERT) + 查询 (SELECT WHERE alert_id + date_range)
- [ ] getStats 正确汇总: total, unique_alerts, last_triggered
- [ ] 一次性告警 (repeat=false) 触发后标记 expired
- [ ] 30 天定时清理 (每日 03:00), 记录清理行数
- [ ] 清理 Bash 脚本 exit 0 结尾 (kernel.md §Hook 永不阻塞)

**边界/错误：**
- date_range 跨度 > 365 天 → 400 VALIDATION_ERROR
- 查询不存在的 alert_id → 空数组 (非 404)
- 清理过程中 PostgreSQL 连接断开 → 跳过本次, 下次重试
- 一次性告警重复触发 → 幂等 (status=expired 则跳过)
- 30 天保留期满后, 软删除保留 7 天再物理删除 (kernel.md §最小影响)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 冷却逻辑 | Jest | 5 分钟精确, 原子性 |
| 集成 | Redis Lua 原子操作 | Jest (ioredis mock) | 并发下无绕过 |
| 集成 | 事件消费+发布 | Jest (mock event bus) | AlertConditionMet→AlertTriggered 链路 |
| 集成 | 历史 CR + 过期 | Jest (pg-mock) | 事务 + 级联 |
| 集成 | 定时清理 | Jest (mock timer) | 30 天精确 |
| 安全 | 幂等性 | Jest | delivery_id 去重 |
| 证据 | 每次声明 VERIFIED: | Jest expect | 引用 kernel.md §证据门禁 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/alert-engine/trigger-history/cooldown.ts` | 新增 | 冷却检查 (Redis Lua) |
| `src/alert-engine/trigger-history/cooldown.lua` | 新增 | Redis Lua 原子 GET+SET |
| `src/alert-engine/trigger-history/event-consumer.ts` | 新增 | AlertConditionMet 消费 |
| `src/alert-engine/trigger-history/event-publisher.ts` | 新增 | AlertTriggered 发布 |
| `src/alert-engine/trigger-history/history-store.ts` | 新增 | 历史存储 + 查询 |
| `src/alert-engine/trigger-history/expiration.ts` | 新增 | 一次性告警过期 |
| `src/alert-engine/trigger-history/cleanup.ts` | 新增 | 30 天清理 |

---

## 非范围

- 不实现告警 CRUD（由 Alert CRUD 负责）
- 不实现通知投递（由 Notification Delivery 负责）
- 不实现评估逻辑（由 Price/Advanced Evaluation 负责）
- 不实现 Dashboard 订阅（由 Dashboard 域负责）
