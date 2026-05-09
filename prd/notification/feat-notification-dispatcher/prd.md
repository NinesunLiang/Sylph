# Feature: Notification Dispatcher

> 所属 Sub PRD：Notification Delivery
> 职责：通知分发核心 — 队列管理、背压控制、重试编排、通道降级、静默时段过滤

## 功能边界

- **负责**：
  - 消费 AlertTriggered 事件，解析 channels 列表
  - 读取用户通知偏好（调用 User Preferences API）及静默时段配置
  - 投递前静默时段过滤（Quiet Hours 期间抑制通知）
  - 按优先级依次投递各通道（Push → Email → SMS）
  - 投递队列管理（Bull + Redis），背压控制
  - 失败重试（指数退避，max 3 次）
  - 通道故障时自动降级到下一优先通道
  - 投递状态追踪（`getDeliveryStatus` 接口）
  - 通道健康检查（`testChannel` 接口）
  - 发布 DeliveryConfirmed / DeliveryFailed 事件

- **不负责**：
  - 具体通道的投递实现（Push/Email/SMS 由独立 feature 负责）
  - 用户偏好管理
  - 告警条件评估

## 对外接口

### 接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `sendNotification` | inbound (event) | alert_id, user_id, title, body, channels | delivery_id[] |
| `getDeliveryStatus` | inbound (API) | delivery_id | {status, channel, attempts} |
| `testChannel` | inbound (API) | user_id, channel | {success, latency_ms} |

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `AlertTriggered` | inbound | 由 Alert Engine 触发，启动通知投递流程 | alert_id, symbol, price, user_id, channels |
| `PreferencesChanged` | inbound | 用户偏好变更 → 刷新缓存偏好与静默时段配置 | user_id, changed_fields |
| `PremiumTierChanged` | inbound | Tier 变更 → 刷新通道可用性（降级用户禁用 SMS） | user_id, old_tier, new_tier |
| `DeliveryConfirmed` | outbound | 投递成功 | delivery_id, alert_id, channel, timestamp |
| `DeliveryFailed` | outbound | 投递失败 | delivery_id, alert_id, channel, error, retry_count |

## 非功能要求

| 属性 | 约束值 | 优先级 | 来源 |
|------|--------|--------|------|
| 调度延迟 | < 500ms（事件入队到派发给通道） | P0 | Sub PRD §性能 |
| 背压阈值 | 队列积压 > 10000 → 触发限流 | P0 | Sub PRD §扩展性 |
| 重试间隔 | 指数退避（30s, 2min, 5min） | P0 | Sub PRD §可靠性 |
| 投递成功率 | 99.5%（含重试） | P0 | Sub PRD §Success Metrics |
| 静默时段 | 严格抑制，不休眠 | P0 | Sub PRD §功能 |
| 水平扩展 | 支持 Dispatcher 水平扩展 | P1 | Sub PRD §Scalability |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| NotificationDelivery | Own | CR | 投递记录（通道、状态、延迟、重试次数） |
| DeliveryChannelConfig | Own | CRUD | 通道配置（API Key、优先级、权重、健康状态） |
| NotificationPreference | Read | R | 读取用户通知偏好（含静默时段）— 归属 User Preferences 域 |
| DeliveryReceipt | Own | CR | 通道回执记录（delivery_id, channel, status, raw_response）— 回调处理 |

## 依赖关系

- **依赖**：Push/Email/SMS 通道 feature（调用 deliverPush/deliverEmail/deliverSms）、User Preferences（读取通知偏好和静默时段）、Alert Engine（消费 AlertTriggered 事件）
- **被依赖**：无

## Mock 数据

```json
{
  "mock_dispatch_push": {
    "input": {
      "alert_id": "alert_001",
      "user_id": "user_001",
      "title": "BTC/USD 价格提醒",
      "body": "BTC 已突破 $70,000",
      "channels": ["push"]
    },
    "output": {
      "delivery_ids": ["del_001"],
      "status": "queued"
    }
  },
  "mock_channel_fallback": {
    "scenario": "Push 不可用时自动降级到 Email",
    "input": { "channels": ["push", "email"] },
    "output": {
      "push_result": { "status": "failed", "error": "device_offline" },
      "email_fallback": { "status": "delivered", "latency_ms": 45000 }
    }
  }
}
```

## 验收条件

- [ ] AC-1: AlertTriggered 事件入队到派发通道延迟 < 500ms
- [ ] AC-2: 队列积压 > 10000 时触发背压限流
- [ ] AC-3: 投递失败后指数退避重试（max 3 次）
- [ ] AC-4: 通道故障时自动降级到下一优先通道
- [ ] AC-5: 静默时段通知被抑制，不休眠
- [ ] AC-6: getDeliveryStatus 返回准确的投递状态
- [ ] AC-7: testChannel 正确返回通道健康状态
- [ ] AC-8: PreferencesChanged 事件刷新缓存的用户偏好（< 5s 生效）
- [ ] ACC-9: PremiumTierChanged 事件触发 Premium 降级用户 SMS 通道禁用（< 5s）
- [ ] AC-10: 通道回执（DeliveryReceipt）正确记录并持久化

## 技术约束

- Bull 队列 + Redis 做投递缓冲
- Node.js（与 Sub PRD 技术栈一致）
