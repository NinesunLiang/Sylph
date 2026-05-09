# Research: TradingView Indicator Data

> 基于 `prd/tradingview/feat-tv-indicators/prd.md` · 2026-05-09
> Feature 职责：技术指标数据计算与提供（RSI, MACD, MA, EMA, Bollinger Bands 等）

---

## 关键调用链路

```
客户端请求指标数据 (getIndicator)
  └─→ GET /api/indicator/{symbol}/{indicator_type}?params={period, ...}
        ├─→ 经 rate-limit 中间件 (feat-tv-ratelimit)
        ├─→ 查询 IndicatorCache (Redis: indicator:{symbol}:{type})
        │     ├─→ 命中 (且未过期) → {value, confidence, source: "cache"}
        │     └─→ miss → TradingView REST API
        │           ├─→ 成功 → 写入 IndicatorCache → 返回
        │           │     └─→ TTL 按指标类型差异化:
        │           │           ├─→ RSI/MACD: 1min (高频)
        │           │           ├─→ SMA/EMA/BB/STOCH/ATR: 3min (中频)
        │           │           └─→ ICHI/VPROF/FIBO: 5min (低频)
        │           └─→ 错误:
        │                 ├─→ 429 → 共享配额耗尽 → RATE_LIMITED + 缓存兜底
        │                 ├─→ 404 → SYMBOL_NOT_FOUND
        │                 └─→ 5xx → INDICATOR_ERROR
        └─→ 返回指标数据 + confidence + source + delayed 标记

indicatorUpdate 自动推送 (outbound event)
  └─→ PriceUpdate 事件到达 → 触发指标重算
        ├─→ 检查当前 symbol 是否有订阅者/活跃告警
        │     ├─→ 无 → 跳过 (省配额)
        │     └─→ 有 → 计算/获取指标值
        ├─→ 写入 IndicatorCache (刷新 TTL)
        ├─→ 发布 IndicatorUpdate 事件 (→ Alert Engine)
        │     {event: "IndicatorUpdate", symbol, indicator, value, confidence, timestamp}
        └─→ 刷新频率: 活跃 symbol 30s, 冷门 5min

10 指标实现策略:
  ┌─────────────────────────────────────────────────────┐
  │ v1: TradingView REST API (快, 省本地计算)            │
  │     getIndicator → TV API → 缓存 → 返回              │
  │                                                      │
  │ v2: 本地计算 + TV 数据 (可控, 省配额)                 │
  │     1. TV 提供 K 线数据 (OHLCV)                       │
  │     2. 本地用 ta.js / technicalindicators npm 计算   │
  │     3. 结果缓存 (TTL 按指标类型)                      │
  │                                                      │
  │ v1 → v2 切换策略: 配额使用率 > 80% → 自动切本地计算   │
  └─────────────────────────────────────────────────────┘
```

## 指标缓存 TTL 策略

| 指标 | TTL | 更新触发 | 配额消耗 |
|------|-----|---------|---------|
| RSI | 60s | PriceUpdate | 1 req |
| MACD | 60s | PriceUpdate | 1 req |
| SMA | 3min | PriceUpdate | 1 req |
| EMA | 3min | PriceUpdate | 1 req |
| BB | 3min | PriceUpdate | 1 req |
| STOCH | 3min | PriceUpdate | 1 req |
| ATR | 3min | PriceUpdate | 1 req |
| ICHI | 5min | PriceUpdate | 1 req |
| VPROF | 5min | PriceUpdate | 1 req |
| FIBO | 5min | PriceUpdate | 1 req |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| API 速率 | 100 req/min (共享配额, 经 rate-limit 中间件) | prd.md §非功能要求 |
| 缓存 TTL | 1min-5min 按指标类型, jitter ±20% | prd.md §性能 |
| 延迟 | PriceFeed 更新后 30s 内推送 | prd.md §非功能要求 |
| v1 实现 | TradingView REST API (配额优先) | prd.md §技术约束 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 指标计算频率？ | 按 symbol 活跃度: 活跃 30s, 冷门 5min |
| Q2 | v1 vs v2？ | v1 TV API, 配额 > 80% 自动切本地计算 |
| Q3 | 缓存 TTL 是否需要 jitter？ | +20% 随机偏移防雪崩 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| API 配额耗尽 | 🟡 P1 | 100 req/min 共享 | 缓存 + 本地计算降级 |
| 指标数据延迟 | 🟡 P2 | 依赖 PriceFeed 更新频率 | PriceUpdate 事件驱动刷新 |
| 冷门缓存 MISS | 🟢 P3 | 长期未查询指标缓存空 | 惰性加载 + 配额兜底 |
| 缓存雪崩 | 🟡 P1 | 大量缓存同时过期 | TTL +20% jitter (claude-next.md: R27) |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | 指标计算引用 tradingview.com 文档或 npm 包文档 |
| 证据门禁 | 10 指标正确性 VERIFIED: 与已知数据集对齐 |
| 断言真实 | 缓存命中率不自称, 必须有统计数据 |

### kernel.md §错误处理铁律
- Error DNA: TV API 调用失败记录至 error-dna.jsonl
- 降级: v1→v2 自动切换, 不阻塞指标查询

### 反模式防范 (claude-next.md)
- [seed:typescript] API 响应类型: `IndicatorResponse = { value, confidence, source, delayed }`
- R24: 构建脚本避免 unquoted glob
- R27: 缓存命中率不自称"高"/">80%", 标注 `[内部自检，非行业标准]`

## 实现路径建议

1. **Phase 1**: getIndicator 接口 + TradingView REST API 客户端 (经 rate-limit 中间件)
2. **Phase 2**: IndicatorCache Redis (TTL 按类型 1min-5min + 20% jitter)
3. **Phase 3**: indicatorUpdate 自动推送 (PriceUpdate 事件驱动, 活跃/冷门差异化)
4. **Phase 4**: v2 本地计算降级 (ta.js, 配额 > 80% 自动切换)
