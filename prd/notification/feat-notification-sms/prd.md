# Feature: Notification SMS Channel

> 所属 Sub PRD：Notification Delivery
> 职责：SMS 通知投递通道 — Twilio 集成（仅 Premium）

## 功能边界

- **负责**：
  - Twilio API 集成与 SMS 发送
  - SMS 投递延迟保障（< 90 秒 P2）
  - 发送频率限制（1 条/5 分钟/用户 P0）
  - E2E 加密（SMS 内容端到端加密 P0）
  - 投递状态回执处理

- **不负责**：
  - 用户 Premium 权限校验（由 User Preferences 负责）
  - SMS 2FA（由 User Preferences 2FA 模块负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `deliverSms` | inbound | phone_number, message | {delivery_id, status, latency_ms} |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 投递延迟 | < 90 秒（P95） | P2 |
| 频率限制 | 同一用户最多 1 条/5 分钟 | P0 |
| 内容加密 | SMS 内容必须 E2E 加密 | P0 |
| 用户限制 | 仅 Premium 用户可用 | P0 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| SmsRateLimit | Own | CR | 用户发送频率记录（user_id, last_sent_at） |

## 依赖关系

- **依赖**：Dispatcher（调用方）、Twilio API（第三方）、User Preferences（Premium 校验）
- **被依赖**：Dispatcher（消费 deliverSms 接口）

## Mock 数据

```json
{
  "mock_sms_delivery": {
    "input": { "phone_number": "+1234567890", "message": "BTC $70,005 - 价格提醒" },
    "output": { "delivery_id": "sms_001", "status": "delivered", "latency_ms": 1200 }
  },
  "mock_sms_rate_limited": {
    "scenario": "5 分钟内重复发送被拦截",
    "input": { "phone_number": "+1234567890", "message": "ETH $3,500" },
    "output": { "delivery_id": null, "status": "rate_limited", "retry_after_sec": 240 }
  }
}
```

## 验收条件

- [ ] AC-1: SMS < 90 秒到达（P95）
- [ ] AC-2: 同一用户 5 分钟内第 2 条被频率限制拦截
- [ ] AC-3: SMS 内容 E2E 加密
- [ ] AC-4: 非 Premium 用户调用被拒绝

## 技术约束

- Twilio API
- Premium 订阅校验由上游调用方保证
