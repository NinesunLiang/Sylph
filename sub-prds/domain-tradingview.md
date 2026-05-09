# Sub PRD: TradingView Integration

> 主 PRD：`mothership-prd.md` | 拆解日期：2026-05-08

## 功能边界（黑盒）

- **负责**：
  - TradingView WebSocket 连接管理与实时行情推送
  - 价格数据馈送（延迟 < 5 秒）
  - 技术指标数据计算与提供（RSI, MACD, MA, EMA, Bollinger Bands 等）
  - TradingView API 速率限制管理（100 req/min 智能批处理）
  - AI 模式检测（头肩顶、双顶/底、三角形、楔形 — 5 种关键形态）
  - 数据源归属标注

- **不负责**：
  - 告警条件评估（由 Alert Engine 负责）
  - 用户界面渲染（由 Alert Dashboard 负责）
  - 通知投递（由 Notification Delivery 负责）

## 对外接口契约

### 接口列表

| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `getPrice` | inbound | symbol | {price, timestamp, source} | SYMBOL_NOT_FOUND, RATE_LIMITED |
| `getIndicator` | inbound | symbol, indicator_type, params | {value, confidence, source} | INDICATOR_ERROR, DATA_DELAYED |
| `detectPattern` | inbound | symbol, pattern_types[] | {pattern, confidence, description} | INSUFFICIENT_DATA |
| `subscribePrice` | inbound | symbol, webhook_url | subscription_id | RATE_LIMITED |
| `unsubscribePrice` | inbound | subscription_id | 204 | NOT_FOUND |
| `priceUpdate` | outbound (WebSocket) | symbol, price, change_24h, volume | - | - |
| `indicatorUpdate` | outbound | symbol, indicator, value, timestamp | - | - |

### 事件 / 消息

| 事件名 | 发布方 | 订阅方 | 载荷 |
|--------|--------|--------|------|
| `PriceUpdate` | TradingView Integration | Alert Engine | symbol, price, timestamp |
| `IndicatorUpdate` | TradingView Integration | Alert Engine | symbol, indicator, value, confidence |

## 非功能契约

| 属性 | 约束值 | 优先级 | 来源 |
|------|--------|--------|------|
| 数据延迟 | < 5 秒 | P0 | PRD §Acceptance Criteria |
| API 速率 | 100 req/min（TradingView 限制） | P0 | PRD §Third-Party |
| WebSocket 连接 | 10,000 并发（当前上限） | P1 | PRD §Technical Constraints |
| 批处理评估 | 对 50K 告警做智能批处理 | P0 | PRD §Risk Mitigation |
| 缓存层 | 缓存热点数据减少 API 调用 | P1 | PRD §Risk Mitigation |
| 降级告警 | 数据延迟时显示置信度 | P0 | PRD Use Case 2 Edge Cases |

## Mock 数据

```json
{
  "mock_price_feed": {
    "input": {"symbol": "BTC/USD"},
    "output": {
      "price": 70005.50,
      "change_24h": "+2.3%",
      "volume_24h": 28500000000,
      "timestamp": "2026-05-08T14:30:00Z",
      "source": "TradingView",
      "delay_ms": 1200
    }
  },
  "mock_indicator": {
    "input": {"symbol": "ETH/USD", "indicator": "RSI", "params": {"period": 14}},
    "output": {
      "value": 28.5,
      "interpretation": "oversold",
      "confidence": "high",
      "source": "TradingView",
      "delayed": false
    }
  },
  "mock_pattern": {
    "input": {"symbol": "BTC/USD", "pattern_types": ["head_and_shoulders", "double_top"]},
    "output": {
      "detected": true,
      "pattern": "head_and_shoulders",
      "confidence": 0.78,
      "description": "Head & Shoulders 形态识别，可能预示趋势反转"
    }
  }
}
```

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| PriceFeed | Own | R | 实时行情数据（内存/Redis 缓存） |
| IndicatorCache | Own | R | 指标计算结果缓存 |
| PatternDetection | Own | CR | AI 模式检测结果 |
| WebSocketConnection | Own | CRUD | WebSocket 连接管理 |
| APIRateLimitState | Own | CRUD | API 调用配额跟踪 |

## 依赖关系

- **依赖**：TradingView 外部 API（互联网连接）
- **被依赖**：Alert Engine（消费 PriceUpdate 和 IndicatorUpdate 事件）

## 父需求追溯

| 主 PRD 章节 | 覆盖内容 |
|-------------|---------|
| §TradingView Integration (P0) | 全部 |
| §Technical Indicator Alerts (P1) | 数据源部分 |
| §AI Pattern Detection (P1) | 全部 |
| §Third-Party Integrations - TradingView | 全部 |
| §Technical Constraints - TradingView API | 全部 |
| §Risk - TradingView API Rate Limits | 全部 |

## 验收条件

- [ ] AC-1: 行情数据延迟 < 5 秒
- [ ] AC-2: 10 个常用技术指标数据可获取
- [ ] AC-3: 5 种关键图表形态可检测（含置信度）
- [ ] AC-4: TradingView API 速率限制（100 req/min）被正确处理
- [ ] AC-5: WebSocket 连接 10,000 并发稳定

## 技术约束

- TradingView WebSocket + REST API
- 指标计算缓存（Redis）
- 模式检测使用 AI/ML 模型
- 批处理队列（Bull）
