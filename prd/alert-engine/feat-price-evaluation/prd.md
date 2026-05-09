# [Feature] Price Evaluation

> 所属 Sub PRD：Alert Engine | 目录：`prd/alert-engine/feat-price-evaluation/`

## 功能边界（黑盒）

- **负责**：
  - 价格水平告警条件实时评估（above/below/crosses）
  - 从 TradingView 集成域获取实时价格数据
  - 评估频率调度（按告警优先级确定检查间隔）
  - 评估结果判定（触发/不触发）
  - MVP 核心评估逻辑（P0）

- **不负责**：
  - 技术指标或 AI 模式评估（由 Advanced Evaluation 负责）
  - 告警触发后的通知处理（由 Trigger History 负责）
  - 告警 CRUD/配置管理（由 Alert CRUD 负责）

## 对外接口契约

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `evaluateAlert` | inbound | alert_id, current_price | {triggered, price_at_eval} | EVAL_ERROR |
| `batchEvaluate` | inbound | alert_ids[], prices[] | triggered[] | EVAL_ERROR |
| `getEvaluationStatus` | inbound | alert_id | {last_eval, next_eval, state} | NOT_FOUND |

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `AlertConditionMet` | outbound | Price Evaluation → Trigger History | alert_id, symbol, price, condition_type, evaluated_at |
| `PriceUpdate` | inbound | TradingView → Price Evaluation（实时行情驱动评估） | symbol, price, timestamp |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 评估延迟 | 条件满足后 < 30 秒触发 | P0 |
| 并发评估 | 1,000 评估/秒 | P1 |
| 总容量 | 50,000+ 告警 | P0 |

## 数据实体归属

无（价格评估为纯计算逻辑，不持久化实体）

## 依赖关系

- **依赖**：TradingView Integration（实时价格数据）、Alert CRUD（告警配置）
- **被依赖**：Trigger History（消费 AlertConditionMet 事件）

## 技术约束

- Node.js + TypeScript
- Redis（实时价格缓存）
- Bull 队列（批量评估调度）

## Mock 数据

```json
{
  "evaluate_price_above": {
    "alert": {"condition": "price_above", "threshold": 70000, "symbol": "BTC/USD"},
    "current_price": 70005.50,
    "result": {"triggered": true, "price_at_eval": 70005.50, "trigger_type": "above"}
  },
  "evaluate_not_triggered": {
    "alert": {"condition": "price_below", "threshold": 60000, "symbol": "BTC/USD"},
    "current_price": 70005.50,
    "result": {"triggered": false, "price_at_eval": 70005.50}
  }
}
```

## 验收条件

- [ ] AC-1: 价格 above 条件准确触发
- [ ] AC-2: 价格 below 条件准确触发
- [ ] AC-3: crosses 两种方向支持
- [ ] AC-4: 批量评估 1,000 告警/秒
- [ ] AC-5: 50,000 并发告警下内存稳定
