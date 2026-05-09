# Research: UpRef Notification Channels

> 基于 `prd/user-preferences/feat-upref-channels/prd.md` · 2026-05-09
> Feature 职责：通知渠道偏好管理 + 静默时段 + 测试通知 + 偏好事件发布

---

## 关键调用链路

```
用户打开通知偏好设置
  └─→ GET /api/preferences/{user_id} → getPreferences(user_id)
        ├─→ 读取 NotificationPreference (PostgreSQL)
        │     └─→ cache: Redis (npref:{user_id}, TTL 30s, stale-while-revalidate)
        ├─→ 返回 {channels, quiet_hours, tier}
        └─→ 404 → NOT_FOUND (用户未设置过偏好)

用户更新偏好
  └─→ PUT /api/preferences/{user_id} → updatePreferences(user_id, preferences)
        ├─→ 校验 (validation layer):
        │     ├─→ SMS.enabled → 检查 User2FA.verified (feat-upref-2fa)
        │     │     └─→ 未验证 → 400 2FA_REQUIRED + redirect_url
        │     ├─→ quiet_hours: start < end (跨天支持: 22:00 < 08:00 → 有效)
        │     ├─→ timezone: 必须是 IANA timezone (e.g., "America/New_York")
        │     └─→ channels: 至少一个 enabled = false (允许全关)
        ├─→ 乐观锁: UPDATE WHERE user_id=$1 AND version=$old_version
        │     └─→ version 不匹配 → 409 CONFLICT
        ├─→ 写入 NotificationPreference (PostgreSQL)
        ├─→ 失效 Redis 缓存 (npref:{user_id})
        ├─→ 发布 PreferencesChanged 事件 (→ Alert Engine + Notification Delivery)
        │     {event: "PreferencesChanged", user_id, changed_fields, timestamp}
        │     └─→ event latency < 5s (prd.md P0 NFR)
        └─→ 返回 updated_preferences

通知测试发送
  └─→ POST /api/preferences/{user_id}/test → testNotification(user_id, channel)
        ├─→ 检查通道是否已启用 (enabled=true)
        ├─→ SMS → 检查 User2FA.verified
        ├─→ 调用 Notification Delivery testChannel(channel, user_id)
        │     └─→ response: {status, delivery_id}
        ├─→ 返回 {status, delivery_id}
        └─→ channel 未启用 → 400 CHANNEL_DISABLED

静默时段 (quiet hours)
  ├─→ 配置: {enabled, start: "HH:mm", end: "HH:mm", timezone: "IANA"}
  ├─→ 跨天支持: start=22:00, end=08:00 → 22:00-23:59 + 00:00-08:00
  ├─→ 时区转换: 存储为 UTC, 按用户 timezone 解释
  │     └─→ 判断: now_tz >= start || now_tz < end (跨天)
  └─→ Notification Delivery 在发送前调用 isInQuietHours(user_id)
        └─→ 命中 → 队列到 quiet_hours.end 后发送

PreferencesChanged 事件消费方 (sub-prds/domain-user-preferences.md):
  ├─→ Alert Engine: 刷新通知偏好缓存 (npref:{user_id})
  └─→ Notification Delivery: 刷新渠道配置
```

## 数据流

| 接口 | 方向 | 输入 | 输出 | 缓存 |
|------|------|------|------|------|
| getPreferences | inbound | user_id | {channels, quiet_hours, tier} | Redis 30s + stale |
| updatePreferences | inbound | user_id, preferences | updated_preferences | 失效缓存 |
| testNotification | inbound | user_id, channel | {status, delivery_id} | — |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 偏好更新生效 | < 30 秒 | prd.md §非功能要求 |
| SMS 2FA 前置 | SMS.enabled 必须 User2FA.verified | prd.md §Security |
| 事件延迟 | PreferencesChanged 入队 < 5s | prd.md §非功能要求 |
| 乐观锁 | updatePreferences version 校验 | kernel.md §并发控制 |
| 跨天静默 | start > end 视为跨天 | prd.md §功能边界 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 静默时段时区支持？ | IANA timezone, 默认 UTC, 存储时转换为 UTC |
| Q2 | 偏好变更生效？ | < 30s: 事件驱动 + 缓存 TTL 30s |
| Q3 | 多设备 Push 令牌？ | device_tokens 列表在 NotificationPush 域管理, 本域只存 enabled |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 并发更新 | 🟡 P2 | 多端同时修改偏好 | 乐观锁 + version 字段 |
| SMS 未 2FA 绕过 | 🟡 P2 | 直接调 SMS API 绕过 UI | updatePreferences 时服务端校验 User2FA |
| 事件丢失 | 🟡 P2 | PreferencesChanged 未送达 | 事件发布确认 + 定时全量刷新 (5min) |
| 缓存一致 | 🟡 P2 | Redis 缓存和 DB 不一致 | TTL 30s + 变更时主动失效 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | 缓存 TTL 30s 引用 prd.md NFR, 不自设 |
| 范围冻结 | 只管理偏好, 不涉及投递 |
| 证据门禁 | "更新 < 30s" VERIFIED: 端到端计时 |

### kernel.md §错误处理铁律
- 乐观锁 409 → 通知用户刷新重试, 不自动覆盖
- Redis 缓存失效失败 → TTL 兜底, 不阻塞更新

### 反模式防范 (claude-next.md)
- [seed:typescript] API 响应类型: `PreferencesResponse = { channels, quiet_hours, tier }`
- R27: "更新 < 30s" 不自称, 必须有实测数据
- R24: Bash 脚本 `for x in $USERS` → `set -f`

## 实现路径建议

1. **Phase 1**: NotificationPreference CRUD + get/updatePreferences (含乐观锁)
2. **Phase 2**: 静默时段配置 + 跨天支持 + IANA timezone 校验
3. **Phase 3**: PreferencesChanged 事件发布 + 缓存失效 + testNotification
