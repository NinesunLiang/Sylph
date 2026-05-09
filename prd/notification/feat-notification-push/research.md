# Research: Notification Push Channel

> 基于 `prd/notification/feat-notification-push/prd.md` · 2026-05-09
> Feature 职责：Push 通知投递 — Firebase Cloud Messaging 集成

---

## 关键调用链路

```
Dispatcher → deliverPush(device_token, title, body, data)
  ↓
├─ 1. OAuth 2.0 鉴权
│      Google Service Account → access_token (缓存 50min)
│      refresh: 提前 5min 自动刷新
│
├─ 2. 构建 FCM HTTP v1 消息
│      POST https://fcm.googleapis.com/v1/projects/{project}/messages:send
│      {
│        message: {
│          token: device_token,
│          notification: { title, body },
│          data: { alert_id, ... }
│        }
│      }
│
├─ 3. 投递状态解析
│      ├─ 200 OK          → status=delivered
│      ├─ 404 NOT_FOUND    → status=failed, error=token_expired → 清理 DeviceToken
│      ├─ 429 TOO_MANY     → status=failed, error=rate_limited → Dispatcher 重试
│      └─ 5xx              → status=failed, error=server_error → 重试
│
└─ 4. 返回 Dispatcher: {delivery_id, status, latency_ms}

设备令牌管理:
  registerToken(user_id, device_token, platform):
    → DeviceToken.upsert({user_id, device_token, platform, last_active_at})
  
  unregisterToken(device_token):
    → DeviceToken.delete
  
  token 过期清理:
    FCM 返回 NOT_FOUND → DeviceToken.delete(device_token)
    定时任务: 清理 last_active_at > 90 天的 token
```

## 数据流

```
deliverPush:
  Dispatcher 调用 → FCM 客户端 → FCM API → 响应解析 → 返回

DeviceToken CRUD:
  注册 → Upsert DeviceToken
  更新 → 刷新 last_active_at
  注销 → 软删除（保留 7 天后物理删除）

平台差异:
  iOS: notification.title + notification.body → APNs 展示
  Android: 同上 + data payload → 前台 FCM 接收
  data payload 始终包含: alert_id, symbol, price, condition_type
```

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | FCM HTTP v1 vs legacy API？ | HTTP v1（OAuth 2.0），2024+ 必须迁移 |
| Q2 | iOS 通过 FCM 代理 APNs 的延迟？ | FCM→APNs 额外 < 1s，可接受 |
| Q3 | 多设备去重？ | 同一 alert 推送到用户所有设备，不做去重 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 投递延迟 | < 10 秒 (P95) | prd.md §非功能要求 |
| 平台支持 | iOS (APNs via FCM) + Android | prd.md §功能边界 |
| OAuth 凭据 | Service Account JSON | prd.md §技术约束 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| FCM 配额限制 | 🟡 P2 | 每日 10M 条配额 | 监控 + 配额预警 + 降级 Email |
| OAuth token 过期 | 🟡 P2 | access_token 过期 FCM 拒绝 | 提前 5min 刷新 + 失败重试 |
| 令牌膨胀 | 🟢 P3 | 僵尸 token 累积 | 90 天未活跃 → 自动清理 |
| FCM 服务中断 | 🟡 P2 | GCP 区域故障 | 多区域部署 + 降级 Email |
| 推送 payload 过大 | 🟢 P3 | FCM 限制 4KB | data payload 精简, 超长截断 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | FCM HTTP v1 API 结构引用 firebase.google.com/docs, 不自创 |
| 隐私防线 | Service Account JSON 仅 env 引用, 代码中无明文路径 |
| 范围冻结 | 只做 Push 投递, 不涉及设备管理 UI |

### kernel.md §错误处理铁律
- Hook 永不阻塞: FCM 超时 → 返回 failure, Dispatcher 降级 (不阻塞整体)
- Error DNA: FCM 429/5xx 自动记录
- 非硬编码: Service Account 路径 env 配置, fail-fast 启动

### 反模式防范 (claude-next.md)
- R31: FCM API Key 受 permission-gate 保护
- R27: "投递延迟 < 10s" → 不自称, 必须有监控
- [seed:general] 修改 DeviceToken 接口前查所有引用方

## 实现路径建议

1. **Phase 1**: FCM HTTP v1 客户端 + OAuth 鉴权 + 基本推送
2. **Phase 2**: 设备令牌管理 CRUD + 注册/注销
3. **Phase 3**: 回执处理 + token 过期清理 + 90 天清理定时任务
