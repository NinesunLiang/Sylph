# Plan: TradingView Indicator Data

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: getIndicator 接口 + TradingView REST API

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/indicators/indicator-client.ts`, `src/tradingview/indicators/get-indicator.ts`, `src/tradingview/indicators/indicator-validator.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/tradingview/indicators/` |

**验收标准：**
- [ ] getIndicator 返回 {value, confidence, source, delayed}
- [ ] 10 个常用指标数据可获取 (RSI, MACD, SMA, EMA, BB, STOCH, ATR, ICHI, VPROF, FIBO)
- [ ] 经 rate-limit 中间件 (共享 100 req/min 配额)
- [ ] 格式校验: value 类型正确, confidence 0-1, delayed boolean

**边界/错误：**
- 指标类型不合法 → 400 VALIDATION_ERROR
- params 缺失 → 使用默认值 (RSI period=14, SMA period=20, ...)
- TV API 429 → RATE_LIMITED + 缓存兜底
- TV API 5xx → INDICATOR_ERROR
- symbol 不存在 → SYMBOL_NOT_FOUND
- 经 rate-limit (feat-tv-ratelimit), 这里不重复实现

### Task 2: IndicatorCache + 过期策略

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/indicators/indicator-cache.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/tradingview/indicators/indicator-cache.ts` |

**验收标准：**
- [ ] Redis 缓存读写正确 (key: indicator:{symbol}:{type})
- [ ] 差异化过期: RSI/MACD 60s, 趋势 3min, 低频 5min
- [ ] TTL +20% 随机偏移防雪崩
- [ ] 缓存命中率统计 (用于配额优化决策)

**边界/错误：**
- Redis miss → 回源 TV API + 写缓存
- Redis SET 失败 → 降级直连 TV API (不缓存)
- 缓存数据格式不兼容 (版本变更) → 清除 + 回源
- 缓存统计: hits/total, 用于触发 v1→v2 切换

### Task 3: indicatorUpdate 自动推送

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/indicators/indicator-refresh-trigger.ts`, `src/tradingview/indicators/indicator-event-publisher.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/tradingview/indicators/indicator-refresh-trigger.ts` |

**验收标准：**
- [ ] PriceUpdate 事件到达 → 触发指标重算 (活跃 symbol)
- [ ] 活跃 symbol 30s, 冷门 5min 刷新频率
- [ ] IndicatorUpdate 事件发布: {event, symbol, indicator, value, confidence, timestamp}
- [ ] 无订阅者/无活跃告警的 symbol 跳过计算 (省配额)

**边界/错误：**
- PriceUpdate 事件丢失 → 定时兜底 max 5min
- 同时触发的指标计算 → 队列化 (单 symbol 串行, 防配额突增)
- TV API 失败 → 跳过本轮刷新 (下次重试)
- 批量 symbol 刷新 → 经 rate-limit 中间件排队

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 指标参数校验 + 默认值 | Jest | 合法/非法参数 |
| 单元 | 缓存 TTL + jitter | Jest | 差异化 + ±20% |
| 集成 | TV API (mock) | Jest | 200/429/5xx + 10 指标 |
| 集成 | 事件驱动刷新 (mock bus) | Jest | PriceUpdate→IndicatorUpdate |
| 集成 | v1→v2 自动切换 | Jest | 配额 > 80% 触发 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/tradingview/indicators/indicator-client.ts` | 新增 | TV REST API 客户端 |
| `src/tradingview/indicators/get-indicator.ts` | 新增 | 查询接口 (经 rate-limit) |
| `src/tradingview/indicators/indicator-validator.ts` | 新增 | 参数校验 |
| `src/tradingview/indicators/indicator-cache.ts` | 新增 | Redis 缓存 (TTL jitter) |
| `src/tradingview/indicators/indicator-refresh-trigger.ts` | 新增 | PriceUpdate 触发刷新 |
| `src/tradingview/indicators/indicator-event-publisher.ts` | 新增 | IndicatorUpdate 发布 |

---

## 非范围

- 不实现实时行情数据（由 WebSocket & Price Feed 负责）
- 不实现 AI 模式检测（由 Pattern Detection 负责）
- 不实现 API 速率限制状态机（由 Rate Limit 负责）
- 不实现本地计算引擎 v2（v2 计划）
