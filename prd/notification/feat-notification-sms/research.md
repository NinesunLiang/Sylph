# Research: Notification SMS Channel

> 基于 `prd/notification/feat-notification-sms/prd.md` · 2026-05-09
> Feature 职责：SMS 通知投递 — Twilio 集成（仅 Premium）

---

## 关键调用链路

```
Dispatcher → deliverSms(phone_number, message)
  ↓
├─ 0. 【前置门禁 — Dispatcher 保证】
│     检查 UserTierCache: tier=premium → 放行
│     tier=free → SMS 通道禁用 → 跳过
│
├─ 1. 频率限制检查（SmsRateLimit）
│     查询 last_sent_at < now - 5min?
│     ├─ 通过 → 更新 SmsRateLimit → 继续发送
│     └─ 命中 → 返回 rate_limited, retry_after_sec → Dispatcher 不重试
│
├─ 2. 内容加密（E2E）
│     AES-256-GCM 加密 message
│     Key: 每个 user_id 独立密钥（KMS 管理）
│
├─ 3. Twilio API 发送
│     POST /2010-04-01/Accounts/{sid}/Messages.json
│     { To: phone, From: {twilio_number}, Body: {encrypted_message} }
│     Auth: Basic base64({sid}:{auth_token})
│
├─ 4. 投递状态
│     同步响应:
│     ├─ queued/sent/delivered → status=delivered
│     └─ failed/undelivered    → status=failed
│     异步回调（StatusCallback）:
│     └─ 更新最终状态
│
└─ 5. 返回 Dispatcher: {delivery_id, status, latency_ms}

频率限制:
  SmsRateLimit {user_id, last_sent_at, count_last_5min}
  滑动窗口: count_last_5min ≥ 1 → 拦截
  (v1: 简单窗口; v2: 精确滑动窗口)
```

## 数据流

```
deliverSms:
  Dispatcher 调用 → (频率检查) → 加密 → Twilio API → 响应解析 → 返回

Premium 门禁:
  由 Dispatcher 在调用 deliverSms 前检查 UserTierCache
  (tier=free → 不调用 deliverSms)

E2E 加密:
  user_id → KMS 获取密钥 → AES-256-GCM encrypt → base64
  Key 轮换: 每 90 天, 旧 key 保留 7 天用于解密历史消息
```

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | E2E 加密方案？ | AES-256-GCM, 每用户独立密钥, KMS 管理 |
| Q2 | 频率限制窗口？ | v1 简单 5min 窗口, v2 滑动窗口 |
| Q3 | 国际号码格式？ | E.164 统一, 发送时 + 前缀 |
| Q4 | Twilio StatusCallback 安全？ | 验证 Twilio 签名 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 投递延迟 | < 90 秒 (P95) | prd.md §非功能要求 |
| 频率限制 | 1 条/5 分钟/用户 | prd.md §非功能要求 |
| 内容加密 | 必须 E2E 加密 | prd.md §非功能要求 |
| 用户限制 | 仅 Premium | prd.md §非功能要求 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| SMS 成本超支 | 🟡 P1 | 大量 SMS 触发费用飙升 | 频率限制 + Premium 门禁 + 预算告警 |
| 加密密钥泄露 | 🟡 P2 | KMS 密钥泄露 → 历史内容可读 | KMS 自动轮换 + 审计 |
| Twilio API 限流 | 🟡 P2 | 超过 1 条/秒 配额 | 队列排队 + 监控 |
| 频率限制竞态 | 🟡 P2 | 并发请求同时通过检查 | Redis atomic INCR + 读后写 |
| 号码被标记为 spam | 🟢 P3 | 用户投诉 → 运营商拦截 | 退订管理 + 发送频率控制 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | Twilio API 结构引用 twilio.com/docs, E2E 加密引用 NIST AES-256-GCM |
| 隐私防线 | SMS 内容 E2E 加密 (AES-256-GCM), 密钥 KMS 管理, 代码无明文 |
| 范围冻结 | 只做 SMS 投递, 不涉及 Premium 权限判断 (Dispatcher 上游负责) |

### kernel.md §错误处理铁律
- Hook 永不阻塞: Twilio 超时 → 返回 failure, Dispatcher 降级
- Error DNA: 加密失败自动记录 (含 key_id, 不含明文)
- 隐私红线: SMS 内容不入日志, E2E 加密后传输

### 反模式防范 (claude-next.md)
- R27: "投递延迟 < 90s" + "频率限制 1条/5min" → 不自称, 必须有监控
- R24: 清理脚本 `for x in $SMS_QUEUE` → `set -f`
- [seed:general] KMS 密钥轮换接口修改前查所有 consumer

## 实现路径建议

1. **Phase 1**: Twilio API 集成 + 基本发送（deliverSms）
2. **Phase 2**: 频率限制（滑动窗口 5min, Redis atomic）
3. **Phase 3**: E2E 加密（AES-256-GCM + KMS）+ 回执处理
