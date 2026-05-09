# Feature: Dashboard Mobile

> 所属 Sub PRD：Alert Dashboard
> 职责：移动端告警仪表盘 — React Native 全功能适配

## 功能边界

- **负责**：
  - React Native 移动端告警仪表盘
  - 移动端列表/创建/历史视图适配
  - 响应式适配（320px - 2560px）
  - 移动端推送通知展示

- **不负责**：
  - Web 版告警列表（由 Dashboard Alert List 负责）
  - Web 版创建界面（由 Dashboard Alert Creator 负责）
  - Web 版历史页面（由 Dashboard Alert History 负责）
  - 告警业务逻辑（由 Alert Engine 负责）

## 对外接口

无独立接口（复用 Web 版 interface，通过 Alert Engine API 交互）

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `AlertTriggered` | inbound | 移动端即时展示触发通知 | alert_id, symbol, price, condition_type, user_id, channels |
| `DeliveryFailed` | inbound | 移动端展示投递失败告警 | delivery_id, alert_id, channel, error, retry_count |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 仪表盘加载时间 | < 2 秒（100 条活跃告警） | P0 |
| 响应式适配 | 320px - 2560px | P0 |
| WCAG 2.1 AA 合规 | 全部 | P1 |

## 数据实体归属

无（移动端为纯 UI，数据通过 Alert Engine API 读取）

## 依赖关系

- **依赖**：Alert Engine API（告警数据 CRUD）、Firebase Cloud Messaging（推送通知）
- **被依赖**：无

## Mock 数据

```json
{
  "mock_mobile_dashboard": {
    "input": { "user_id": "user_001", "device": "iPhone 15" },
    "output": { "alerts": [{ "id": "alert_001", "symbol": "BTC/USD", "status": "active" }], "layout": "mobile_optimized" }
  }
}
```

## 验收条件

- [ ] AC-1: 移动端仪表盘在 < 2 秒内加载
- [ ] AC-2: 响应式适配 320px-2560px
- [ ] AC-3: 移动端创建/列表/历史全部可用
- [ ] AC-4: 推送通知在 App 内正确展示
- [ ] AC-5: WCAG 2.1 AA 合规

## 技术约束

- React Native（Mobile）
- 与 Alert Engine API 直接交互
