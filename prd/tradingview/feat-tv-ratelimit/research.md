# Research: TradingView Rate Limit & Cache

> 基于 `prd/tradingview/feat-tv-ratelimit/prd.md` · 2026-05-09
> Feature 职责：API 速率限制管理、缓存层、调用配额跟踪、智能批处理

---

## 关键调用链路

```
上游 feature 调用 TradingView API (getPrice / getIndicator / detectPattern)
  └─→ Rate Limit 中间件检查
        ├─→ Token Bucket 配额检查:
        │     ├─→ 配额 > 0 → 放行 → 配额 -1
        │     ├─→ 配额 = 0 → 缓存兜底检查
        │     │     ├─→ 缓存命中 → 返回缓存数据 (标记 source: "cache", confidence: "medium")
        │     │     └─→ 缓存未命中 → 返回 rate_limited + retry_after_sec
        │     └─→ refill 1.67 token/s (100/min, 每秒恢复约 1.67)
        ├─→ 并发安全: Redis atomic INCR key: tv_quota:{window_start_epoch}
        │     └─→ INCR 返回 ≤ 100 → 放行; > 100 → rate_limited
        ├─→ 配额追踪:
        │     └─→ 滑动窗口: window_start = floor(now/60)*60 → {used, limit=100, reset_at}
        └─→ 缓存策略:
              ├─→ 热门 symbol (TOP20): 强制缓存, 配额优先
              ├─→ 冷门 symbol: 惰性缓存, LRU 淘汰
              └─→ 缓存 MISS 时: 如果配额不足 → 排队到下一窗口

智能批处理:
  └─→ 请求合并窗口 (100ms)
        ├─→ 累积相同 symbol + indicator 的请求
        ├─→ 窗口结束 → 批量 API 调用 (1 次 TV API = 多 symbol)
        ├─→ 按请求方分发结果
        └─→ max 50 请求/批 (超限 → 分多批)

Token Bucket 算法:
  ┌─────────────────────────────────────────────────────────┐
  │ class TokenBucket {                                      │
  │   capacity: 100           // 最大令牌数                  │
  │   refillPerSecond: 1.67   // ≈ 100/60                    │
  │   lastRefill: timestamp    // 上次补充时间               │
  │   tokens: number           // 当前令牌数                 │
  │                                                          │
  │   tryConsume(): boolean {                                 │
  │     refill()               // 根据时间差补充令牌          │
  │     if (tokens > 0) { tokens--; return true }            │
  │     return false                                         │
  │   }                                                      │
  │ }                                                        │
  │                                                          │
  │ Redis 实现:                                              │
  │   key: tv_bucket:{symbol}                                │
  │   HGETALL → 计算 refill → HINCRBY tokens -1              │
  │   注: 跨 symbol 共享 100 配额                            │
  └─────────────────────────────────────────────────────────┘

缓存防雪崩:
  ├─→ 过期时间 +20% 随机偏移 (claude-next.md: R27)
  ├─→ 缓存 key: tv:{type}:{symbol}:{params_hash}
  ├─→ 热门 symbol 缓存永不过期 (主动刷新)
  └─→ 本地缓存 (LRU, max 1000 entry) 兜底 Redis 宕机
```

## 数据流

```
请求到达 → Token Bucket 检查 → 配额检查
  ├─→ 有余:
  │     └─→ 执行 API 调用
  │           ├─→ 成功 → 写入缓存 → 返回
  │           └─→ 失败 → 错误处理
  └─→ 耗尽:
        ├─→ 检查缓存 → 命中 → 返回缓存 (confidence: "medium")
        └─→ 缓存 miss → retry_after_sec + QUOTA_EXCEEDED

批处理:
  请求累积 (100ms) → 合并相同参数
    → 批量 API 调用 (1 req = 多 symbol)
    → 结果分发 (按 subscription_id)
```

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| API 速率 | 100 req/min (共享) | prd.md §非功能要求 |
| 批处理窗口 | 100ms | prd.md §性能 |
| 缓存策略 | Redis + 本地 LRU 两级 | prd.md §技术约束 |
| 缓存 TTL jitter | +20% 随机偏移 | kernel.md §防雪崩 |
| Token Bucket | capacity=100, refill=1.67/s | prd.md §非功能要求 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 限流算法？ | Token Bucket (capacity=100, refill=1.67/s), Redis atomic INCR |
| Q2 | 批处理窗口？ | 100ms, max 50 请求/批 |
| Q3 | 缓存分级？ | Redis 全局 + 本地 LRU (1000 entry) 双级 |
| Q4 | 配额跨 symbol 共享？ | 是, 全局 100 req/min |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 全局锁竞争 | 🟡 P2 | 高并发配额检查争抢 | Redis atomic INCR + 本地配额缓存 (50ms 刷新) |
| 缓存雪崩 | 🟡 P1 | 大量缓存同时过期 | TTL +20% jitter + 热门永不过期 |
| 批处理增加延迟 | 🟢 P3 | 100ms 窗口增加响应时间 | 窗口可配置, 紧急请求可跳过批处理 |
| Redis 宕机 | 🟡 P1 | 缓存不可用 | 本地 LRU 兜底 + 限流降级为放过 (kernel.md §降级) |
| 配额计数器偏移 | 🟢 P3 | INCR 计数和实际消耗不一致 | 定时校正 (每 5min 对齐实际配额) |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | Token Bucket 算法有 RFC 参考, 不自创 \\
| 断言真实 | retry_after_sec 不自称"准确", 引用 Redis TTL 数据 |
| 范围冻结 | 只负责限流/缓存, 不干涉业务数据 |

### kernel.md §错误处理铁律
- Redis 宕机 → 降级放过 (宁可多发, 不可漏发告警数据)
- Error DNA: 配额异常记录至 error-dna.jsonl

### 反模式防范 (claude-next.md)
- R24: 批处理 Bash 脚本 `for x in $PENDING` → `set -f`
- R27: 缓存命中率不自称 ">90%", 标注 `[内部自检]`
- R32: 本地 LRU 大小不自称"行业标准 optimial", 标注经验值

## 实现路径建议

1. **Phase 1**: Token Bucket 限流器 + Redis atomic INCR 配额检查
2. **Phase 2**: Redis 缓存层 + TTL jitter + 热门 symbol 策略
3. **Phase 3**: 智能批处理 (100ms 窗口 + 请求合并 + 分发)
4. **Phase 4**: 本地 LRU 兜底 + Redis 宕机降级
