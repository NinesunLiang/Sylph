# Research: Alert CRUD

> 基于 `prd/alert-engine/feat-alert-crud/prd.md` · 2026-05-09
> Feature 职责：告警配置 CRUD、条件构建器、状态管理、Tier 门禁、入站事件消费

---

## 关键调用链路

```
用户创建告警
  └─→ createAlert(user_id, symbol, condition_type, threshold, channels)
        ├─→ 校验: symbol 格式 (E.164)，threshold 范围 (>0), channels 非空
        ├─→ Tier 门禁: checkTierGate(condition_type, user_id)
        │     ├─→ Free × (technical_indicator|ai_pattern_detection) → TIER_RESTRICTED + upgrade_url
        │     ├─→ Free × (price_above|price_below|price_crosses) → 放行 (限额检查)
        │     └─→ Premium → 放行
        ├─→ 限额检查: Free 最多 5 条活跃告警 (SELECT COUNT WHERE status IN (active,paused))
        │     ├─→ ≤5 → 继续
        │     └─→ >5 → LIMIT_EXCEEDED
        ├─→ PostgreSQL 事务写入 (Alert + AlertCondition):
        │     BEGIN;
        │     INSERT INTO alerts (user_id, symbol, condition_type, threshold, channels, status, created_at)
        │       VALUES ($1, $2, $3, $4, $5, 'active', NOW()) RETURNING id;
        │     INSERT INTO alert_conditions (alert_id, condition_type, params) VALUES ($1, $2, $3);
        │     COMMIT;
        ├─→ 发布 AlertStateChanged 事件 (async, fire-and-forget)
        │     {event: "AlertStateChanged", alert_id, user_id, old_status: null, new_status: "active", timestamp}
        └─→ 返回 {alert_id, status: "active"}

告警状态机
  ┌─────────────────────────────────────────────────────┐
  │                    active                            │
  │     ┌─────────────┘  │  └──────────────┐             │
  │     ▼                ▼                 ▼             │
  │  pauseAlert    (冷却触发)          (超期过期)        │
  │     │           AlertConditionMet    checkExpiry     │
  │     ▼                ▼                 ▼             │
  │   paused         triggered           expired         │
  │     │                │                                │
  │     └──resumeAlert──┘  (若 repeat=true → active)     │
  └─────────────────────────────────────────────────────┘

  有效转换:
    active  ↔ paused    (pause/resume)
    active  → triggered → active|expired   (仅 repeat=true 恢复 active)
    active  → expired   (一次性告警期满)
    *       → deleted   (级联删除)

入站事件消费（缓存刷新）
  └─→ PreferencesChanged (inbound from User Preferences)
        └─→ 失效用户偏好缓存 (Redis: npref:{user_id}, TTL 失效)
              └─→ 下次 createAlert/updateAlert 读取最新渠道配置
              └─→ 降级: 缓存不可用时使用上次缓存值 (stale-while-revalidate)

  └─→ PremiumTierChanged (inbound from User Preferences)
        └─→ 失效用户 Tier 缓存 (Redis: tier:{user_id}, TTL 失效)
              └─→ 下次 createAlert 读取最新 tier 门禁
              └─→ 降级: Redis 不可用 → 放过 (宁可多发一条, 不可阻止 Premium 用户)

级联删除流程
  deleteAlert(alert_id)
    ├─→ BEGIN TRANSACTION
    ├─→ DELETE FROM alert_history WHERE alert_id = $1
    ├─→ DELETE FROM alert_conditions WHERE alert_id = $1
    ├─→ DELETE FROM alerts WHERE id = $1
    ├─→ COMMIT
    ├─→ Redis: DEL cooldown:{alert_id} (清理冷却状态)
    └─→ 发布 AlertStateChanged {old_status: *, new_status: "deleted"}

  错误处理:
    ├─→ 事务任意步失败 → ROLLBACK → 返回 500
    ├─→ 告警不存在 → 返回 404 (NOT_FOUND)
    └─→ 并发删除同一告警 → 乐观锁 version 检查
```

## 数据流

