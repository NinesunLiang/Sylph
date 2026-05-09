# Feature: TradingView Rate Limit & Cache

> 所属 Sub PRD：TradingView Integration
> 职责：API 速率限制管理、缓存层、调用配额跟踪

## 功能边界

- **负责**：
  - TradingView API 速率限制管理（100 req/min）
  - 调用配额跟踪与智能批处理
  - 热点数据缓存管理
  - 速率超限时的降级与排队

- **不负责**：
  - WebSocket 连接管理（由 WebSocket & Price Feed 负责）
  - 技术指标计算（由 Indicator Data 负责）
  - AI 模式检测（由 Pattern Detection 负责）
  - 具体业务数据查询（由各上游 feature 负责）

## 对外接口

无独立业务接口（作为基础设施层，为其他 feature 提供速率控制与缓存能力）

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| API 速率 | 100 req/min（TradingView 限制） | P0 |
| 批处理评估 | 对 50K 告警做智能批处理 | P0 |
| 缓存层 | 缓存热点数据减少 API 调用 | P1 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| APIRateLimitState | Own | CRUD | API 调用配额跟踪 |

## 依赖关系

- **依赖**：TradingView API（第三方）、WebSocket & Price Feed（数据源）
- **被依赖**：Indicator Data、Pattern Detection（共享速率配额与缓存）

## Mock 数据

```json
{
  "mock_rate_limit": {
    "scenario": "配额耗尽时降级",
    "input": { "target_quota": 100, "used": 100, "reset_at": "2026-05-08T15:00:00Z" },
    "output": { "status": "rate_limited", "retry_after_sec": 300, "fallback": "cache" }
  }
}
```

## 验收条件

- [ ] AC-1: TradingView API 速率限制（100 req/min）被正确处理
- [ ] AC-2: 超限时自动降级到缓存数据
- [ ] AC-3: 智能批处理减少 API 调用次数
- [ ] AC-4: 配额重置后恢复直连

## 技术约束

- 缓存层（Redis）
- 批处理队列（Bull）
