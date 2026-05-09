# Feature: TradingView Indicator Data

> 所属 Sub PRD：TradingView Integration
> 职责：技术指标数据计算与提供（RSI, MACD, MA, EMA, Bollinger Bands）

## 功能边界

- **负责**：
  - 技术指标数据查询（getIndicator）
  - 指标数据 WebSocket 推送（indicatorUpdate outbound）
  - IndicatorUpdate 事件发布（输出至 Alert Engine）
  - 指标计算结果缓存（IndicatorCache）
  - 10 个常用技术指标支持

- **不负责**：
  - 实时行情数据（由 WebSocket & Price Feed 负责）
  - AI 模式检测（由 Pattern Detection 负责）
  - API 速率限制管理（由 Rate Limit 负责）
  - 告警条件评估（由 Alert Engine 负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `getIndicator` | inbound | symbol, indicator_type, params | {value, confidence, source} |
| `indicatorUpdate` | outbound | symbol, indicator, value, timestamp | - |

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `IndicatorUpdate` | outbound | 指标更新事件（输出至 Alert Engine） | symbol, indicator, value, confidence |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| API 速率 | 100 req/min（TradingView 限制） | P0 |
| 缓存层 | 缓存热点数据减少 API 调用 | P1 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| IndicatorCache | Own | R | 指标计算结果缓存 |

## 依赖关系

- **依赖**：TradingView API（第三方）、Price Feed（基础行情数据）
- **被依赖**：Alert Engine（消费 IndicatorUpdate 事件）

## Mock 数据

```json
{
  "mock_indicator": {
    "input": { "symbol": "ETH/USD", "indicator": "RSI", "params": { "period": 14 } },
    "output": { "value": 28.5, "interpretation": "oversold", "confidence": "high", "source": "TradingView", "delayed": false }
  }
}
```

## 验收条件

- [ ] AC-1: 10 个常用技术指标数据可获取
- [ ] AC-2: 指标数据缓存命中率达标
- [ ] AC-3: IndicatorUpdate 事件正确发射

## 技术约束

- TradingView REST API
- 指标计算缓存（Redis）
