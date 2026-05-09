# PRD 拆解索引

> 主 PRD：`mothership-prd.md`（Smart Trading Alerts）
> 拆解日期：2026-05-08

## 层级关系图

```
                    ┌──────────────────────────┐
                    │  Smart Trading Alerts     │
                    │      (主 PRD)              │
                    └─────────────┬────────────┘
                                  │
         ┌───────────┬────────────┼────────────┬──────────────┐
         ▼           ▼            ▼            ▼              ▼
  domain-alert-  domain-     domain-      domain-         domain-user-
  engine.md      notification  dashboard   tradingview.md  preferences.md
                  .md          .md
```

## 依赖关系

| 域 | 依赖 | 被依赖 | 建议开发顺序 |
|----|------|--------|-------------|
| alert-engine | tradingview, user-preferences | notification, dashboard | 2 |
| notification | alert-engine, user-preferences | 无 | 3 |
| dashboard | alert-engine | 无 | 3 |
| tradingview | 无（外部 API） | alert-engine | 1 |
| user-preferences | 无（认证/计费系统） | alert-engine, notification | 1 |

**无依赖的两个域（可优先开发）**：tradingview, user-preferences

## 各域文件清单

| 文件 | 功能域 | 行数 |
|------|--------|------|
| [domain-alert-engine.md](domain-alert-engine.md) | 告警引擎（核心评估逻辑） | ~120 |
| [domain-notification.md](domain-notification.md) | 通知投递（Push/Email/SMS） | ~110 |
| [domain-dashboard.md](domain-dashboard.md) | 告警管理仪表盘 | ~100 |
| [domain-tradingview.md](domain-tradingview.md) | TradingView 行情集成 | ~115 |
| [domain-user-preferences.md](domain-user-preferences.md) | 用户偏好与 Premium 管理 | ~110 |

## MECE 正交性说明

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 职责重叠 | ✅ 无重叠 | 各域边界清晰：评估 vs 投递 vs 展示 vs 数据 vs 配置 |
| 功能内聚 | ✅ 高内聚 | 每个域围绕一个核心职责聚合 |
| 接口明确 | ✅ 低耦合 | 域间仅通过事件/API 通信 |
| 独立验证 | ✅ 可验证 | 每个域绑定了 Mock 数据可独立测试 |

## 开发阶段建议

| 阶段 | 内容 | 域 |
|------|------|-----|
| Phase 1 (Sprint 1-2) | 基础设施搭建 | tradingview + user-preferences |
| Phase 2 (Sprint 3-4) | MVP 核心功能 | alert-engine (价格告警) |
| Phase 3 (Sprint 5-6) | 通知+界面 | notification + dashboard |
| Phase 4 (Sprint 7-8) | Premium 功能 | alert-engine (指标/AI) + user-preferences (计费) |

---

## 拆解质量报告

- 文件完整性：✅（INDEX.md + 5 domain files 全部存在）
- 模板字段（8 项）：✅（边界/接口/非功能/Mock/数据实体/依赖/追溯/AC 均覆盖）
- 正交性抽查：✅（alert-engine vs notification = 评估逻辑 vs 投递，无重叠；dashboard vs alert-engine = UI vs 业务逻辑）
- 依赖闭合性：✅（tradingview 和 user-preferences 无内部依赖，可独立开发）
- 数据实体唯一性：✅（Alert/AlertHistory → alert-engine; NotificationDelivery → notification; PriceFeed/IndicatorCache → tradingview; NotificationPreference/User2FA → user-preferences）
- 非功能契约一致性：✅（各域约束值 ≤ 主 PRD 全局约束）
- 父需求全覆盖：✅（各域追溯条目覆盖 PRD 所有章节）
