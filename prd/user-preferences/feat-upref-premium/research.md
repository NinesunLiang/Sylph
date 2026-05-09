# Research: UpRef Premium Management

> 基于 `prd/user-preferences/feat-upref-premium/prd.md` · 2026-05-09
> Feature 职责：Premium 订阅管理与计费

---

## 关键调用链路

```
用户查询 Premium 状态
  └─→ GET /api/premium/status/{user_id} → getPremiumStatus(user_id)
        ├─→ 读取 PremiumSubscription (PostgreSQL)
        │     └─→ cache: Redis (tier:{user_id}, TTL 5min)
        ├─→ features 动态计算 (feature-gate.ts):
        │     ├─→ free: ["price_above", "price_below", "price_crosses"]
        │     └─→ premium: ["technical_indicators", "ai_pattern_detection", "sms", "unlimited_alerts"]
        ├─→ 返回 {tier, features, expires_at}
        └─→ NOT_FOUND → 用户无订阅 → 返回 {tier: "free", features: [...free], expires_at: null}

用户升级 Premium
  └─→ POST /api/premium/upgrade {user_id, plan} → upgradePremium(user_id, plan)
        ├─→ Stripe: Checkout Session 创建
        │     POST https://api.stripe.com/v1/checkout/sessions
        │     { customer, line_items, mode: "subscription", success_url, cancel_url }
        │     └─→ API Key 从 env 读取 (kernel.md §非硬编码)
        ├─→ 返回 {status: "pending", invoice_url, session_id}
        ├─→ 用户完成支付 (Stripe 托管页面)
        └─→ Stripe Webhook → 异步处理 (Task 3)

Stripe Webhook 处理
  └─→ POST /api/stripe/webhook (Stripe 推送)
        ├─→ 签名校验: Stripe-Signature header → webhook secret (env)
        │     └─→ 无效 → 400 (kernel.md §防御性规则)
        ├─→ event.id 幂等检查 (Redis: stripe_event:{id}, TTL 24h)
        │     └─→ 已处理 → 200 (跳过)
        ├─→ event.type 路由:
        │     ├─→ payment_intent.succeeded:
        │     │     ├─→ 写入 PremiumSubscription (tier=premium, 新 expires_at)
        │     │     └─→ 发布 PremiumTierChanged 事件 (→ Alert Engine + Dashboard + Notification Delivery)
        │     │           {event: "PremiumTierChanged", user_id, old_tier, new_tier, timestamp}
        │     └─→ customer.subscription.deleted:
        │           └─→ 标记 status=cancelled (access_until 不变)
        └─→ 返回 200 (Stripe 要求 2s 内响应)

用户取消 Premium
  └─→ POST /api/premium/cancel {user_id} → cancelPremium(user_id)
        ├─→ Stripe: 取消订阅 (at_period_end=true)
        │     POST /v1/subscriptions/{sub_id} (cancel_at_period_end=true)
        ├─→ 更新 PremiumSubscription (status=cancelled, cancelled_at=NOW())
        └─→ 返回 {cancelled_at, access_until}

自动降级 (每日 03:00 cron):
  └─→ 定时任务: SELECT * FROM premium_subscriptions WHERE expires_at < NOW()
        ├─→ 逐条: tier=free, published PremiumTierChanged
        └─→ 审计日志: {user_id, old_tier=premium, new_tier=free, reason: "expired"}
```

## 数据流

| 接口 | 方向 | 输入 | 输出 | 存储 |
|------|------|------|------|------|
| getPremiumStatus | inbound | user_id | {tier, features, expires_at} | PostgreSQL + Redis |
| upgradePremium | inbound | user_id, plan | {status, invoice_url} | Stripe + PostgreSQL |
| cancelPremium | inbound | user_id | {cancelled_at, access_until} | Stripe + PostgreSQL |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 计费准确性 | 99.99% | prd.md §非功能要求 |
| Stripe 集成 | Checkout + Webhook | prd.md §技术约束 |
| API Key | env 读取, 非硬编码 | kernel.md §隐私防线 |
| Webhook 签名 | Stripe-Signature 校验 | prd.md §Security |
| 幂等 | event.id 去重 24h | prd.md §Security |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | Stripe Webhook 安全？ | Stripe-Signature 校验 + event.id 幂等 |
| Q2 | 自动降级触发频率？ | 每日 03:00 cron (同 kernel.md §定时任务命名) |
| Q3 | 计费币种？ | USD v1, 多币种 v2 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| Stripe Webhook 重放 | 🟡 P2 | 重复 event | event.id 幂等 (Redis 24h) |
| 支付失败 | 🟡 P2 | 卡被拒 | Stripe 自动重试 + 邮件通知 |
| 降级延迟 | 🟢 P3 | 过期未及时降级 | 每日定时任务 + 订阅变更实时检测 |
| API Key 泄露 | 🔴 P0 | Key 写入日志/代码 | env 读取, 检查无硬编码 |
| Webhook 签名绕过 | 🔴 P0 | 伪造 webhook | Stripe-Signature 强制校验 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | Stripe API 结构从 stripe.com/docs 引用 |
| 隐私防线 | Stripe API Key env 读取, 代码中无明文 |
| 范围冻结 | 只做订阅/计费, 不实现具体 feature 功能 |

### kernel.md §错误处理铁律
- API Key 缺失 → fail-fast 启动报错
- Hook 永不阻塞: Webhook 处理 try/catch, 失败时返回 500 (Stripe 会重试)
- Error DNA: 支付异常记录至 error-dna.jsonl

### 反模式防范 (claude-next.md)
- R31: gh CLI 不涉及本 feature
- R24: 定时降级脚本 `for x in $EXPIRED` → `set -f`
- R27: 计费 99.99% 引用 stripe.com/docs 可用性说明, 不自创指标

## 实现路径建议

1. **Phase 1**: PremiumSubscription CRUD + getPremiumStatus + feature-gate (动态计算)
2. **Phase 2**: Stripe Checkout Session 创建 + upgrade/cancelPremium
3. **Phase 3**: Stripe Webhook 签名校验 + event.id 幂等 + PremiumTierChanged 发布
4. **Phase 4**: 自动降级定时任务 (每日 03:00) + 审计日志
