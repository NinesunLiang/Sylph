# Plan: Notification SMS Channel

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: Twilio API 集成 + 基本发送

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/sms/twilio-client.ts`, `src/notification/sms/deliver-sms.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/notification/sms/` |

**验收标准：**
- [ ] Twilio API (POST Messages.json) 可正常发送
- [ ] E.164 号码格式校验
- [ ] deliverSms 返回 {delivery_id, status, latency_ms}

**边界/错误：**
- Twilio 返回 400 (invalid phone) → 校验错误，不重试
- Twilio 返回 429 (rate limited) → failure, Dispatcher 重试
- Twilio 返回 5xx → failure, 重试
- phone_number 非 E.164 → 同步校验失败
- StatusCallback 验证 Twilio 签名 → 无效签名 400
- delivery_id 格式: `sms_{uuid_v4_short}`

### Task 2: 频率限制（滑动窗口）

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/sms/rate-limiter.ts`, `src/notification/sms/sms-rate-limit-store.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/notification/sms/rate-limiter.ts` |

**验收标准：**
- [ ] 同一用户 5 分钟内第 2 条被拦截
- [ ] Redis atomic INCR 防竞态（读后写一致性）
- [ ] 频率限制返回 retry_after_sec
- [ ] 滑动窗口精确（基于 last_sent_at）

**边界/错误：**
- Redis 断连 → 降级为放过（宁可多发一次，不可漏发告警通知）
- 同用户并发请求 → Redis INCR 原子保证
- last_sent_at 缺失 → 视为首次发送

### Task 3: E2E 加密 + 回执处理

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/sms/sms-encrypt.ts`, `src/notification/sms/sms-receipt-handler.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/notification/sms/sms-encrypt.ts` |

**验收标准：**
- [ ] SMS 内容 AES-256-GCM 加密
- [ ] 每用户独立密钥（KMS 管理）
- [ ] Key 每 90 天轮换，旧 key 保留 7 天
- [ ] 投递回执正确解析（同步 + 异步）
- [ ] failed → Dispatcher 重试/降级

**边界/错误：**
- KMS 不可达 → 缓存密钥（max 1h），超时后阻塞
- 加密失败 → 返回 failure，不发送明文
- 解密历史消息（旧 key）→ 按 key_id 查找对应密钥
- StatusCallback 签名验证失败 → 400，不处理

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 频率限制逻辑 + 滑动窗口 | Jest | 5 分钟精确, Redis atomic |
| 单元 | 加密/解密 | Jest | AES-256-GCM, KMS mock |
| 单元 | Key 轮换逻辑 | Jest | 90 天轮换, 7 天保留 |
| 集成 | Twilio API (mock) | Jest | 200/400/429/5xx + StatusCallback |
| 集成 | Redis 断连 + 恢复 | Jest mock | 降级放过, 恢复后正常 |
| 安全 | 明文检查 | Jest | 加密前→密文, 无明文泄漏 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/notification/sms/twilio-client.ts` | 新增 | Twilio 客户端 |
| `src/notification/sms/deliver-sms.ts` | 新增 | 发送接口 |
| `src/notification/sms/rate-limiter.ts` | 新增 | 频率限制 |
| `src/notification/sms/sms-rate-limit-store.ts` | 新增 | 频率存储 |
| `src/notification/sms/sms-encrypt.ts` | 新增 | 内容加密 |
| `src/notification/sms/sms-receipt-handler.ts` | 新增 | 回执处理 |

---

## 非范围

- 不实现 Premium 权限校验（由 Dispatcher 上游保证）
- 不实现 SMS 2FA（由 User Preferences feat-upref-2fa 负责）
- 不实现投递决策与重试编排（由 Dispatcher 负责）
