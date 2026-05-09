# [Feature] Trigger History

> 所属 Sub PRD：Alert Engine | 目录：`prd/alert-engine/feat-trigger-history/`

## 功能边界（黑盒）

- **负责**：
  - 告警触发后的冷却/去重逻辑（5 分钟冷却窗口）
  - AlertTriggered 事件生成与发射（通知 Notification Delivery 域）
  - 告警触发历史记录（触发时间、价格、状态）
  - 告警自动过期（触发后标记，可配置为重复触发）
  - 历史查询 API（近 30 天）

- **不负责**：
  - 告警条件评估（由 Price/Advanced Evaluation 负责）
  - 通知实际投递（由 Notification Delivery 域负责）
  - 告警配置管理（由 Alert CRUD 负责）

## 对外接口契约

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `processTrigger` | inbound (event) | alert_id, symbol, price, condition_type | {action, cooldown_remaining} | - |
| `getAlertHistory` | inbound | alert_id, date_range | history_entry[] | - |
| `getStats` | inbound | user_id | {total_triggers, today_count, top_symbols} | - |
| `alertTriggered` | outbound | alert_id, symbol, price_at_trigger, channel_hints | — | — |

### 事件（出站至 Notification Delivery）

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `AlertTriggered` | outbound | 告警触发生成事件（完整载荷发送至 Notification Delivery） | alert_id, symbol, price, condition_type, user_id, channels |

```json
{
  "event": "AlertTriggered",
  "payload": {
    "alert_id": "alert_001",
    "symbol": "BTC/USD",
    "price": 70005.50,
    "condition_type": "price_above",
    "user_id": "user_001",
    "channels": ["push", "email"],
    "triggered_at": "2026-05-08T14:30:00Z"
  }
}
```

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| AlertHistory | Own | CR | 告警触发历史记录（触发时间、价格、状态） |

## 依赖关系

- **依赖**：Alert CRUD（告警配置）、Price Evaluation / Advanced Evaluation（消费 AlertConditionMet 事件）
- **被依赖**：Notification Delivery（消费 AlertTriggered 事件）、Dashboard（消费 AlertTriggered 事件）

## 技术约束

- Node.js + TypeScript
- PostgreSQL（历史记录持久化）
- Bull 队列（事件发射缓冲）

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 冷却窗口 | 5 分钟（同告警 ID 去重） | P0 |
| 事件发射延迟 | < 1 秒（决策完成到发出） | P0 |
| 历史保留 | 30 天 | P1 |

## Mock 数据

```json
{
  "process_trigger_with_cooldown": {
    "scenario": "同一告警 2 分钟内重复触发 → 冷却拦截",
    "first_trigger": {"action": "fire", "alert_id": "alert_001"},
    "second_trigger_90s_later": {"action": "cooldown", "cooldown_remaining": 210}
  },
  "history_query": {
    "alert_id": "alert_001",
    "last_30_days": [
      {"triggered_at": "2026-05-08T14:30", "price": 70005.50, "notification_status": "delivered"},
      {"triggered_at": "2026-05-07T09:15", "price": 65000.00, "notification_status": "delivered"}
    ]
  }
}
```

## 验收条件

- [ ] AC-1: 同一告警 5 分钟内重复触发被冷却拦截
- [ ] AC-2: AlertTriggered 事件正确发射（含完整 payload）
- [ ] AC-3: 告警触发后标记为已触发（可配置重复触发）
- [ ] AC-4: 近 30 天历史可查询
- [ ] AC-5: 统计接口返回正确汇总数据
