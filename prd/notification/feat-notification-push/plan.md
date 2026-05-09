# Plan: Notification Push Channel

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: FCM HTTP v1 客户端 + 基本推送

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/push/fcm-client.ts`, `src/notification/push/deliver-push.ts`, `src/notification/push/fcm-auth.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/notification/push/` |

**验收标准：**
- [ ] FCM HTTP v1 API POST 正确
- [ ] OAuth 2.0 鉴权（Google Service Account, access_token 缓存 50min）
- [ ] iOS + Android 平台消息构建正确
- [ ] deliverPush 返回 {delivery_id, status, latency_ms}

**边界/错误：**
- FCM 429 → 返回 rate_limited → Dispatcher 重试
- FCM 404 → 返回 token_expired
- FCM 5xx → 返回 server_error
- Service Account JSON 文件缺失 → 启动时 fail-fast
- access_token 刷新失败 → 自动重试（max 3 次，间隔 1s）

### Task 2: 设备令牌管理

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/push/device-token-store.ts`, `src/notification/push/token-registration.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/notification/push/device-token-store.ts` |

**验收标准：**
- [ ] DeviceToken CRUD 正确
- [ ] 同一用户支持多设备（平台区分）
- [ ] token 注册/注销接口可用
- [ ] data payload 含 alert_id, symbol, price, condition_type

**边界/错误：**
- 重复注册同一 token → upsert（刷新 last_active_at）
- 注销不存在的 token → 静默成功
- 空 user_id → 校验错误，拒绝
- token 格式非法 → 校验错误，拒绝

### Task 3: 回执处理 + token 过期清理

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/push/push-receipt-handler.ts`, `src/notification/push/token-cleanup.ts` |
| 预估行数 | ~40 行 |
| 回滚方案 | `git checkout -- src/notification/push/push-receipt-handler.ts` |

**验收标准：**
- [ ] FCM NOT_FOUND → 自动清理 DeviceToken
- [ ] 推送成功 → 正确回执
- [ ] 设备离线 → 返回 failure → Dispatcher 降级
- [ ] 90 天未活跃 token 定时清理

**边界/错误：**
- 清理过程中新注册的同一 token → 先删后增（无竞态）
- 清理任务执行间隔 → 每日凌晨 03:00

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | FCM 消息构建 | Jest | iOS/Android payload 不同 |
| 单元 | token 过期判断 | Jest | 90 天精确 |
| 单元 | OAuth token 缓存 + 刷新 | Jest | 50min 缓存, 提前 5min 刷新 |
| 集成 | FCM API (mock) | Jest | 200/404/429/5xx |
| 集成 | token 注册 + 注销 | Jest | CRUD 正确 + 幂等 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/notification/push/fcm-client.ts` | 新增 | FCM 客户端 |
| `src/notification/push/fcm-auth.ts` | 新增 | OAuth 鉴权 |
| `src/notification/push/deliver-push.ts` | 新增 | 推送接口 |
| `src/notification/push/device-token-store.ts` | 新增 | 令牌存储 |
| `src/notification/push/token-registration.ts` | 新增 | 令牌注册 |
| `src/notification/push/push-receipt-handler.ts` | 新增 | 回执处理 |
| `src/notification/push/token-cleanup.ts` | 新增 | 过期清理 |

---

## 非范围

- 不实现投递决策与重试编排（由 Dispatcher 负责）
- 不实现其他通知通道
- 不实现用户偏好管理（由 User Preferences 负责）
