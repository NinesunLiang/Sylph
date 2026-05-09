# Feature: Dashboard Alert List

> 所属 Sub PRD：Alert Dashboard
> 职责：告警列表展示、CRUD 操作、批量操作、App 内通知展示、事件消费

## 功能边界

- **负责**：
  - 告警列表/查看/编辑/暂停/恢复/删除
  - 批量操作（全部暂停、全部删除）
  - 通知触发后 App 内展示（AlertTriggered 事件消费）
  - 投递状态 badge 更新（DeliveryConfirmed 事件消费）
  - 仪表盘主视图渲染（renderDashboard）
  - 列表加载性能保障（< 2 秒 / 100 条 P0）

- **不负责**：
  - 告警创建界面（由 Dashboard Alert Creator 负责）
  - 告警历史展示（由 Dashboard Alert History 负责）
  - 移动端适配（由 Dashboard Mobile 负责）
  - 告警业务逻辑（由 Alert Engine 负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `renderDashboard` | N/A (UI) | user_id | Alert list view |

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `AlertTriggered` | inbound | Alert Engine 触发告警后更新 UI | alert_id, symbol, price, condition_type, user_id, channels |
| `AlertStateChanged` | inbound | Alert Engine 状态变更后更新 UI | alert_id, user_id, old_status, new_status |
| `DeliveryConfirmed` | inbound | 通知投递成功后更新 badge | delivery_id, alert_id, channel, timestamp |
| `DeliveryFailed` | inbound | 通知投递失败后展示异常 | delivery_id, alert_id, channel, error, retry_count |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 仪表盘加载时间 | < 2 秒（100 条活跃告警） | P0 |
| API 响应时间 | < 500ms (P95) | P1 |
| 键盘导航 | 所有告警功能 | P2 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| DashboardLayout | Own | CRUD | 用户仪表盘布局偏好 |
| AlertViewModel | Read | R | 告警数据展示视图（从 Alert Engine 读取） |

## 依赖关系

- **依赖**：Alert Engine（告警 CRUD 操作）、Notification Delivery（投递事件消费）
- **被依赖**：Dashboard Mobile（共享数据视图）

## Mock 数据

```json
{
  "mock_dashboard_list": {
    "input": { "user_id": "user_001" },
    "output": {
      "alerts": [
        { "id": "alert_001", "symbol": "BTC/USD", "condition": "price_above 70000", "status": "active", "channels": ["push", "email"] },
        { "id": "alert_002", "symbol": "ETH/USD", "condition": "rsi_below 30", "status": "paused", "channels": ["push"] }
      ],
      "stats": { "total_active": 2, "total_paused": 1, "triggered_today": 1 }
    }
  }
}
```

## 验收条件

- [ ] AC-1: 仪表盘在 < 2 秒内加载 100 条活跃告警
- [ ] AC-2: 暂停/恢复/编辑/删除操作即时生效
- [ ] AC-3: 批量操作（全部暂停、全部删除）可用
- [ ] AC-4: 通知触发后 App 内即时展示
- [ ] AC-5: 投递成功 badge 正确更新
- [ ] AC-6: 键盘导航覆盖所有告警功能

## 技术约束

- React Web App（Web）
- 与 Alert Engine API 直接交互
