# Feature: TradingView WebSocket & Price Feed

> 所属 Sub PRD：TradingView Integration
> 职责：WebSocket 连接管理、实时行情推送、价格数据查询

## 功能边界

- **负责**：
  - TradingView WebSocket 连接管理与维护
  - 实时行情推送（priceUpdate outbound）
  - 价格数据同步查询（getPrice）
  - WebSocket 订阅/退订管理（subscribePrice / unsubscribePrice）
  - PriceUpdate 事件发布（输出至 Alert Engine）
  - WebSocket 10,000 并发连接保障
  - 数据延迟 < 5 秒

- **不负责**：
  - 技术指标数据计算（由 Indicator Data 负责）
  - AI 模式检测（由 Pattern Detection 负责）
  - API 速率限制管理（由 Rate Limit 负责）
  - 告警条件评估（由 Alert Engine 负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `getPrice` | inbound | symbol | {price, timestamp, source} |
| `subscribePrice` | inbound | symbol, webhook_url | subscription_id |
| `unsubscribePrice` | inbound | subscription_id | 204 |
| `priceUpdate` | outbound (WebSocket) | symbol, price, change_24h, volume | - |

### 事件

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| `PriceUpdate` | outbound | 行情更新事件（输出至 Alert Engine） | symbol, price, timestamp |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| 数据延迟 | < 5 秒 | P0 |
| WebSocket 连接 | 10,000 并发（当前上限） | P1 |
| 降级告警 | 数据延迟时显示置信度 | P0 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| PriceFeed | Own | R | 实时行情数据（内存/Redis 缓存） |
| WebSocketConnection | Own | CRUD | WebSocket 连接管理 |

## 依赖关系

- **依赖**：TradingView WebSocket + REST API（第三方）
- **被依赖**：Alert Engine（消费 PriceUpdate 事件）

## Mock 数据

```json
{
  "mock_price_feed": {
    "input": { "symbol": "BTC/USD" },
    "output": { "price": 70005.50, "change_24h": "+2.3%", "volume_24h": 28500000000, "timestamp": "2026-05-08T14:30:00Z", "source": "TradingView", "delay_ms": 1200 }
  },
  "mock_websocket_subscribe": {
    "input": { "symbol": "ETH/USD", "webhook_url": "https://hooks.example.com/price" },
    "output": { "subscription_id": "sub_001", "status": "active" }
  }
}
```

## 验收条件

- [ ] AC-1: 行情数据延迟 < 5 秒
- [ ] AC-2: WebSocket 连接 10,000 并发稳定
- [ ] AC-3: 订阅/退订操作正确
- [ ] AC-4: 数据延迟时降级告警正确显示

## 技术约束

- TradingView WebSocket + REST API
- 缓存层（Redis）
