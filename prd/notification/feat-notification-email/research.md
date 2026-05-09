# Research: Notification Email Channel

> 基于 `prd/notification/feat-notification-email/prd.md` · 2026-05-09
> Feature 职责：Email 通知投递 — SendGrid 集成

---

## 关键调用链路

```
Dispatcher → deliverEmail(to, subject, html, text)
  ↓
├─ 1. 模板渲染: HTML (Handlebars/SendGrid Dynamic) + 纯文本
│      变量替换: {{symbol}}, {{price}}, {{alert_type}}
│      HTML 转义: XSS 防护
│
├─ 2. SendGrid API v3 发送
│      POST /v3/mail/send
│      { personalizations: [{to, subject}], content: [{type, value}] }
│      Headers: Authorization Bearer ${SENDGRID_API_KEY}
│
├─ 3. 投递状态处理（Webhook 回调）
│      POST /webhook/sendgrid/event
│      events[]: {event, email, timestamp, sg_event_id, reason}
│      ├─ delivered → status=delivered, latency_ms
│      ├─ bounced  → BounceRecord.create(address, reason, timestamp)
│      │              → 标记地址不可用（N 次退信后永久标记）
│      ├─ open     → 可选记录
│      └─ dropped  → status=failed, error=reason
│
└─ 4. 返回 Dispatcher: {delivery_id, status, latency_ms}

退信管理:
  BounceRecord.check(address):
    → count ≥ 3 → permanent_bounce → 禁止后续投递
    → count < 3 → transient_bounce → 可重试
```

## 数据流

```
deliverEmail:
  Dispatcher 调用 → 模板渲染 → SendGrid API → 返回 delivery_id
  → Dispatcher 更新 NotificationDelivery

SendGrid Webhook 回调:
  Webhook 接收 → 事件解析 → BounceRecord/状态更新
  → (异步, 不影响主投递流程)

模板存储:
  EmailTemplate: {id, name, html_body, text_body, variables[]}
  → 渲染时按 template_id 获取 → 变量替换 → 构建 content
```

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | SendGrid Dynamic Templates vs 本地渲染？ | 本地渲染优先（减少 API 调用），SG Templates 兜底 |
| Q2 | Webhook 安全？ | 验证 SendGrid 签名（verify webhook） |
| Q3 | 退信 N 值？ | N=3，同一地址连续 3 次退信后永久标记 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 投递延迟 | < 60 秒 (P95) | prd.md §非功能要求 |
| 退信处理 | 自动标记，不反复投递 | prd.md §非功能要求 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| SendGrid API 限流 | 🟡 P2 | 超过发送配额（100 封/秒） | 队列排队 + Backoff + 配额监控 |
| 退信风暴 | 🟡 P2 | 大量无效地址 → 声誉下降 | 即时标记 + 冷地址预热 + 清零策略 |
| 模板注入 | 🟢 P3 | 变量替换 XSS | HTML 转义 (escape/sanitize) + CSP |
| Webhook 重放 | 🟡 P2 | 重复事件处理 | sg_event_id 幂等去重 |
| API 密钥泄露 | 🟡 P1 | SENDGRID_API_KEY 泄露 | 环境变量 + 定期轮换 + 最小权限 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | SendGrid API 结构引用 stripe.com/docs (SendGrid 文档), 不自创 |
| 隐私防线 | SENDGRID_API_KEY env 读取, 代码中无明文; Webhook 签名校验 |
| 范围冻结 | 只做 Email 投递, 不涉及用户地址管理 |

### kernel.md §错误处理铁律
- API Key 缺失 → fail-fast 启动报错 (非运行时炸)
- Error DNA: 退信异常自动记录至 error-dna.jsonl
- 修复 3 轮上限: SendGrid API 失败 → 指数退避重试 (max 3)

### 反模式防范 (claude-next.md)
- R31: sendgrid API Key 受 permission-gate 保护 (env 级别)
- R27: "投递延迟 < 60s" → 不自称, 必须有端到端数据
- R24: 退信清理脚本 `for x in $BOUNCE_RECORDS` → `set -f`

## 实现路径建议

1. **Phase 1**: SendGrid API 客户端 + 基本发送
2. **Phase 2**: 模板渲染（HTML + 文本 + 变量替换 + XSS 防护）
3. **Phase 3**: Webhook 回调接收 + 退信管理 + 幂等去重
