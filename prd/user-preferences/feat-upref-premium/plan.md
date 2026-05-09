# Plan: UpRef Premium Management

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: PremiumSubscription CRUD + getPremiumStatus + feature-gate

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/premium/premium-store.ts`, `src/user-preferences/premium/get-premium-status.ts`, `src/user-preferences/premium/feature-gate.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/user-preferences/premium/` |

**验收标准：**
- [ ] PremiumSubscription CRUD (PostgreSQL)
- [ ] getPremiumStatus: 返回 {tier, features, expires_at}
- [ ] Redis 缓存: tier:{user_id}, TTL 5min
- [ ] feature-gate: free → 3 features, premium → 全部
- [ ] 无订阅用户 → 返回 {tier: "free", ...}

**边界/错误：**
- PremiumSubscription 不存在 → NOT_FOUND → 默认 free
- 订阅已过期 → expires_at < now → 返回 tier=free (即使 status=active)
- Redis cache miss → 回源 PostgreSQL + 写缓存
- feature 列表由 feature-gate 动态计算 (非 DB 存储)

### Task 2: Stripe Checkout + upgrade/cancelPremium

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/premium/stripe-client.ts`, `src/user-preferences/premium/upgrade-premium.ts`, `src/user-preferences/premium/cancel-premium.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/user-preferences/premium/upgrade-premium.ts` |

**验收标准：**
- [ ] Stripe Checkout Session 创建 (plan→price_id 映射, env 配置)
- [ ] upgradePremium 返回 {status, invoice_url, session_id}
- [ ] cancelPremium: at_period_end=true, 更新 DB
- [ ] API Key 从 env 读取, 无硬编码

**边界/错误：**
- plan 不合法 → 400 VALIDATION_ERROR
- Stripe API 超时 → 500 PAYMENT_FAILED + 重试 3 次
- 已 Premium 用户再次 upgrade → 返回当前状态 (幂等)
- 已 cancelled 用户 cancel → 幂等, 返回当前 cancelled_at
- API Key env 缺失 → fail-fast 启动 (kernel.md §非硬编码)

### Task 3: Webhook + 事件发布 + 自动降级

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/premium/stripe-webhook.ts`, `src/user-preferences/premium/premium-event-publisher.ts`, `src/user-preferences/premium/auto-downgrade.ts` |
| 预估行数 | ~70 行 |
| 回滚方案 | `git checkout -- src/user-preferences/premium/stripe-webhook.ts` |

**验收标准：**
- [ ] Stripe Webhook 签名校验 (Stripe-Signature + webhook secret)
- [ ] event.id 幂等检查 (Redis, TTL 24h)
- [ ] payment_intent.succeeded → PremiumSubscription 更新 + 事件发布
- [ ] PremiumTierChanged 事件: {user_id, old_tier, new_tier} (→ 3 consumers)
- [ ] 每日 03:00 自动降级: expires_at < now → tier=free

**边界/错误：**
- 签名校验失败 → 400 (kernel.md §防御性规则)
- 已处理的 event.id → 200 (跳过, 幂等)
- 事件发布失败 → 重试 3 次, 第 3 次 → 死信队列
- 自动降级中 DB 连接断开 → 跳过本轮, 下次 cron 再试
- Stripe Webhook 必须在 2s 内响应 → 异步处理耗时逻辑

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 订阅 CRUD + feature gate | Jest | free/premium features 正确 |
| 集成 | Stripe API (mock) | Jest | Checkout/取消/Webhook 签名 |
| 集成 | 事件发布 (mock bus) | Jest | PremiumTierChanged 载荷 |
| 集成 | 自动降级 | Jest (mock timer) | 03:00 cron, 过期检测 |
| 安全 | API Key 硬编码检查 | Jest | 搜索 env 引用, 无硬编码 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/user-preferences/premium/premium-store.ts` | 新增 | PostgreSQL + Redis |
| `src/user-preferences/premium/get-premium-status.ts` | 新增 | 状态查询 (缓存优先) |
| `src/user-preferences/premium/feature-gate.ts` | 新增 | 功能门禁 (动态计算) |
| `src/user-preferences/premium/stripe-client.ts` | 新增 | Stripe API 客户端 |
| `src/user-preferences/premium/upgrade-premium.ts` | 新增 | Checkout Session |
| `src/user-preferences/premium/cancel-premium.ts` | 新增 | 取消 (at_period_end) |
| `src/user-preferences/premium/stripe-webhook.ts` | 新增 | 签名 + 幂等 + 路由 |
| `src/user-preferences/premium/premium-event-publisher.ts` | 新增 | PremiumTierChanged |
| `src/user-preferences/premium/auto-downgrade.ts` | 新增 | 03:00 cron 降级 |

---

## 非范围

- 不实现具体 feature 功能（仅权限门禁）
- 不实现用户认证（由现有 OAuth 负责）
- 不实现通知偏好管理（由 feat-upref-channels 负责）
- 不实现多币种计费（v2 计划）
