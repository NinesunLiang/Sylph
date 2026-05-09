# Plan: UpRef GDPR Compliance

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: UserDataRetention CRUD + deleteUserData 入口

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/gdpr/data-retention-store.ts`, `src/user-preferences/gdpr/delete-user-data.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/user-preferences/gdpr/` |

**验收标准：**
- [ ] UserDataRetention CRUD (PostgreSQL)
- [ ] deleteUserData: 写入 retention 记录 (status=deleting, requested_at)
- [ ] 返回 204 (异步删除)
- [ ] source_ip + request_id 记录

**边界/错误：**
- 重复请求同一 user_id (已有 deleting 记录) → 返回 202 (已接收)
- 已删除用户再次请求 → 404 NOT_FOUND (已无数据可删)
- DB 写入失败 → 500 + 审计告警
- request_id = uuid_v4 (可追溯)

### Task 2: 级联删除

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/gdpr/cascade-delete.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/user-preferences/gdpr/cascade-delete.ts` |

**验收标准：**
- [ ] NotificationPreference → 物理删除
- [ ] PremiumSubscription → 匿名化 (user_id→null)
- [ ] User2FA → 物理删除
- [ ] 通知 Alert Engine API 删除告警数据 (async)
- [ ] 通知 Notification Delivery 删除投递记录 (async)
- [ ] 级联清单 + 每条确认: 失败→审计告警 (不阻断整体)

**边界/错误：**
- 单个模块删除失败 → 审计告警 + 继续下一模块 (GDPR 要求尽可能删除)
- Alert Engine API 超时 → 重试 3 次, 第 3 次 → 审计告警
- 匿名化 PremiumSubscription → user_id→null, 保留 Stripe reference
- 全部完成 → UPDATE user_data_retention SET status='deleted', completed_at=NOW()
- 级联期间新数据写入 → 删除后再次清理 (v2 防竞态)

### Task 3: 超时监控 + 审计日志

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/gdpr/deadline-monitor.ts`, `src/user-preferences/gdpr/audit-log.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/user-preferences/gdpr/deadline-monitor.ts` |

**验收标准：**
- [ ] 定时任务: 每 1h 检查 deleting > 71h → 告警
- [ ] > 72h → 升级 P1 告警
- [ ] 审计日志: {event, user_id(hash), request_id, timestamp, result}
- [ ] 独立审计表, 7 年保留
- [ ] user_id 在审计日志中 hash (kernel.md §隐私防线)

**边界/错误：**
- 监控任务死循环 → 单次超时 30s → 跳过本轮
- 审计日志写入失败 → ERROR 日志 (不能回滚删除)
- 告警通道不可用 → 降级为 ERROR 日志
- user_id hash: SHA256 (不可逆)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | deleteUserData 请求记录 | Jest | 204 + retention 记录 |
| 单元 | cascase-delete 逐模块逻辑 | Jest | 6 模块 + 失败跳过 |
| 单元 | 72h 超时计算 | Jest | 边界 71h/72h |
| 集成 | 完整删除流程 (mock 各模块) | Jest | 级联完成 + 匿名化 |
| 集成 | 监控 + 告警 | Jest (mock timer) | 1h 检查, 71h 告警 |
| 安全 | user_id hash 审计 | Jest | 不可逆, 无明文 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/user-preferences/gdpr/data-retention-store.ts` | 新增 | PostgreSQL retention 表 |
| `src/user-preferences/gdpr/delete-user-data.ts` | 新增 | 删除入口 (204) |
| `src/user-preferences/gdpr/cascade-delete.ts` | 新增 | 6 模块级联 |
| `src/user-preferences/gdpr/deadline-monitor.ts` | 新增 | 71h/72h 超时监控 |
| `src/user-preferences/gdpr/audit-log.ts` | 新增 | 审计日志 (7 年) |

---

## 非范围

- 不实现用户认证（由现有 OAuth 负责）
- 不实现 Stripe 数据删除（按 Stripe 政策保留）
- 不实现数据导出请求（v2 计划）
- 不实现删除确认邮件（v2 计划）
