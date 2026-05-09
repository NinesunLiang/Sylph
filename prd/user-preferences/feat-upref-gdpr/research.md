# Research: UpRef GDPR Compliance

> 基于 `prd/user-preferences/feat-upref-gdpr/prd.md` · 2026-05-09
> Feature 职责：GDPR 合规 — 用户数据删除与隐私管理

---

## 关键调用链路

```
用户请求数据删除
  └─→ DELETE /api/user/{user_id}/data → deleteUserData(user_id)
        ├─→ 记录删除请求 (UserDataRetention)
        │     INSERT INTO user_data_retention
        │       (user_id, status, requested_at, source_ip, request_id)
        │     VALUES ($1, 'deleting', NOW(), $2, $3)
        ├─→ 级联删除 (cascade-delete):
        │     ├─→ NotificationPreference → DELETE (PostgreSQL)
        │     ├─→ PremiumSubscription → 匿名化: user_id→NULL, 保留 Stripe ref
        │     ├─→ User2FA → DELETE
        │     ├─→ alert 数据 → 通知 Alert Engine: DELETE alerts WHERE user_id=$1
        │     │     └─→ 事务: 各模块独立, 单个失败不阻断整体
        │     ├─→ 投递记录 → 通知 Notification Delivery 删除
        │     └─→ UserDataRetention → UPDATE status='deleted', completed_at=NOW()
        ├─→ 审计日志写入 (audit-log.ts)
        │     {event: "GDPR_DELETE", user_id, request_id, timestamp, result: "completed"}
        └─→ 返回 204 (No Content)

72 小时超时监控 (deadline-monitor.ts):
  └─→ 定时任务 (每 1h):
        ├─→ SELECT * FROM user_data_retention
        │     WHERE status='deleting' AND requested_at < NOW() - INTERVAL '71 hours'
        ├─→ 超时 → 告警 (PagerDuty / slack)
        │     {alert: "GDPR_DELETE_OVERDUE", user_id, requested_at, elapsed_hours}
        └─→ > 72h 仍未完成 → 升级告警 (P1)

审计日志:
  ├─→ 每次 deleteUserData 写入 (谁、何时、request_id、结果)
  ├─→ 独立审计表 (user_audit_log), 不级联删除
  └─→ 保留 7 年 (GDPR 要求)

软删除方案:
  ├─→ 数据留存: UserDataRetention 保留 7 年 (审计用)
  ├─→ 业务数据: 物理删除 (不软删除, GDPR right to erasure)
  └─→ Stripe: 仅匿名化关联, 不删除 Stripe 数据
```

## 级联删除清单

| 模块 | 操作 | 失败处理 | 备注 |
|------|------|---------|------|
| NotificationPreference | 物理删除 | 跳过+审计告警 | own |
| PremiumSubscription | 匿名化 (user_id→null) | 跳过+审计告警 | 保留计费记录 |
| User2FA | 物理删除 | 跳过+审计告警 | own |
| 告警 (Alert Engine) | 通知 Alert Engine API | 跳过+审计告警 | async |
| 投递記錄 (Notification) | 通知 Notification Delivery | 跳过+审计告警 | async |
| UserDataRetention | UPDATE status=deleted | — | 自身 |
| 审计日志 | 保留 (不删除) | — | 独立存储, 7 年 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 删除完成 | 72 小时内 | prd.md §非功能要求 |
| 审计日志 | 必须记录 (7 年保留) | prd.md §GDPR |
| 级联清单 | 每条失败→审计告警 | prd.md §GDPR |
| Stripe 数据 | 匿名化, 不删除 | prd.md §GDPR |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 删除确认？ | 完成后发送邮件 (v2), v1 静默完成 |
| Q2 | Stripe 数据保留？ | 匿名化, 保留 Stripe ref |
| Q3 | 删除撤销？ | v1 不支持 (GDPR 要求立即开始删除) |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 删除不完整 | 🟡 P1 | 某模块漏删 → GDPR 违规 | 级联清单 + 每条确认 |
| 72h 超时 | 🟡 P1 | 删除流程超时 | 1h 监控 + P1 告警 |
| 误删 | 🟡 P2 | 用户误操作 | 审计日志可追溯 |
| 审计日志丢失 | 🟡 P2 | 删除操作不可追溯 | 独立审计表 + backup |
| Stripe 级联失败 | 🟢 P3 | Stripe API 不可达 | 匿名化先, Stripe 后 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 隐私防线 | 用户 ID 不入审计日志明文 (hash), 仅内部 request_id |
| 范围冻结 | 只做数据删除, 不做导出 (v2) |
| 证据门禁 | "72h 内完成" VERIFIED: 监控日志 |

### kernel.md §错误处理铁律
- Hook 永不阻塞: 级联删除模块失败 → 跳过 + 审计告警 (不阻断整体)
- Error DNA: 删除失败记录至 error-dna.jsonl

### 反模式防范 (claude-next.md)
- R6 (隐私): 审计日志中 user_id hash, 不存明文
- R24: 清理脚本 `for x in $REQUESTS` → `set -f`
- R27: "删除完成 72h" 不自称达标, 必须有超时监控数据

## 实现路径建议

1. **Phase 1**: UserDataRetention CRUD + deleteUserData 入口 (记录请求 + 返回 204)
2. **Phase 2**: 级联删除 (逐模块物理删除/匿名化 + 失败审计)
3. **Phase 3**: 超时监控 (每 1h, 71h 告警, 72h P1) + 审计日志 (7 年保留)
