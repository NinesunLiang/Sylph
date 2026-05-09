# [Feature] Alert CRUD

> 所属 Sub PRD：Alert Engine | 目录：`prd/alert-engine/feat-alert-crud/`

## 功能边界（黑盒）

- **负责**：
  - 告警配置的完整 CRUD（创建/读取/更新/删除）
  - 告警条件构建器（价格水平条件）
  - 告警状态管理（暂停/恢复）
  - 告警条件校验（阈值合理性、参数完整性）
  - 按用户 tier 限制告警类型（Free 仅价格告警，Premium 含指标/AI — 调用 Tier Gating 验证）

- **不负责**：
  - 告警条件实际评估（由 Price Evaluation 负责）
  - 告警触发后的处理（由 Trigger History 负责）
  - 技术指标或 AI 模式条件构建（由 Advanced Evaluation 负责）

## 对外接口契约

### API 端点（对应 Sub PRD 接口）

| 接口 | 方法 | 入参 | 出参 | 错误码 |
|------|------|------|------|--------|
| `createAlert` | POST | symbol, condition_type, threshold, channels, user_id | alert_id, status | VALIDATION_ERROR, TIER_RESTRICTED |
| `updateAlert` | PUT | alert_id, partial_fields | updated_alert | NOT_FOUND, VALIDATION_ERROR |
| `deleteAlert` | DELETE | alert_id | 204 | NOT_FOUND |
| `pauseAlert` | POST | alert_id | updated_alert | NOT_FOUND |
| `resumeAlert` | POST | alert_id | updated_alert | NOT_FOUND |
| `listAlerts` | GET | user_id, status, page, limit | alert[] | - |
| `getAlert` | GET | alert_id | alert_detail | NOT_FOUND |

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `AlertStateChanged` | outbound | Alert CRUD → Alert Dashboard | alert_id, user_id, old_status, new_status |
| `PreferencesChanged` | inbound | User Preferences → Alert CRUD（更新后使能偏好缓存） | user_id, changed_fields |
| `PremiumTierChanged` | inbound | User Preferences → Alert CRUD（Tier 变更后刷新门禁） | user_id, old_tier, new_tier |

### 关键逻辑

- `createAlert` 在写入前检查 `condition_type` × `user_tier`：
  - Free: 只允许 `price_above` / `price_below` / `price_crosses`
  - Premium: 允许所有类型
  - TIER_RESTRICTED 时返回错误码 + 提示升级

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 告警配置延迟 | CRUD 操作 < 200ms (P95) | P0 |
| 冷却窗口 | 5 分钟（同告警 ID 去重） | P0 |
| 并发容量 | 50,000+ 告警 | P0 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| Alert | Own | CRUD | 告警配置（条件、渠道、状态） |
| AlertCondition | Own | CRUD | 条件定义（类型、阈值、逻辑） |

## Mock 数据

```json
{
  "create_price_alert": {
    "request": {"user_id": "free_user_01", "symbol": "BTC/USD", "condition_type": "price_above", "threshold": 70000, "channels": ["push"]},
    "response": {"alert_id": "alert_001", "status": "active"}
  },
  "create_indicator_alert_blocked": {
    "request": {"user_id": "free_user_01", "symbol": "ETH/USD", "condition_type": "rsi_below", "threshold": 30, "channels": ["push"]},
    "response": {"error": "TIER_RESTRICTED", "message": "技术指标告警仅限 Premium 用户", "upgrade_url": "/premium"}
  }
}
```

## 依赖关系

- **依赖**：User Preferences（Tier 校验）、Alert Engine 数据模型
- **被依赖**：Price Evaluation（读取告警配置）、Trigger History（告警状态变更通知）

## 技术约束

- Node.js + TypeScript
- PostgreSQL（告警配置持久化）
- 状态机（active ↔ paused → triggered → expired）

## 验收条件

- [ ] AC-1: Free 用户创建价格告警成功
- [ ] AC-2: Free 用户创建技术指标告警被 TIER_RESTRICTED 拦截
- [ ] AC-3: Premium 用户可创建所有类型告警
- [ ] AC-4: 暂停/恢复告警状态切换正确
- [ ] AC-5: 告警列表分页查询正确
- [ ] AC-6: Free 用户创建第 6 条告警返回 ALERT_LIMIT_REACHED
- [ ] AC-7: 用户删除告警级联删除历史记录
