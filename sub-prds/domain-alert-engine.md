# Sub PRD: Alert Engine

> 主 PRD：`mothership-prd.md` | 拆解日期：2026-05-08

## 功能边界（黑盒）

- **负责**：
  - 告警条件定义与评估（价格水平、技术指标、AI 模式）
  - **功能门控：按用户 tier 限制告警类型（Free 仅价格告警且最多 5 条，Premium 含指标+AI）**
  - 告警触发决策引擎（含冷却/去重逻辑）
  - 告警生命周期管理（创建、更新、暂停、恢复、过期）
  - 告警评估性能保障（< 30 秒触发、50K 并发告警）
  - 告警历史记录（触发时间、触发时价格、状态）

- **不负责**：
  - 通知投递（push/email/SMS 由 Notification Delivery 负责）
  - 用户界面渲染（由 Alert Dashboard 负责）
  - 行情数据获取（由 TradingView Integration 负责）
  - 用户偏好管理（由 User Preferences 负责）

## 对外接口契约

### 接口列表

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `createAlert` | inbound | symbol, condition_type, threshold, channels, user_id | alert_id, status | VALIDATION_ERROR, RATE_LIMIT, TIER_RESTRICTED |
| `updateAlert` | inbound | alert_id, partial_fields | updated_alert | NOT_FOUND, VALIDATION_ERROR |
| `deleteAlert` | inbound | alert_id | 204 | NOT_FOUND |
| `pauseAlert` | inbound | alert_id | updated_alert | NOT_FOUND |
| `resumeAlert` | inbound | alert_id | updated_alert | NOT_FOUND |
| `listAlerts` | inbound | user_id, status, page, limit | alert[] | - |
| `getAlert` | inbound | alert_id | alert_detail | NOT_FOUND |
| `getAlertHistory` | inbound | alert_id, date_range | history_entry[] | NOT_FOUND |
| `processTrigger` | inbound | alert_id, symbol, price, condition_type | {action, cooldown_remaining} | COOLDOWN_ACTIVE |
| `getStats` | inbound | user_id | {total_triggers, today_count, top_symbols} | - |
| `alertTriggered` | outbound | alert_id, symbol, price_at_trigger, channel_hints | - | - |

### 事件 / 消息 — 出站

| 事件名 | 发布方 | 订阅方 | 载荷 |
|--------|--------|--------|------|
| `AlertTriggered` | Alert Engine | Notification Delivery | alert_id, symbol, price, condition_type, user_id, channels |
| `AlertStateChanged` | Alert Engine | Alert Dashboard | alert_id, user_id, old_status, new_status |
| `AlertConditionMet` | Alert Engine | 内部（Trigger History） | alert_id, symbol, price, condition_type, evaluation_id |

### 事件 / 消息 — 入站（Alert Engine 消费）

| 事件名 | 发布方 | 载荷 |
|--------|--------|------|
| `PriceUpdate` | TradingView Integration | symbol, price, timestamp |
| `IndicatorUpdate` | TradingView Integration | symbol, indicator, value, confidence |
| `PreferencesChanged` | User Preferences | user_id, changed_fields |
| `PremiumTierChanged` | User Preferences | user_id, old_tier, new_tier |

## 非功能契约

| 属性 | 约束值 | 优先级 | 来源 |
|------|--------|--------|------|
| 告警触发延迟 | < 30 秒（条件满足→触发） | P0 | PRD §非功能需求 |
| 并发告警评估 | 1,000 评估/秒 | P0 | PRD §非功能需求 |
| 总告警容量 | 50,000+ 并发告警 | P1 | PRD §非功能需求 |
| API 响应时间 | < 500ms (P95) | P1 | PRD §非功能需求 |
| 冷却窗口 | 5 分钟（价格快速穿越去重） | P0 | PRD Use Case 1 Edge Case |

## Mock 数据

```json
{
  "mock_create_alert": {
    "request": {
      "user_id": "user_001",
      "symbol": "BTC/USD",
      "condition_type": "price_above",
      "threshold": 70000.00,
      "notification_channels": ["push", "email"]
    },
    "response": {
      "alert_id": "alert_001",
      "status": "active",
      "created_at": "2026-05-08T10:00:00Z"
    }
  },
  "mock_trigger_event": {
    "alert_id": "alert_001",
    "symbol": "BTC/USD",
    "price_at_trigger": 70005.50,
    "condition_type": "price_above",
    "triggered_at": "2026-05-08T14:30:00Z"
  }
}
```

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| Alert | Own | CRUD | 告警配置（条件、渠道、状态） |
| AlertHistory | Own | CR | 告警触发历史记录 |
| AlertCondition | Own | CRUD | 条件定义（类型、阈值、逻辑） — feat-alert-crud 负责 CRUD, feat-advanced-evaluation 仅 Read |

## 依赖关系

- **依赖**：TradingView Integration（行情数据输入）、User Preferences（用户渠道偏好）
- **被依赖**：Notification Delivery（消费 AlertTriggered 事件）

## 父需求追溯

| 主 PRD 章节 | 覆盖内容 |
|-------------|---------|
| §Product Requirements - Price Level Alerts (P0) | 全部 |
| §Product Requirements - Technical Indicator Alerts (P1) | 全部 |
| §Product Requirements - AI Pattern Detection (P1) | 全部 |
| §Technical Specifications - Alert Processing | 全部 |
| §Performance - Alert trigger evaluation | 全部 |

## 验收条件

- [ ] AC-1: 创建价格水平告警 → 条件满足后 30 秒内完成触发决策（含引擎评估+冷却判断；通知投递延迟由 Notification Delivery 域单独计量：Push < 10s）
- [ ] AC-2: 价格快速穿越时 5 分钟冷却窗口生效
- [ ] AC-3: 50,000 并发告警下系统稳定
- [ ] AC-4: 暂停/恢复告警状态切换正确
- [ ] AC-5: 告警触发后自动过期，可配置为重复触发

## 技术约束

- Node.js + Bull 队列（PRD 指定）
- PostgreSQL 存储告警配置
- Redis 存储实时告警状态
