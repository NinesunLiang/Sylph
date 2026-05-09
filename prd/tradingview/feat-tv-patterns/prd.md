# Feature: TradingView Pattern Detection

> 所属 Sub PRD：TradingView Integration
> 职责：AI 模式检测 — 5 种关键图表形态识别

## 功能边界

- **负责**：
  - AI 图表形态检测（detectPattern）
  - 5 种关键形态识别（头肩顶、双顶/底、三角形、楔形）
  - 形态置信度评分
  - 模式检测结果持久化（PatternDetection）
  - 不足数据时的降级处理

- **不负责**：
  - 实时行情数据（由 WebSocket & Price Feed 负责）
  - 技术指标数据（由 Indicator Data 负责）
  - API 速率限制（由 Rate Limit 负责）
  - 告警条件评估（由 Alert Engine 负责）

## 对外接口

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| `detectPattern` | inbound | symbol, pattern_types[] | {pattern, confidence, description} |

## 非功能要求

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| API 速率 | 100 req/min（TradingView 限制） | P0 |
| 批处理评估 | 对 50K 告警做智能批处理 | P0 |
| 降级告警 | 数据不足时返回 INSUFFICIENT_DATA | P0 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| PatternDetection | Own | CR | AI 模式检测结果 |

## 依赖关系

- **依赖**：TradingView API（第三方）、Price Feed（基础行情数据）
- **被依赖**：Alert Engine（消费检测结果）

## Mock 数据

```json
{
  "mock_pattern": {
    "input": { "symbol": "BTC/USD", "pattern_types": ["head_and_shoulders", "double_top"] },
    "output": { "detected": true, "pattern": "head_and_shoulders", "confidence": 0.78, "description": "Head & Shoulders 形态识别，可能预示趋势反转" }
  }
}
```

## 验收条件

- [ ] AC-1: 5 种关键图表形态可检测（含置信度）
- [ ] AC-2: 数据不足时正确返回 INSUFFICIENT_DATA
- [ ] AC-3: 批处理 50K 告警时系统稳定

## 技术约束

- TradingView API
- 模式检测使用 AI/ML 模型
- 批处理队列（Bull）
