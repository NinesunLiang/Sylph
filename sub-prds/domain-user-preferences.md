# Sub PRD: User Preferences & Premium

> 主 PRD：`mothership-prd.md` | 拆解日期：2026-05-08

## 功能边界（黑盒）

- **负责**：
  - 通知渠道偏好管理（Push/Email/SMS 独立开关）
  - 静默时段（Quiet Hours）配置
  - SMS 通知的双因素认证（2FA）设置
  - Premium 订阅管理与计费
  - 用户数据隐私（GDPR 合规、历史数据删除）
  - 通知测试发送（Test Delivery）

- **不负责**：
  - 告警创建/管理（由 Alert Engine + Dashboard 负责）
  - 通知实际投递（由 Notification Delivery 负责）
  - 行情数据（由 TradingView Integration 负责）

## 对外接口契约

### 接口列表

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `getPreferences` | inbound | user_id | {channels, quiet_hours, tier} | NOT_FOUND |
| `updatePreferences` | inbound | user_id, preferences | updated_preferences | VALIDATION_ERROR |
| `setup2FA` | inbound | user_id, phone | 2fa_status | ALREADY_CONFIGURED |
| `verify2FA` | inbound | user_id, code | token | INVALID_CODE |
| `getPremiumStatus` | inbound | user_id | {tier, features, expires_at} | NOT_FOUND |
| `upgradePremium` | inbound | user_id, plan | {status, invoice_url} | PAYMENT_FAILED |
| `cancelPremium` | inbound | user_id | {cancelled_at, access_until} | NOT_FOUND |
| `testNotification` | inbound | user_id, channel | {status, delivery_id} | CHANNEL_FAILURE |
| `deleteUserData` | inbound | user_id | 204 (GDPR 删除) | NOT_FOUND |

### 事件 / 消息

| 事件名 | 发布方 | 订阅方 | 载荷 |
|--------|--------|--------|------|
| `PreferencesChanged` | User Preferences | Alert Engine + Notification Delivery | user_id, changed_fields |
| `PremiumTierChanged` | User Preferences | Alert Engine + Dashboard + Notification Delivery | user_id, old_tier, new_tier |

## 非功能契约

| 属性 | 约束值 | 优先级 | 来源 |
|------|--------|--------|------|
| 偏好更新生效时间 | < 30 秒 | P0 | PRD §用户体验 |
| GDPR 数据删除 | 72 小时内完成 | P0 | PRD §Security |
| 计费准确性 | 99.99% | P0 | PRD §Revenue |
| 事件延迟 | 偏好变更事件入队 < 5 秒（Notification Delivery 消费端要求） | P0 | PRD §性能 |
| SMS 2FA 必须 | SMS 功能前置 | P0 | PRD §Security |
| E2E 加密（依赖 Notification Delivery） | SMS 通知端到端加密由 Notification Delivery 域保障 | P0 | PRD §Security |

## Mock 数据

```json
{
  "mock_preferences": {
    "user_id": "user_001",
    "channels": {
      "push": {"enabled": true, "device_tokens": ["ios_xxx", "android_yyy"]},
      "email": {"enabled": true, "address": "user@example.com"},
      "sms": {"enabled": false, "phone": null, "2fa_verified": false}
    },
    "quiet_hours": {
      "enabled": true,
      "start": "22:00",
      "end": "08:00",
      "timezone": "America/New_York"
    },
    "tier": "premium",
    "premium_features": ["technical_indicators", "ai_pattern_detection", "sms"]
  },
  "mock_premium_upgrade": {
    "request": {"user_id": "user_001", "plan": "premium_monthly"},
    "response": {
      "status": "success",
      "tier": "premium",
      "features": ["technical_indicators", "ai_pattern_detection", "sms", "unlimited_alerts"],
      "invoice_url": "https://billing.example.com/inv_001",
      "valid_from": "2026-05-08",
      "valid_until": "2026-06-08"
    }
  }
}
```

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| NotificationPreference | Own | CRUD | 通知渠道偏好、静默时段 |
| User2FA | Own | CRUD | SMS 2FA 认证状态 |
| PremiumSubscription | Own | CRUD | Premium 订阅与计费 |
| UserDataRetention | Own | CRUD | GDPR 数据留存策略 |

## 依赖关系

- **依赖**：计费系统（Stripe）、认证系统（OAuth）
- **被依赖**：Alert Engine（读取偏好）、Notification Delivery（读取渠道配置）

## 父需求追溯

| 主 PRD 章节 | 覆盖内容 |
|-------------|---------|
| §Multi-Channel Notifications - 独立开关 | 全部 |
| §User Goals - Customize alerts | 偏好配置部分 |
| §Security & Privacy - GDPR/2FA | 全部 |
| §Risk - Notification Fatigue (Quiet Hours) | 全部 |
| §Risk - SMS Cost Overruns | 全部 |
| §Premium Feature Launch | 全部 |

## 验收条件

- [ ] AC-1: 用户可独立开关 Push/Email/SMS 通知
- [ ] AC-2: 静默时段内不发送通知
- [ ] AC-3: SMS 通知要求 2FA 验证
- [ ] AC-4: Premium 升级后即时解锁对应功能
- [ ] AC-5: GDPR 数据删除请求 72 小时内完成
- [ ] AC-6: 测试通知发送可验证各通道可达性

## 技术约束

- Stripe（计费）
- 现有 OAuth 系统（认证）
- GDPR 合规要求
