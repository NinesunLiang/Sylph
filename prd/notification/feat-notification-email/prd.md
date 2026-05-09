# Feature: Notification Email Channel

> 所属 Sub PRD：Notification Delivery
> 职责：Email 通知投递通道 — SendGrid 集成

## 功能边界

- **负责**：
  - SendGrid API 集成与邮件发送
  - 邮件模板渲染（HTML + 纯文本）
  - 邮件投递延迟保障（< 60 秒 P1）
  - 投递状态回执处理（已发送/已打开/已退回）
  - 发件人信誉管理（退信处理）

- **不负责**：
  - 投递决策与重试编排（由 Dispatcher 负责）
  - 用户邮件地址管理（由 User Preferences 负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `deliverEmail` | inbound | to_address, subject, body_html, body_text | {delivery_id, status, latency_ms} |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 投递延迟 | < 60 秒（P95） | P1 |
| 模板渲染 | 支持变量替换（动态内容） | P0 |
| 退信处理 | 自动标记，不反复投递已失效地址 | P0 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| EmailTemplate | Own | CRUD | 邮件模板定义（HTML + 纯文本版本） |
| BounceRecord | Own | CR | 退信记录（地址、原因、时间） |

## 依赖关系

- **依赖**：Dispatcher（调用方）、SendGrid API v3（第三方）
- **被依赖**：Dispatcher（消费 deliverEmail 接口）

## Mock 数据

```json
{
  "mock_email_delivery": {
    "input": { "to_address": "user@example.com", "subject": "价格提醒", "body_html": "<p>BTC $70,005</p>", "body_text": "BTC $70,005" },
    "output": { "delivery_id": "email_001", "status": "delivered", "latency_ms": 45000 }
  },
  "mock_email_bounce": {
    "input": { "to_address": "invalid@bounce.com", "subject": "价格提醒", "body_text": "ETH $3,500" },
    "output": { "delivery_id": "email_002", "status": "bounced", "error": "invalid_address" }
  }
}
```

## 验收条件

- [ ] AC-1: Email < 60 秒到达收件箱（P95）
- [ ] AC-2: HTML 模板变量正确替换
- [ ] AC-3: 退信地址自动标记，不再投递
- [ ] AC-4: 投递状态回执正确解析

## 技术约束

- SendGrid API v3
- 模板使用 SendGrid Dynamic Templates（或内嵌 Handlebars）
