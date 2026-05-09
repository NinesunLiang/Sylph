# Plan: Alert CRUD

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: PostgreSQL 数据模型 + DDL + CRUD 核心

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/alert-crud/alert-model.ts`, `src/alert-engine/alert-crud/alert-repository.ts`, `src/alert-engine/alert-crud/alert-handlers.ts`, `src/alert-engine/alert-crud/migrations/001_create_alerts.sql` |
| 预估行数 | ~180 行 |
| 回滚方案 | `git checkout -- src/alert-engine/alert-crud/` + `pg_ctl dropdb` 回退 migration |

**验收标准：**
- [ ] PostgreSQL Alert + AlertCondition + AlertHistory 表结构 (含索引: user_id, status, symbol)
- [ ] DDL migration 脚本可重复执行 (idempotent, IF NOT EXISTS)
- [ ] create/update/delete/get/list 全部实现
- [ ] 级联删除正确 (事务: DELETE alert_conditions → alert_history → alerts)
- [ ] 乐观锁并发控制 (version 字段, 更新时 WHERE version = old_version)
- [ ] Gate-X: migration 脚本须经二次批准

**边界/错误：**
- symbol 格式非法 → 400 VALIDATION_ERROR
- threshold ≤ 0 → 400 VALIDATION_ERROR
- channels 为空数组 → 400 VALIDATION_ERROR
- 删除不存在的 alert_id → 404 NOT_FOUND
- 并发更新同一告警 → 409 CONFLICT (version 不匹配)
- 事务超时 → 500 TRANSACTION_TIMEOUT, 自动 ROLLBACK

### Task 2: Tier 门禁 + 限额

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/alert-crud/tier-gate.ts`, `src/alert-engine/alert-crud/alert-limiter.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/alert-engine/alert-crud/tier-gate.ts` |

**验收标准：**
- [ ] Free × technical_indicator / ai_pattern_detection → TIER_RESTRICTED + upgrade_url
- [ ] Free 限额 5 条活跃告警 (status IN (active,paused))
- [ ] 服务端强制校验 (非仅 UI)
- [ ] tier 缓存 TTL 5min, 兜底刷新 30min
- [ ] 引用 AGENTS.md §难度分级: Free→L1, Premium→L3+

**边界/错误：**
- tier 缓存 miss → 查询 PostgreSQL user_preferences 表
- Redis 不可用 → 降级放过 (stale-while-revalidate)
- Free 用户升级 Premium 后立即解锁 (事件驱动刷新, 不需等 TTL)
- 超限创建 → 403 LIMIT_EXCEEDED + 当前活跃数

### Task 3: 状态机 + 事件消费

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/alert-crud/state-machine.ts`, `src/alert-engine/alert-crud/event-consumer.ts`, `src/alert-engine/alert-crud/event-publisher.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/alert-engine/alert-crud/event-consumer.ts` |

**验收标准：**
- [ ] 状态机转换: active ↔ paused (pause/resume), active → triggered → expired
- [ ] PreferencesChanged → 刷新偏好缓存 (Redis: npref:{user_id})
- [ ] PremiumTierChanged → 刷新 tier 缓存 (Redis: tier:{user_id})
- [ ] AlertStateChanged 事件正确发布 (含 old_status, new_status)
- [ ] 事件消费者降级: 消息总线不可用 → 重试队列 (max 3 次, 间隔 1s)

**边界/错误：**
- pause 已 paused 告警 → 幂等, 返回当前状态不变
- resume 已 active 告警 → 幂等, 返回当前状态不变
- delete 不存在的告警 → 404
- 事件发布失败 → 重试 3 次, 第 3 次失败 → 写死信队列 + 审计日志
- 缓存刷新失败 → TTL 过期后自动回源, 不阻塞主流程

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | CRUD 操作 + Tier 门禁 | Jest | 边界条件正确, 引用 AGENTS.md §铁律 |
| 单元 | 状态机转换 | Jest | 6 种转换全覆盖, 无效转换拒绝 |
| 集成 | 数据库 + 事务 | Jest (pg-mock) | 事务回滚 + 乐观锁 |
| 集成 | 入站事件消费 | Jest (mock event bus) | 缓存使能正确 + 降级 |
| 安全 | Tier 门禁绕过 | Jest | 无客户端侧绕过路径 |
| 证据 | 每次测试必须 VERIFIED: | Jest expect + | 引用实际输出 (kernel.md §证据门禁) |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/alert-engine/alert-crud/alert-model.ts` | 新增 | 数据模型 (含 version 乐观锁) |
| `src/alert-engine/alert-crud/alert-repository.ts` | 新增 | 数据访问 (pg client) |
| `src/alert-engine/alert-crud/alert-handlers.ts` | 新增 | CRUD API handlers |
| `src/alert-engine/alert-crud/migrations/001_create_alerts.sql` | 新增 | DDL (idempotent) |
| `src/alert-engine/alert-crud/tier-gate.ts` | 新增 | Tier 门禁 (引用 AGENTS.md §难度分级) |
| `src/alert-engine/alert-crud/alert-limiter.ts` | 新增 | Free 限额 5 条 |
| `src/alert-engine/alert-crud/state-machine.ts` | 新增 | 状态机 |
| `src/alert-engine/alert-crud/event-consumer.ts` | 新增 | 入站事件 (含降级) |
| `src/alert-engine/alert-crud/event-publisher.ts` | 新增 | 事件发布 |

---

## 非范围

- 不实现评估逻辑（由 Price/Advanced Evaluation 负责）
- 不实现触发后处理（由 Trigger History 负责）
- 不实现通知投递（由 Notification Delivery 负责）
