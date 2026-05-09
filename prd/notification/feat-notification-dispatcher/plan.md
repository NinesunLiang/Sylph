# Plan: Notification Dispatcher

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: Bull 队列 + AlertTriggered 消费 + 投递编排

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/dispatcher/queue.ts`, `src/notification/dispatcher/event-consumer.ts`, `src/notification/dispatcher/dispatch-orchestrator.ts` |
| 预估行数 | ~120 行 |
| 回滚方案 | `git checkout -- src/notification/dispatcher/` |

**验收标准：**
- [ ] Bull 队列初始化（Redis 连接）
- [ ] AlertTriggered 事件正确消费（解析 channels 列表）
- [ ] 静默时段检查（入队前）+ 命中 → 丢弃并记录 suppression
- [ ] 按 channel 优先级编排投递（push → email → sms）
- [ ] 调度延迟 < 500ms
- [ ] 回滚: 清空队列 + 恢复 Redis 备份

**边界/错误：**
- 空 channels 列表 → 记录 warning，不投递
- 未知 channel 类型 → 跳过，记录 error
- Redis 连接失败 → 降级为同步投递（无队列，延迟劣化但保活）

### Task 2: 重试 + 降级 + 回执

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/dispatcher/retry-handler.ts`, `src/notification/dispatcher/channel-fallback.ts`, `src/notification/dispatcher/delivery-receipt-store.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/notification/dispatcher/retry-handler.ts` |

**验收标准：**
- [ ] 指数退避：30s → 2min → 5min, max 3 次
- [ ] 通道故障 → 自动降级下一优先通道
- [ ] DeliveryReceipt 正确记录（status, latency_ms, error）
- [ ] 轮次间根因假设记录（避免盲目重试）
- [ ] DeliveryConfirmed/DeliveryFailed 事件正确发布

**边界/错误：**
- 所有通道失败 → 发布 DeliveryFailed，标记最终状态
- 重试到 max 后仍失败 → 禁止再次入队，永久失败
- 回执写入失败 → 记录 error 日志，不阻塞投递
- 降级图: push→email→sms→全部失败

### Task 3: 事件消费（PreferencesChanged, PremiumTierChanged）+ 缓存

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/dispatcher/preference-change-consumer.ts`, `src/notification/dispatcher/premium-change-consumer.ts`, `src/notification/dispatcher/preference-cache.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/notification/dispatcher/preference-change-consumer.ts` |

**验收标准：**
- [ ] PreferencesChanged → 刷新缓存（< 5s 生效）
- [ ] PremiumTierChanged → free → 禁用 SMS 通道 + 清理队列中 SMS 任务
- [ ] 缓存 TTL 5min，事件刷新后重置
- [ ] 事件消费失败 → 定时全量刷新（30s 兜底）
- [ ] 队列中待发任务更新（非删除，标记跳过）

**边界/错误：**
- 事件消费连续 3 次失败 → 降级为定时轮询
- 缓存刷新中同时收到新 AlertTriggered → 新事件走新缓存（读后写一致性）
- changed_fields 不涉及 channels/quiet_hours → 不触发刷新
- old_tier == new_tier → 跳过处理
- SMS 队列清理不删除任务，仅标记 skip 避免下游读到空洞

### Task 4: 背压 + 静默时段 + 状态查询

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/dispatcher/backpressure.ts`, `src/notification/dispatcher/quiet-hours.ts`, `src/notification/dispatcher/delivery-status-store.ts`, `src/notification/dispatcher/health-check.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/notification/dispatcher/backpressure.ts` |

**验收标准：**
- [ ] 积压 > 10000 → 背压限流触发（暂停入队）
- [ ] 积压 < 5000 → 自动恢复（hysteresis 防抖动）
- [ ] 出队时二次静默检查（防入队后 preferences 变更）
- [ ] getDeliveryStatus 返回准确投递状态
- [ ] testChannel 正确返回通道健康状态

**边界/错误：**
- 背压触发期间新 AlertTriggered → 记录 rejected 日志（不丢失，由上游重试）
- 背压状态持久化 → 进程重启后恢复
- 静默时段 end=start → 视为禁用静默（配置错误容错）

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 重试逻辑 + 退避算法 | Jest | 时间间隔精确、max 3 次 |
| 单元 | 缓存刷新 + 失效策略 | Jest | TTL、事件刷新、兜底刷新 |
| 单元 | 背压迟滞区间 | Jest | 10000 触发 / 5000 恢复 |
| 单元 | 静默时段 + 时区计算 | Jest | 边界值（跨天、夏令时） |
| 集成 | 事件消费 + 回执 (mock bus) | Jest | 3 条入站事件正确处理 |
| 集成 | 队列 (ioredis mock) | Jest | 入队/出队/重试/降级 |
| 破坏性 | Redis 断连 + 恢复 | Jest mock | 降级同步、恢复后重建队列 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/notification/dispatcher/queue.ts` | 新增 | Bull 队列初始化 |
| `src/notification/dispatcher/event-consumer.ts` | 新增 | AlertTriggered 消费 |
| `src/notification/dispatcher/dispatch-orchestrator.ts` | 新增 | 投递编排 |
| `src/notification/dispatcher/retry-handler.ts` | 新增 | 重试管理 |
| `src/notification/dispatcher/channel-fallback.ts` | 新增 | 通道降级 |
| `src/notification/dispatcher/delivery-receipt-store.ts` | 新增 | 回执存储 |
| `src/notification/dispatcher/backpressure.ts` | 新增 | 背压控制 |
| `src/notification/dispatcher/quiet-hours.ts` | 新增 | 静默时段 |
| `src/notification/dispatcher/delivery-status-store.ts` | 新增 | 状态持久化 |
| `src/notification/dispatcher/health-check.ts` | 新增 | 通道健康检查 |
| `src/notification/dispatcher/preference-change-consumer.ts` | 新增 | PreferencesChanged 消费 |
| `src/notification/dispatcher/premium-change-consumer.ts` | 新增 | PremiumTierChanged 消费 |
| `src/notification/dispatcher/preference-cache.ts` | 新增 | 偏好缓存 |

---

## 非范围

- 不实现具体通道投递（由 Push/Email/SMS feature 负责）
- 不实现用户偏好管理（由 User Preferences 负责）
- 不实现告警条件评估（由 Alert Engine 负责）
- 不实现消息去重（由 Alert Engine Trigger History 负责）
