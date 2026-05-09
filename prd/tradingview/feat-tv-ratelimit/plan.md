# Plan: TradingView Rate Limit & Cache

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: Token Bucket 限流器 + 配额跟踪

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/ratelimit/token-bucket.ts`, `src/tradingview/ratelimit/rate-limit-middleware.ts`, `src/tradingview/ratelimit/quota-store.ts` |
| 预估行数 | ~70 行 |
| 回滚方案 | `git checkout -- src/tradingview/ratelimit/` |

**验收标准：**
- [ ] Token Bucket: capacity=100, refill=1.67/s
- [ ] Redis atomic INCR 配额检查 (key: tv_quota:{window})
- [ ] 配额 = 0 → 返回 rate_limited + retry_after_sec
- [ ] APIRateLimitState 持久化: {used, limit, reset_at}
- [ ] 滑动窗口: window_start = floor(now/60)*60
- [ ] 定时校正: 每 5min 对齐实际配额

**边界/错误：**
- Redis INCR 失败 → 降级放过 (不阻断业务, kernel.md §降级)
- 同一窗口并发 INCR → 原子保证 (Redis atomic)
- 窗口切换抖动 → 前一窗口计数 + 新窗口同时双重检查
- retry_after_sec = reset_at - now (精确到秒)
- 校正发现 INCR 和实际配额偏移 → 重置为 min(INCR, 100)

### Task 2: Redis + 本地缓存层

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/ratelimit/cache-manager.ts`, `src/tradingview/ratelimit/cache-middleware.ts`, `src/tradingview/ratelimit/lru-cache.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/tradingview/ratelimit/cache-manager.ts` |

**验收标准：**
- [ ] Redis 缓存读写: key tv:{type}:{symbol}:{params_hash}
- [ ] TTL +20% 随机偏移防雪崩
- [ ] 热门 symbol (TOP20) 缓存永不过期 (事件驱动刷新)
- [ ] 本地 LRU (max 1000 entry) 兜底 Redis 宕机
- [ ] 缓存命中率统计 (hits/total)

**边界/错误：**
- Redis 宕机 → 本地 LRU 兜底 + 限流降级放过
- 缓存数据格式不兼容 → 清除 + 回源
- LRU 满 → 驱逐最旧 (kernel.md §最小影响)
- 热门 symbol 列表变更 → 主动刷新缓存 (不等待 TTL)
- 缓存命中率不自称 ">90%", 标注 `[内部自检，非行业标准]` (R27)

### Task 3: 智能批处理

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/ratelimit/batch-merge.ts`, `src/tradingview/ratelimit/batch-dispatcher.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/tradingview/ratelimit/batch-merge.ts` |

**验收标准：**
- [ ] 100ms 请求合并窗口
- [ ] 相同 symbol + indicator 请求合并为单批
- [ ] 批处理分发: 每批 max 50 请求
- [ ] 紧急请求可跳过批处理 (header: x-skip-batch: true)

**边界/错误：**
- 窗口内到达请求 < 2 → 不等待, 立即执行 (减少延迟)
- 窗口满 (50) → 提前结束窗口, 立即执行
- 合并后 API 调用失败 → 逐请求方返回错误 (不丢失)
- 紧急请求跳过批处理 → 仍走配额检查

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | Token Bucket 算法 | Jest | capacity=100, refill 精确, 边界 |
| 单元 | Redis atomic INCR + 窗口 | Jest (redis-mock) | 并发安全, 窗口切换 |
| 单元 | TTL jitter ±20% | Jest | 随机偏移统计 |
| 集成 | 缓存读写 + LRU | Jest | Redis 宕机降级 |
| 集成 | 批处理合并 + 分发 | Jest | 合并正确, 紧急跳过 |
| 性能 | 100 req/min 连续 10 窗口 | autocannon | 第 100 条 rate_limited |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/tradingview/ratelimit/token-bucket.ts` | 新增 | Token Bucket (capacity=100) |
| `src/tradingview/ratelimit/rate-limit-middleware.ts` | 新增 | 限流中间件 |
| `src/tradingview/ratelimit/quota-store.ts` | 新增 | Redis 配额追踪 |
| `src/tradingview/ratelimit/cache-manager.ts` | 新增 | Redis 缓存 (TTL jitter) |
| `src/tradingview/ratelimit/cache-middleware.ts` | 新增 | 缓存中间件 |
| `src/tradingview/ratelimit/lru-cache.ts` | 新增 | 本地 LRU 兜底 |
| `src/tradingview/ratelimit/batch-merge.ts` | 新增 | 请求合并 100ms |
| `src/tradingview/ratelimit/batch-dispatcher.ts` | 新增 | 批处理分发 |

---

## 非范围

- 不实现 WebSocket 连接管理（由 WebSocket & Price Feed 负责）
- 不实现技术指标计算（由 Indicator Data 负责）
- 不实现 AI 模式检测（由 Pattern Detection 负责）
- 不实现具体业务数据查询（由各上游 feature 负责）
