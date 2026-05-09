# [Feature] Advanced Evaluation

> 所属 Sub PRD：Alert Engine | 目录：`prd/alert-engine/feat-advanced-evaluation/`

## 功能边界（黑盒）

- **负责**：
  - 技术指标告警条件评估（RSI, MACD, MA, EMA, Bollinger Bands 等 10 种）
  - 多条件组合逻辑（AND/OR）
  - AI 图表模式检测（头肩顶、双顶/底、三角形、楔形 — 5 种）
  - 模式检测置信度评分
  - 教育性上下文生成（解释"为什么触发"）
  - **仅限 Premium 用户**

- **不负责**：
  - 价格告警评估（由 Price Evaluation 负责）
  - 指标数据获取（由 TradingView Integration 域提供）
  - 触发后处理（由 Trigger History 负责）

## 对外接口契约

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `evaluateIndicator` | inbound | alert_id, indicator_values | {triggered, value, interpretation} | INDICATOR_ERROR, DATA_DELAYED |
| `detectPattern` | inbound | symbol, pattern_types[] | {pattern, confidence, description} | INSUFFICIENT_DATA |
| `getEducationalContext` | inbound | alert_id, condition_type | {title, explanation, link} | - |

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `AlertConditionMet` | outbound | Advanced Evaluation → Trigger History | alert_id, symbol, value, confidence, context |
| `IndicatorUpdate` | inbound | TradingView → Advanced Evaluation（指标数据驱动高级评估） | symbol, indicator, value, confidence |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 指标数据延迟 | 显示置信度标注 | P1 |
| 多指标同时触发 | 合并为单条通知 | P1 |
| 评估延迟 | 条件满足后 < 30 秒触发 | P0 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| AlertCondition | Read | R | 条件定义（从 Alert CRUD 读取） |

## 依赖关系

- **依赖**：TradingView Integration（行情/指标数据）、Alert CRUD（告警配置）
- **被依赖**：Trigger History（消费 AlertConditionMet 事件）

## 技术约束

- Node.js + TypeScript
- TradingView API（指标数据源）
- AI/ML 模型（模式检测）

## Mock 数据

```json
{
  "evaluate_rsi": {
    "alert": {"condition": "rsi_below", "threshold": 30, "symbol": "ETH/USD"},
    "indicator_value": 28.5,
    "result": {"triggered": true, "value": 28.5, "interpretation": "oversold"},
    "context": "RSI 低于 30 表示 ETH 可能超卖，这可能预示买入机会"
  },
  "detect_head_shoulders": {
    "symbol": "BTC/USD",
    "result": {"detected": true, "pattern": "head_and_shoulders", "confidence": 0.78, "description": "头肩顶形态，可能预示趋势反转"}
  }
}
```

## 验收条件

- [ ] AC-1: 10 种技术指标全部可评估
- [ ] AC-2: 5 种 AI 图表模式可检测
- [ ] AC-3: 多条件组合（AND/OR）逻辑正确
- [ ] AC-4: 仅 Premium 用户可创建——由 Alert CRUD 域的 tier gate 拦截，本域不重复验证
- [ ] AC-5: 教育上下文文字合理且可配置
