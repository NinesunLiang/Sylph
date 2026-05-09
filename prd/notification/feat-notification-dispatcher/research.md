# Research: Notification Dispatcher

> 基于 `prd/notification/feat-notification-dispatcher/prd.md` · 2026-05-09
> Feature 职责：通知分发核心 — 队列管理、背压控制、重试编排、通道降级、静默时段过滤、入站事件消费

---

## 关键调用链路

```
▶ 入站事件消费（3 条线）

┌─ AlertTriggered (alert_id, symbol, price, user_id, channels)
│     ↓
│  1. 解析载荷 → 查询 NotificationDeliveryConfig
│  2. 读取 User Preferences (getPreferences: 通知偏好 + 静默时段)
│  3. 【静默时段检查】→ 命中 → 丢弃（不等待不休眠），记录 suppression
│  4. 按优先级拆分通道子任务: push → email → sms
│  5. 入队 Bull 队列 (channel, user_id, alert_id, payload)
│
├─ PreferencesChanged (user_id, changed_fields)
│     ↓
│  1. 识别变更字段: channels / quiet_hours
│  2. 刷新本地缓存 NotificationPreferenceCache
│  3. 若 channels 变更 → 检查队列中该用户待发送任务 → 更新通道列表
│  4. 缓存 TTL: 5min，事件刷新后重置
│
└─ PremiumTierChanged (user_id, old_tier, new_tier)
      ↓
   1. 刷新 UserTierCache
   2. 若 new_tier=free → 禁用 SMS 通道
   3. 检查队列中该用户待发送 SMS 任务 → 移除或标记跳过
   4. 发布内部通知: 后续所有 dispatch 检查 tier

▶ 投递编排（per channel）

  Bull Worker 出队 → 调用 deliverPush/deliverEmail/deliverSms
      ↓
  ├─ 成功 → 写入 DeliveryReceipt (status=delivered, latency_ms)
  │         → 发布 DeliveryConfirmed (delivery_id, alert_id, channel, timestamp)
  │
  └─ 失败 → 写入 DeliveryReceipt (status=failed, error)
            → 重试计数 < 3?
              ├─ 是 → 重新入队（指数退避: 30s → 2min → 5min）
              └─ 否 → 记录 DeliveryReceipt (status=permanent_failure)
                      → 发布 DeliveryFailed (delivery_id, alert_id, channel, error, retry_count)
                      → 尝试下一优先通道

▶ 通道降级

  deliverPush 返回 device_offline → 标记 push 失败
  → 检查 channels 列表中下一优先级: email 可用?
    → 是 → 调用 deliverEmail
    → 否 → 调用 deliverSms
  → 所有通道失败 → 发布 DeliveryFailed (last_error)

▶ 背压控制

  Bull 队列监控: queue_size > 10000
  → 暂停 notifyQueue.add()  → 记录 backpressure_triggered
  → queue_size < 5000 → 恢复入队 → 记录 backpressure_resolved
```

## 数据流

```
事件入站:
  AlertTriggered → 偏好检查(含缓存) → 静默过滤 → 拆分通道 → Bull 入队
  PreferencesChanged → 缓存刷新 → 队列中待发任务更新
  PremiumTierChanged → 缓存刷新 → SMS 通道禁用 → 队列清理

投递执行:
  Bull Worker → 通道调用 → DeliveryReceipt 写入 → 事件发布/重试

缓存架构:
  NotificationPreferenceCache (内存, TTL 5min, 事件刷新)
  UserTierCache (内存, TTL 5min, 事件刷新)
  - 命中: 直接使用
  - 未命中: 同步读取 User Preferences API + 写入缓存
  - 事件到达: 立即刷新对应条目
```

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 队列中待发任务更新策略？ | 遍历队列 + 标记跳过（非删除），避免竞态 |
| Q2 | 静默时段内到达的 AlertTriggered 是否补发？ | 不补发，丢弃并记录 suppression |
| Q3 | 背压恢复阈值？ | 积压 < 5000 恢复（hysteresis 防抖动） |
| Q4 | 事件消费失败后重试？ | 指数退避 3 次，最终降级为定时全量刷新（30s） |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 调度延迟 | < 500ms 入队到派发 | prd.md §非功能要求 |
| 背压阈值 | 积压 > 10000 → 限流 | prd.md §非功能要求 |
| 重试 | 指数退避 30s/2min/5min, max 3 | prd.md §非功能要求 |
| 投递成功率 | 99.5%（含重试） | prd.md §非功能要求 |
| 事件生效 | PreferencesChanged < 5s | prd.md §验收条件 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 队列积压爆满 | 🟡 P1 | 高波动期大量告警触发 | 背压限流 + 水平扩展 |
| 通道全故障 | 🔴 P0 | Push/Email/SMS 全部不可用 | 记录失败 + 人工告警 + 降级日志 |
| 重试风暴 | 🟡 P2 | 大量重试拖垮系统 | 指数退避 + 全局重试限流 |
| 缓存不一致 | 🟡 P2 | 事件丢失 → 缓存 stale | 事件刷新 + 定时全量刷新 (30s 兜底) |
| 静默时段逃逸 | 🟡 P2 | 入队后才收到 PreferencesChanged | 出队时二次检查（缓存刷新） |
| 事件消费失败 | 🟡 P2 | PreferencesChanged/PremiumTierChanged 漏处理 | 定时全量刷新 30s 兜底 |
| 背压抖动 | 🟢 P3 | 阈值上下摆动 | 5000-10000 迟滞区间 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | Bull 队列延迟引用 prd.md §非功能要求 "< 500ms"，不自设指标 |
| 范围冻结 | 只管理分发编排和队列，不介入具体通道实现 |
| 证据门禁 | "调度延迟 < 500ms" VERIFIED: 出队记录 + 端到端计时 |

### kernel.md §错误处理铁律
- Hook 永不阻塞: 背压触发仅暂停入队，不 crash 进程
- Error DNA: 投递失败自动记录
- 修复上限 3 轮: 重试 max 3 次, 第 3 次 → 永久失败 (不 BLOCKED)

### 反模式防范 (claude-next.md)
- R27: "投递成功率 99.5%" → 不自称达标, 必须有监控数据
- [seed:general] 接口变更前查引用: 修改事件消费者前查所有订阅方
- R24: 清理脚本 `for x in $QUEUE_JOBS` → `set -f`

## 实现路径建议

1. **Phase 1**: Bull 队列初始化 + AlertTriggered 消费 + 投递编排
2. **Phase 2**: 重试 + 指数退避 + 通道降级 + DeliveryReceipt
3. **Phase 3**: 偏好缓存 + PreferencesChanged/PremiumTierChanged 事件消费
4. **Phase 4**: 背压控制 + 静默时段过滤 + getDeliveryStatus/testChannel
