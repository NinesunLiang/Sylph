# Feature: Notification Push Channel

> 所属 Sub PRD：Notification Delivery
> 职责：Push 通知投递通道 — Firebase Cloud Messaging 集成

## 功能边界

- **负责**：
  - FCM 设备令牌管理与注册
  - Push 通知构建与发送（标题、正文、数据 payload）
  - 推送延迟保障（< 10 秒 P0）
  - 推送结果回执处理（成功/失败/设备离线）

- **不负责**：
  - 投递决策与重试编排（由 Dispatcher 负责）
  - 其他通道的实现

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `deliverPush` | inbound | device_token, title, body, data | {delivery_id, status, latency_ms} |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 投递延迟 | < 10 秒（P95） | P0 |
| 平台支持 | iOS (APNs via FCM) + Android | P0 |
| 离线处理 | 设备离线返回 failure，由 Dispatcher 降级 | P0 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| DeviceToken | Own | CRUD | FCM 设备令牌（含平台、最后活跃时间） |

## 依赖关系

- **依赖**：Dispatcher（调用方）、Firebase Cloud Messaging（第三方）
- **被依赖**：Dispatcher（消费 deliverPush 接口）

## Mock 数据

```json
{
  "mock_push_ios": {
    "input": { "device_token": "ios_token_001", "title": "BTC 提醒", "body": "BTC $70,005", "data": { "alert_id": "a001" } },
    "output": { "delivery_id": "push_001", "status": "delivered", "latency_ms": 3200 }
  },
  "mock_push_offline": {
    "input": { "device_token": "ios_token_offline", "title": "ETH 提醒", "body": "ETH $3,500" },
    "output": { "delivery_id": "push_002", "status": "failed", "error": "device_offline" }
  }
}
```

## 验收条件

- [ ] AC-1: iOS 设备 Push 通知 < 10 秒到达
- [ ] AC-2: Android 设备 Push 通知 < 10 秒到达
- [ ] AC-3: 设备离线时正确返回 failure 状态
- [ ] AC-4: 令牌过期/注销后自动清理

## 技术约束

- Firebase Cloud Messaging
- 令牌管理支持刷新/过期/注销
