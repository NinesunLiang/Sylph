# Plan: UpRef Notification Channels

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: NotificationPreference CRUD + 缓存

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/channels/preference-store.ts`, `src/user-preferences/channels/get-preferences.ts`, `src/user-preferences/channels/update-preferences.ts`, `src/user-preferences/channels/preference-cache.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/user-preferences/channels/` |

**验收标准：**
- [ ] getPreferences 返回 {channels, quiet_hours, tier}
- [ ] updatePreferences 校验 + 写入正确 (含 SMS 2FA 校验)
- [ ] 乐观锁: version 字段, 409 时返回冲突
- [ ] Redis 缓存: npref:{user_id}, TTL 30s, 更新时失效
- [ ] channels 全关不阻断 (允许静音所有通知)

**边界/错误：**
- 用户无偏好 (首访) → 返回默认值 {push: false, email: false, sms: false, tier: "free"}
- SMS.enabled 但 User2FA 未验证 → 400 2FA_REQUIRED + redirect_url
- 乐观锁 version 不匹配 → 409 CONFLICT + 当前值 (客户端重试)
- 跨天静默: start=22:00, end=08:00 → 有效 (跨天)
- IANA timezone 非法 → 400 VALIDATION_ERROR

### Task 2: 静默时段 + 时区

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/channels/quiet-hours.ts`, `src/user-preferences/channels/timezone-util.ts` |
| 预估行数 | ~40 行 |
| 回滚方案 | `git checkout -- src/user-preferences/channels/quiet-hours.ts` |

**验收标准：**
- [ ] 静默时段配置: {enabled, start, end, timezone}
- [ ] IANA timezone 校验 (luxon/Intl.supportedValuesOf)
- [ ] 跨天支持: start > end → 跨天
- [ ] isInQuietHours(user_id) → boolean (被 Notification Delivery 调用)
- [ ] 时区转换: 用户 timezone → UTC 存储 → 查询时转回用户 timezone

**边界/错误：**
- timezone 非法 → 使用默认 UTC
- 跨天静默: 22:00→08:00, 当前 02:00 用户时间 → 命中
- 非跨天: 08:00→22:00, 当前 02:00 → 未命中
- enabled=false → 始终返回 false (不抑制)

### Task 3: 事件发布 + 测试通知

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/channels/preference-event-publisher.ts`, `src/user-preferences/channels/test-notification.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/user-preferences/channels/preference-event-publisher.ts` |

**验收标准：**
- [ ] 偏好变更后发布 PreferencesChanged 事件 (到 Alert Engine + Notification Delivery)
- [ ] event latency < 5s (发布方计时)
- [ ] testNotification: 检查通道启用状态 → 调 Notification Delivery API
- [ ] SMS 测试 → 检查 User2FA.verified

**边界/错误：**
- 事件发布失败 → 重试 3 次 (1s), 第 3 次 → 死信队列
- testNotification 通道未启用 → 400 CHANNEL_DISABLED
- SMS test 但 2FA 未验证 → 400 2FA_REQUIRED
- Notification Delivery API 超时 → 返回 TIMEOUT (非 block)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 偏好 CRUD + 乐观锁 | Jest | version 冲突 |
| 单元 | 静默时段 + 跨天 + 时区 | Jest | start>end, timezone 转化 |
| 集成 | 事件发布 (mock bus) | Jest | PreferencesChanged 载荷 + 重试 |
| 集成 | testNotification (mock delivery) | Jest | SMS 2FA 门禁 |
| 安全 | SMS 2FA bypass | Jest | 直接更新 → 400 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/user-preferences/channels/preference-store.ts` | 新增 | 偏好持久化 |
| `src/user-preferences/channels/get-preferences.ts` | 新增 | 查询 (缓存优先) |
| `src/user-preferences/channels/update-preferences.ts` | 新增 | 更新 (乐观锁) |
| `src/user-preferences/channels/preference-cache.ts` | 新增 | Redis 缓存 (TTL 30s) |
| `src/user-preferences/channels/quiet-hours.ts` | 新增 | 静默时段 (跨天) |
| `src/user-preferences/channels/timezone-util.ts` | 新增 | IANA timezone |
| `src/user-preferences/channels/preference-event-publisher.ts` | 新增 | PreferencesChanged |
| `src/user-preferences/channels/test-notification.ts` | 新增 | 测试发送 |

---

## 非范围

- 不实现通知实际投递（由 Notification Delivery 负责）
- 不实现 SMS 2FA（由 feat-upref-2fa 负责）
- 不实现 Premium 订阅管理（由 feat-upref-premium 负责）
