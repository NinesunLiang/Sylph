# Feature: Dashboard Alert History

> 所属 Sub PRD：Alert Dashboard
> 职责：告警历史展示 — 近 30 天触发历史时间线

## 功能边界

- **负责**：
  - 告警历史展示 UI（近 30 天）
  - 历史时间线渲染（renderAlertHistory）
  - 日期范围筛选与分页
  - 历史加载性能保障

- **不负责**：
  - 告警列表展示（由 Dashboard Alert List 负责）
  - 告警创建界面（由 Dashboard Alert Creator 负责）
  - 移动端适配（由 Dashboard Mobile 负责）
  - 告警历史数据的持久化（由 Alert Engine 负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `renderAlertHistory` | N/A (UI) | user_id, date_range | History timeline view |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| API 响应时间 | < 500ms (P95) | P1 |
| WCAG 2.1 AA 合规 | 全部 | P1 |

## 数据实体归属

无（历史页为纯 UI 组件，数据通过 Alert Engine API 读取）

## 依赖关系

- **依赖**：Alert Engine API（告警历史数据查询）
- **被依赖**：无

## Mock 数据

```json
{
  "mock_alert_history": {
    "input": { "user_id": "user_001", "date_range": "2026-04-09~2026-05-09" },
    "output": {
      "triggers": [
        { "alert_id": "alert_001", "symbol": "BTC/USD", "price": 70005.50, "triggered_at": "2026-05-08T14:30", "channel": "push", "status": "delivered" }
      ],
      "total": 1,
      "page": 1,
      "page_size": 20
    }
  }
}
```

## 验收条件

- [ ] AC-1: 近 30 天告警历史可查看
- [ ] AC-2: 日期范围筛选正确
- [ ] AC-3: 历史加载 < 500ms (P95)
- [ ] AC-4: WCAG 2.1 AA 合规

## 技术约束

- React Web App（Web）
- 与 Alert Engine API 直接交互
