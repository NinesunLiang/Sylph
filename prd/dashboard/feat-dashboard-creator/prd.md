# Feature: Dashboard Alert Creator

> 所属 Sub PRD：Alert Dashboard
> 职责：告警创建界面 — 条件构建器、渐进式展开表单

## 功能边界

- **负责**：
  - 告警创建界面 UI（条件构建器、渐进式展开）
  - 创建表单渲染（renderAlertCreator）
  - 创建流程体验保障（< 30 秒完成）
  - 屏幕阅读器支持（创建/管理全流程）

- **不负责**：
  - 告警列表展示（由 Dashboard Alert List 负责）
  - 告警历史展示（由 Dashboard Alert History 负责）
  - 移动端适配（由 Dashboard Mobile 负责）
  - 告警业务逻辑与提交（由 Alert Engine API 负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `renderAlertCreator` | N/A (UI) | symbol, user_tier | Alert creation form |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 创建流程耗时 | < 30 秒完成 | P0 |
| WCAG 2.1 AA 合规 | 全部 | P1 |
| 屏幕阅读器支持 | 创建/管理全流程 | P1 |

## 数据实体归属

无（创建操作为纯 UI 组件，数据通过 Alert Engine API 提交）

## 依赖关系

- **依赖**：Alert Engine API（告警创建提交）、User Preferences（用户 tier 校验）
- **被依赖**：无

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `PremiumTierChanged` | inbound | User Preferences → Creator（刷新功能门禁） | user_id, old_tier, new_tier |

## Mock 数据

```json
{
  "mock_alert_creator": {
    "input": { "symbol": "BTC/USD", "user_tier": "premium" },
    "output": { "form_fields": ["condition_type", "threshold", "channels", "quiet_hours"], "available_conditions": ["price_above", "price_below", "rsi_above", "rsi_below"] }
  }
}
```

## 验收条件

- [ ] AC-1: 创建告警流程 < 30 秒完成
- [ ] AC-2: 条件构建器（渐进式展开）可用
- [ ] AC-3: WCAG 2.1 AA 合规（屏幕阅读器测试通过）
- [ ] AC-4: 错误输入即时校验与提示

## 技术约束

- React Web App（Web）
- 与 Alert Engine API 直接交互
