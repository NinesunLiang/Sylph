# Research: Trigger History

> 基于 `prd/alert-engine/feat-trigger-history/prd.md` · 2026-05-09
> Feature 职责：告警触发冷却/去重、AlertTriggered 事件生成、历史记录

---

## 关键调用链路

```
入站事件: AlertConditionMet (alert_id, symbol, price, condition_type, triggered_at)
  from Price Evaluation / Advanced Evaluation
  └─→ processTrigger(alert_id, symbol, price, condition_type)
        ├─→ 冷却检查 (Redis Lua atomic: GET cooldown:{alert_id} + SET if absent)
        │     ├─→ 冷却中 → {action: "cooldown", remaining_sec}
        │     │     └─→ 5 min TTL, 精确到秒
        │     └─→ 未冷却 → SET cooldown:{alert_id} 1 EX 300
        ├─→ 写入 AlertHistory (PostgreSQL)
        │     INSERT INTO alert_history
        │       (alert_id, user_id, symbol, price, condition_type, triggered_at, status)
        │     VALUES ($1, (SELECT user_id FROM alerts WHERE id=$1), $2, $3, $4, NOW(), 'fired');
        ├─→ 读取告警配置 (用于事件完整载荷)
        │     SELECT user_id, channels FROM alerts WHERE id = $1
        ├─→ 发布 AlertTriggered 事件 (完整载荷)
        │     {
        │       event: "AlertTriggered",
        │       alert_id, user_id, symbol, price, condition_type,
        │       channels: ["push", "email", "sms"],
        │       triggered_at: ISO8601
        │     }
        │     └─→ 发送至 Notification Delivery + Dashboard
        ├─→ 自动过期检查 (可配置重复触发):
        │     ├─→ repeat = false (一次性) → UPDATE alerts SET status='expired'
        │     └─→ repeat = true → 保持 active (可再次触发)
        └─→ 返回 {action: "fire", history_id, alert_id, user_id, channels}

getAlertHistory(alert_id, date_range)
  └─→ SELECT * FROM alert_history WHERE alert_id=$1 AND triggered_at BETWEEN $2 AND $3
        └─→ 返回触发时间线 (按 triggered_at DESC)

getStats(user_id)
  └─→ SELECT
        COUNT(*) as total,
        COUNT(DISTINCT alert_id) as unique_alerts,
        MAX(triggered_at) as last_triggered
      FROM alert_history WHERE user_id=$1
        └─→ 返回统计摘要

定时清理 (每日 03:00, kernel.md §定时任务命名):
  DELETE FROM alert_history WHERE triggered_at < NOW() - INTERVAL '30 days'
  └─→ cron 表达式: 0 3 * * *
  └─→ 记录清理行数到审计日志
  └─→ 30 天保留 (prd.md §非功能要求)

事件载荷对照 (全系统一致性验证, 引用 sub-prds/domain-alert-engine.md §对外接口):

| 事件 | 发布方 | 消费方 | 载荷字段 |
|------|--------|--------|---------|
| AlertConditionMet | Price/Advanced Eval | Trigger History | alert_id, symbol, price, condition_type, triggered_at |
| AlertTriggered | Trigger History | Notification + Dashboard | alert_id, user_id, symbol, price, condition_type, channels, triggered_at |
```

## 数据流

| 步骤 | 输入 | 处理 | 输出 | 存储 | 备注 |
|------|------|------|------|------|------|
| 冷却检查 | alert_id | Redis Lua: GET + SET atomic | pass/block | Redis (cooldown:{id}) | TTL 300s |
| 历史写入 | alert_id, price, type | INSERT INTO alert_history | history_id | PostgreSQL | 事务 |
| 事件发布 | alert_id | 构建完整载荷 | AlertTriggered | Redis Pub/Sub | 含 user_id, channels |
| 过期标记 | alert_id | UPDATE alerts SET status='expired' | — | PostgreSQL | repeat=false 时 |
| 历史查询 | alert_id, date_range | SELECT ... WHERE ... | trigger_timeline | PostgreSQL | DESC |
| 统计 | user_id | SELECT COUNT, DISTINCT, MAX | stats | PostgreSQL | — |
| 清理 | — | DELETE WHERE < 30d | deleted_count | PostgreSQL | 每日 03:00 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 冷却窗口 | 5 分钟 (Redis TTL, Lua 原子操作) | prd.md §非功能要求 |
| 事件发射 | < 1 秒 (从决到发出) | prd.md §非功能要求 |
| 历史保留 | 30 天 | prd.md §非功能要求 |
| 重复触发控制 | 一次性 (repeat=false) → expired | prd.md §功能边界 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 冷却窗口可配置？ | v1 固定 5min, v2 per-alert 配置 (alert_config.cooldown_min) |
| Q2 | 一次性 vs 重复告警判定？ | createAlert 时指定 repeat: boolean |
| Q3 | 历史保留时长？ | 30 天, 定时清理 (每日 03:00) |
| Q4 | AlertTriggered 事件重试？ | 发布失败 → 重试 3 次, 第 3 次写死信 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 冷却被绕过 | 🟡 P1 | 并发请求同时通过冷却 | Redis Lua 原子 GET+SET |
| 历史表膨胀 | 🟡 P2 | 高频触发 → 大量写入 | 定时清理 + 归档 |
| 事件重复发射 | 🟡 P1 | AlertTriggered 多次发布 | 幂等性 via delivery_id |
| 事件载荷不完整 | 🟡 P1 | 缺少 user_id/channels | 回表查询 alerts |
| 清理丢失数据 | 🟢 P3 | 清理删了应保留的数据 | 软删除 (status=archived) 保留 7 天后物理删除 |

## 项目特定引用

### AGENTS.md §三重门 映射
- 冷却窗口精度验证 → 三重门 A(预测) → B(盲执行) → A(自证) 验证并发原子性
- 修复上限 3 轮: Lua 脚本连续 3 次 EVAL 失败 → BLOCKED

### kernel.md §错误处理铁律
- Hook 永不阻塞: 定时清理脚本 必须 exit 0 (不可 set -e)
- Error DNA: event-publisher 失败自动记录

### 反模式防范 (claude-next.md §R24/R31)
- R24: 定时清理 Bash 脚本 `for x in $OLD_IDS` → `set -f` 禁用 glob
- R31: gh CLI 不参与本 feature, 保持纯后端代码

## 实现路径建议

1. **Phase 1**: 冷却窗口 (Redis Lua atomic GET+SET, TTL 300s)
2. **Phase 2**: AlertConditionMet 事件消费 + AlertTriggered 事件发布 (完整载荷)
3. **Phase 3**: AlertHistory 写入 + 查询 (getAlertHistory, getStats)
4. **Phase 4**: 一次性告警自动过期 (repeat=false → expired)
5. **Phase 5**: 定时清理 (每日 03:00, 30 天) + 审计日志