| 接口 | 方向 | 输入 | 输出 | 存储 | 缓存策略 |
|------|------|------|------|------|---------|
| createAlert | inbound | condition, threshold, channels, user_id | alert_id, status | PostgreSQL | — |
| getAlert | inbound | alert_id | alert_detail | PostgreSQL | Redis cache 30s |
| listAlerts | inbound | user_id, filters | alert[] | PostgreSQL | — |
| updateAlert | inbound | alert_id, partial_fields | updated_alert | PostgreSQL | 失效 getAlert 缓存 |
| deleteAlert | inbound | alert_id | 204 | PostgreSQL (级联) | 失效 getAlert 缓存 + Redis cooldown |
| pauseAlert | inbound | alert_id | updated_alert | PostgreSQL (status→paused) | 失效 getAlert 缓存 |
| resumeAlert | inbound | alert_id | updated_alert | PostgreSQL (status→active) | 失效 getAlert 缓存 |
| PremiumTierChanged | inbound event | user_id, old_tier, new_tier | tier cache refresh | Redis | TTL 5min, 兜底全量刷新 30min |

## 项目特定引用

### AGENTS.md §三重门 映射
| 门禁 | 本 Feature 实现 | 触发条件 |
|------|----------------|---------|
| Gate-X (Schema 变更) | PostgreSQL migration 需二次批准 | ALTER TABLE / CREATE TABLE |
| 证据门禁 (L1-L4) | 每次 CRUD 操作必须 `VERIFIED:` 标注 | TaskUpdate 前 |
| 修复上限 | 编译/测试失败最多 3 轮, 每轮换假设 | 连续失败 |

### kernel.md §错误处理铁律 映射
| 规则 | 实现 |
|------|------|
| Error DNA 捕获 | 所有 CRUD handler try/catch → `error_classifier.py` |
| 修复 3 轮上限 | Step 3 编码阶段, 第 3 轮 BLOCKED |
| Hook 永不阻塞 | deleteAlert 不调用外部 hook |

### 反模式防范 (claude-next.md §R24/R27/R31)
- **R24 (unquoted glob)**: Bash 脚本中 `for x in $VAR` 必须 `set -f` 禁用 pathname expansion
- **R27 (report sources)**: 所有 AC 验证报告必须有 `file:line` 或命令输出引用
- **R31 (gh CLI)**: gh release/PR 写操作必须经 permission-gate 拦截

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| CRUD 延迟 | < 200ms (P95) | prd.md §非功能要求 |
| 冷却窗口 | 5 分钟（同一告警去重） | prd.md §非功能要求 |
| 并发容量 | 50,000+ 告警 | prd.md §非功能要求 |
| 技术栈 | Node.js + TypeScript + PostgreSQL | prd.md §技术约束 |
| Free 限额 | 5 条活跃告警 (全局) | prd.md §功能边界 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | Free 用户限额 5 条是全局还是按 symbol？ | 全局，与 symbol 无关 |
| Q2 | 级联删除范围：deleteAlert 是否删除 AlertHistory？ | 是，事务级联 |
| Q3 | pauseAlert 停掉单个告警还是所有？ | 单个 (per-alert) |
| Q4 | condition_type 校验规则表？ | Free: price_above/below/crosses; Premium: 全部含 technical_indicator + ai_pattern_detection |
| Q5 | 缓存降级策略？ | Redis 不可用 → 放过 (stale-while-revalidate), 不阻止核心 CRUD |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| Tier 门禁绕过 | 🔴 P0 | 客户端直接调 API | 服务端强制校验 (kernel.md §防御性规则) |
| 限额竞态 | 🟡 P1 | 并发创建时计数竞争 | SELECT COUNT FOR UPDATE + 事务重试 |
| 级联删除遗漏 | 🟡 P1 | 删告警不删历史 | 事务级联 + 审计日志 |
| 缓存一致 | 🟡 P2 | PremiumTierChanged 丢失 → 门禁滞后 | 定时全量刷新 (30min) + 缓存 TTL 上限 5min |
| Gate-X 未触发 | 🟡 P1 | Schema 变更绕过二次批准 | Pre-tool hook 检测 DDL 关键字 |

## 实现路径建议

1. **Phase 1**: PostgreSQL 数据模型 (Alert + AlertCondition + AlertHistory) + DDL migration 脚本
2. **Phase 2**: CRUD API 全套 (create/get/list/update/delete) + 乐观锁并发控制
3. **Phase 3**: Tier 门禁 + 限额检查 (服务端强制, 引用 AGENTS.md §难度分级)
4. **Phase 4**: 告警状态机 (active ↔ paused → triggered → expired) + AlertStateChanged 事件
5. **Phase 5**: 入站事件消费 (PreferencesChanged, PremiumTierChanged → 三层缓存架构: 事件驱动刷新 → TTL 5min → 定时 30min 兜底)
