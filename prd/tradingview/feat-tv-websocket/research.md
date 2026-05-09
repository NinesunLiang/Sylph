# Research: TradingView WebSocket & Price Feed

> 基于 `prd/tradingview/feat-tv-websocket/prd.md` · 2026-05-09
> Feature 职责：WebSocket 连接管理、实时行情推送、价格数据查询

---

## 关键调用链路

```
WebSocket 连接初始化
  └─→ 连接 TradingView WebSocket 服务 (wss://*.tradingview.com/ws)
        ├─→ 鉴权: API Key + 会话 Token (env 读取, kernel.md §非硬编码)
        ├─→ 订阅 symbol 列表 (subscribePrice: symbol, webhook_url → subscription_id)
        ├─→ 连接维护: 心跳 ping/pong (每 30s), empty pong → 断开
        ├─→ 连接池: 支持 10,000 并发 (内存: ~2MB/连接, 总计 ~20GB)
        └─→ 断线重连: exponential backoff 1s→2s→4s→8s→max 30s (kernel.md §修复上限)
              └─→ 4 次失败 → Open 态, 降级 REST API polling (30s)

实时行情推送 (priceUpdate outbound)
  └─→ WebSocket 收到行情帧
        ├─→ 解析: priceParser (symbol, price, change_24h, volume, timestamp)
        │     └─→ 格式校验: price > 0, timestamp < now + 5s (防未来时间戳)
        ├─→ 写入 PriceFeed 缓存 (Redis: price:{symbol}, TTL 30s 热门/60s 冷门)
        │     └─→ TTL 加随机偏移 ±20% 防雪崩 (claude-next.md: R27)
        ├─→ 发布 PriceUpdate 事件 (→ Alert Engine)
        │     {event: "PriceUpdate", symbol, price, timestamp}
        └─→ WebSocket 推送订阅者 (subscription_manager.deliver(symbol, data))

价格查询 (getPrice)
  └─→ GET /api/price/{symbol}
        ├─→ 查询 PriceFeed 缓存 (Redis: price:{symbol})
        │     ├─→ 命中 → {price, timestamp, source: "cache"}
        │     └─→ miss → TradingView REST API (经 rate-limit 中间件)
        │           ├─→ 成功 → 写入缓存 → {price, timestamp, source: "tv", delay_ms}
        │           └─→ 429 → RATE_LIMITED
        │           └─→ 5xx → SYMBOL_NOT_FOUND
        └─→ 数据延迟标记:
              ├─→ < 5s → confidence: "high"
              ├─→ 5-30s → "medium" (降级可用)
              └─→ > 30s → "low" (触发告警降级, prd.md §非功能要求)

订阅管理 (subscribePrice / unsubscribePrice)
  └─→ subscribePrice(symbol, webhook_url):
        ├─→ 检查是否重复 (已订阅则返回已有 subscription_id)
        ├─→ 创建 subscription_id (uuid_v4)
        ├─→ 写入 subscription 表: {id, symbol, webhook_url, created_at}
        ├─→ 若首次订阅该 symbol → WebSocket 订阅
        └─→ 返回 subscription_id

  └─→ unsubscribePrice(subscription_id):
        ├─→ 删除 subscription
        ├─→ 若该 symbol 无其他订阅 → WebSocket 退订
        └─→ 返回 204

降级策略 (三态熔断):
  ├─→ Closed: WebSocket 正常, 实时推送
  ├─→ Open: 断连 > 4 次 → REST API polling (30s)
  │     └─→ 数据标记 confidence: "medium" (prd.md §降级告警)
  └─→ Half-Open: 每 60s 试探 WebSocket 重连
        └─→ 成功 → Closed; 失败 → Open
```

## 数据流

| 步骤 | 输入 | 处理 | 输出 | 存储 | TTL |
|------|------|------|------|------|-----|
| WS 接收 | TradingView 帧 | 解析 + 校验 | price, change, volume | — | — |
| 缓存写入 | parsed data | Redis SET | PriceUpdate 事件 | Redis (price:{symbol}) | 30s/60s ±20% |
| 事件发布 | symbol, price | 发布 PriceUpdate | → Alert Engine | Redis Pub/Sub | — |
| getPrice | symbol | cache → REST | {price, source, delay} | — | — |
| 订阅 | symbol, webhook | 创建 sub_id | subscription_id | 数据库 | — |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 数据延迟 | < 5 秒 (P95) | prd.md §非功能要求 |
| WebSocket 连接 | 10,000 并发 | prd.md §非功能要求 |
| 降级 | 延迟 > 5s → confidence medium/low | prd.md §非功能要求 |
| 断线重连 | exponential backoff 1s→30s | kernel.md §修复上限 |
| 缓存 TTL | 热门 30s, 冷门 60s ±20% jitter | prd.md §性能 |
| API Key | env 读取, 非硬编码 | kernel.md §隐私防线 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 缓存 TTL 策略？ | 热门 symbol (交易量 TOP20) 30s, 其余 60s ±20% jitter |
| Q2 | 断线重连策略？ | exponential backoff 1s/2s/4s/8s/16s/30s, 4 次 → Open |
| Q3 | WebSocket 鉴权？ | API Key + 会话 Token (env 读取, 非硬编码) |
| Q4 | 10,000 并发连接内存预算？ | ~2MB/连接, 总计 ~20GB, 需监控告警 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| WebSocket 断连 | 🟡 P1 | 网络故障 → 行情中断 | exponential backoff + REST polling 降级 |
| 连接数超限 | 🟡 P2 | >10,000 并发 | 连接池 + LRU 驱逐最不活跃 |
| 数据延迟 > 5s | 🟡 P2 | 缓存 miss + API 慢 | confidence 标记 + 降级 |
| 内存泄漏 | 🟢 P3 | 长连接累积未清理 | 定时健康检查 + 30min 不活跃关闭 |
| 缓存雪崩 | 🟡 P1 | 大量同时过期 | TTL +20% jitter (claude-next.md: R27) |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | WebSocket 帧结构从 TradingView 文档导入, 不自造 |
| 隐私防线 | API Key + Token 从 env 读取, 不在代码中硬编码 |
| 范围冻结 | 不实现指标/模式检测 |

### kernel.md §错误处理铁律
- Hook 永不阻塞: WebSocket 帧解析 try/catch, 失败帧跳过不崩溃
- Error DNA: 断连原因自动记录至 error-dna.jsonl
- 非硬编码: API Key 环境变量, 缺失则 fail-fast 启动报错

### 反模式防范 (claude-next.md)
- R24: 启动脚本 `for x in $SYMBOLS` → `set -f`
- R27: 延迟 < 5s 不自称达标, 必须有 P95 计时数据
- R31: gh CLI 操作不涉及本 feature

## 实现路径建议

1. **Phase 1**: WebSocket 连接管理 (连接/鉴权/心跳 ping/pong 30s)
2. **Phase 2**: 行情数据接收 + priceParser (格式校验) + PriceFeed Redis 缓存 (TTL jitter)
3. **Phase 3**: PriceUpdate 事件发布 + 订阅管理 (subscribe/unsubscribe)
4. **Phase 4**: 断线重连 exponential backoff + REST polling 降级 (三态熔断)
5. **Phase 5**: 10,000 并发连接池 + 健康检查 + 不活跃驱逐
