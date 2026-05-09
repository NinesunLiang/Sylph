# Sub PRD: Alert Dashboard

> 主 PRD：`mothership-prd.md` | 拆解日期：2026-05-08

## 功能边界（黑盒）

- **负责**：
  - 告警管理仪表盘 UI（Web + Mobile）
  - 告警创建界面（条件构建器、渐进式展开）
  - 告警列表/查看/编辑/暂停/恢复/删除
  - 告警历史展示（近 30 天）
  - 批量操作（全部暂停、全部删除）
  - 通知触发后 App 内展示

- **不负责**：
  - 告警业务逻辑（由 Alert Engine 负责）
  - 通知投递（由 Notification Delivery 负责）
  - 行情数据展示（由 TradingView Integration 负责）

## 对外接口契约

### 接口列表

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `renderDashboard` | N/A (UI) | user_id | Alert list view | - |
| `renderAlertCreator` | N/A (UI) | symbol, user_tier | Alert creation form | - |
| `renderAlertHistory` | N/A (UI) | user_id, date_range | History timeline view | - |

注意：Dashboard 是纯 UI 层，业务操作通过 Alert Engine API 完成。

### 事件 / 消息

| 事件名 | 发布方 | 订阅方 | 载荷 |
|--------|--------|--------|------|
| `AlertTriggered` | Alert Engine | Dashboard (UI 更新) | alert_id, symbol, price, condition_type, user_id, channels |
| `AlertStateChanged` | Alert Engine | Dashboard (UI 更新) | alert_id, user_id, old_status, new_status |
| `DeliveryConfirmed` | Notification Delivery | Dashboard (UI badge) | delivery_id, alert_id, channel, timestamp |
| `DeliveryFailed` | Notification Delivery | Dashboard (UI 告警) | delivery_id, alert_id, channel, error, retry_count |
| `PremiumTierChanged` | User Preferences | Dashboard (UI 功能门禁) | user_id, old_tier, new_tier |

## 非功能契约

| 属性 | 约束值 | 优先级 | 来源 |
|------|--------|--------|------|
| 仪表盘加载时间 | < 2 秒（100 条活跃告警） | P0 | PRD §非功能需求 |
| API 响应时间 | < 500ms (P95) | P1 | PRD §非功能需求 |
| WCAG 2.1 AA 合规 | 全部 | P1 | PRD §Accessibility |
| 屏幕阅读器支持 | 创建/管理全流程 | P1 | PRD §Accessibility |
| 键盘导航 | 所有告警功能 | P2 | PRD §Accessibility |
| 响应式适配 | 320px - 2560px | P0 | PRD §Browser/Platform |

## Mock 数据

```json
{
  "mock_dashboard": {
    "user_id": "user_001",
    "alerts": [
      {
        "id": "alert_001",
        "symbol": "BTC/USD",
        "condition": "price_above 70000",
        "status": "active",
        "channels": ["push", "email"],
        "created_at": "2026-05-01"
      },
      {
        "id": "alert_002",
        "symbol": "ETH/USD",
        "condition": "rsi_below 30",
        "status": "paused",
        "channels": ["push"],
        "created_at": "2026-05-03"
      }
    ],
    "recent_triggers": [
      {"alert_id": "alert_001", "triggered_at": "2026-05-08T14:30", "price": 70005.50}
    ],
    "stats": {
      "total_active": 2,
      "total_paused": 1,
      "triggered_today": 1
    }
  }
}
```

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| DashboardLayout | Own | CRUD | 用户仪表盘布局偏好 |
| AlertViewModel | Read | R | 告警数据展示视图（从 Alert Engine 读取） |

## 依赖关系

- **依赖**：Alert Engine（读取告警数据、执行 CRUD 操作）

- **被依赖**：无

## 父需求追溯

| 主 PRD 章节 | 覆盖内容 |
|-------------|---------|
| §Alert Management Dashboard (P0) | 全部 |
| §User Experience & Design - Wireframes | 全部 |
| §User Experience & Design - Key Interactions | 全部 |
| §Accessibility | 全部 |
| §Browser/Platform Support | 全部 |

## 验收条件

- [ ] AC-1: 仪表盘在 < 2 秒内加载 100 条活跃告警
- [ ] AC-2: 创建告警流程 < 30 秒完成
- [ ] AC-3: 暂停/恢复/编辑/删除操作即时生效
- [ ] AC-4: 批量操作（全部暂停、全部删除）可用
- [ ] AC-5: 近 30 天告警历史可查看
- [ ] AC-6: WCAG 2.1 AA 合规（屏幕阅读器测试通过）
- [ ] AC-7: 响应式适配 320px-2560px

## 技术约束

- React Web App（Web）
- React Native（Mobile）
- 与 Alert Engine API 直接交互
