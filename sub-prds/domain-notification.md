# Sub PRD: Notification Delivery

> 主 PRD：`mothership-prd.md` | 拆解日期：2026-05-08

## 功能边界（黑盒）

- **负责**：
  - 多通道通知投递（Push / Email / SMS）
  - 通知队列管理与背压控制
  - 通知投递可靠性保障（99.5% 成功率）
  - 投递重试与降级（通道故障时自动切换）
  - 通知投递延迟保障（Push < 10s, Email < 60s, SMS < 90s）
  - 静默时段（Quiet Hours）过滤执行

- **不负责**：
  - 告警条件评估（由 Alert Engine 负责）
  - 用户通知偏好设置（由 User Preferences 负责）
  - 告警管理 UI（由 Alert Dashboard 负责）

## 对外接口契约

### 接口列表

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `sendNotification` | inbound (event) | alert_id, user_id, title, body, channels | delivery_id[] | CHANNEL_FAILURE |
| `getDeliveryStatus` | inbound | delivery_id | status, channel, attempts | NOT_FOUND |
| `testChannel` | inbound | user_id, channel | success/failure | CHANNEL_CONFIG_ERROR |

注意：`testNotification`（定义于 User Preferences 域）为用户面 API，内部调用本域的 `testChannel` 执行实际通道测试。

### 事件 / 消息

| 事件名 | 发布方 | 订阅方 | 载荷 |
|--------|--------|--------|------|
| `AlertTriggered` | Alert Engine → Notification Delivery | 内部 | alert_id, symbol, price, user_id, channels |
| `PreferencesChanged` | User Preferences → Notification Delivery | 内部 | user_id, changed_fields |
| `PremiumTierChanged` | User Preferences → Notification Delivery | 内部 | user_id, old_tier, new_tier |
| `DeliveryConfirmed` | Notification Delivery | Alert Dashboard | delivery_id, alert_id, channel, timestamp |
| `DeliveryFailed` | Notification Delivery | Alert Dashboard | delivery_id, alert_id, channel, error, retry_count |

## 非功能契约

| 属性 | 约束值 | 优先级 | 来源 |
|------|--------|--------|------|
| 推送通知延迟 | < 10 秒 | P0 | PRD §FAQ |
| 邮件投递延迟 | < 60 秒 | P1 | PRD §FAQ |
| SMS 投递延迟 | < 90 秒（Premium） | P2 | PRD §FAQ |
| 投递成功率 | 99.5% | P0 | PRD §Success Metrics |
| 水平扩展 | 支持 Notification Delivery Service 水平扩展 | P1 | PRD §Scalability |
| SMS 频率限制 | 1 条/5 分钟/用户 | P0 | PRD §Risk Mitigation |
| E2E 加密 | SMS 通知端到端加密 | P0 | PRD §Security |

## Mock 数据

```json
{
  "mock_push_delivery": {
    "input": {
      "alert_id": "alert_001",
      "user_id": "user_001",
      "title": "BTC/USD 价格提醒",
      "body": "BTC 已突破 $70,000，当前价 $70,005.50",
      "channel": "push"
    },
    "output": {
      "delivery_id": "del_001",
      "status": "delivered",
      "latency_ms": 3200
    }
  },
  "mock_email_fallback": {
    "scenario": "Push 通道不可用时自动降级到 Email",
    "input": {
      "alert_id": "alert_001",
      "user_id": "user_001",
      "channels": ["push", "email"]
    },
    "output": {
      "push": {"status": "failed", "error": "device_offline"},
      "email_fallback": {"status": "delivered", "latency_ms": 45000}
    }
  }
}
```

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| NotificationDelivery | Own | CR | 投递记录（通道、状态、延迟） |
| DeliveryChannelConfig | Own | CRUD | 通道配置（API Key、优先级、权重） |
| NotificationPreference | Read | R | 读取用户通知偏好（含静默时段）— 归属 User Preferences 域 |
| EmailTemplate | Own | CRUD | 邮件模板定义（HTML + 纯文本版本）— feat-notification-email |
| BounceRecord | Own | CR | 退信记录（地址、原因、时间）— feat-notification-email |
| DeviceToken | Own | CRUD | FCM 设备令牌（含平台、最后活跃时间）— feat-notification-push |
| SmsRateLimit | Own | CR | 用户发送频率记录（user_id, last_sent_at）— feat-notification-sms |
| DeliveryReceipt | Own | CR | 通道回执记录（delivery_id, channel, status, raw_response）— feat-notification-dispatcher |

## 依赖关系

- **依赖**：Alert Engine（消费 AlertTriggered 事件）、User Preferences（读取通知渠道偏好和静默时段）
- **被依赖**：无

## 父需求追溯

| 主 PRD 章节 | 覆盖内容 |
|-------------|---------|
| §Multi-Channel Notifications (P0) | 全部 |
| §Performance - Alert trigger evaluation | 投递延迟部分 |
| §Third-Party Integrations - Firebase/SendGrid/Twilio | 全部 |
| §Risk - Alert Delivery Failure During High Volatility | 全部 |
| §Scalability - Horizontal scaling | Notification Delivery 部分 |

## 验收条件

- [ ] AC-1: Push 通知 < 10 秒到达 iOS 和 Android 设备
- [ ] AC-2: Email < 60 秒到达收件箱
- [ ] AC-3: 通道故障时自动切换到备用通道
- [ ] AC-4: 投递成功率 > 99.5%（含重试）
- [ ] AC-5: 高波动期负载测试通过（模拟 10x 流量峰值）

## 技术约束

- Firebase Cloud Messaging（Push）
- SendGrid（Email）
- Twilio（SMS，仅 Premium）
- Bull 队列 + Redis 做投递缓冲
