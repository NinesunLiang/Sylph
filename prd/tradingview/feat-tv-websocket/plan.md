# Plan: TradingView WebSocket & Price Feed

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: WebSocket 连接管理

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/websocket/ws-manager.ts`, `src/tradingview/websocket/ws-auth.ts`, `src/tradingview/websocket/heartbeat.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/tradingview/websocket/` |

**验收标准：**
- [ ] TradingView WS 连接成功 (wss://*.tradingview.com/ws, 鉴权通过)
- [ ] 心跳 ping/pong 每 30s, pong 超时 10s → 断开触发重连
- [ ] 连接池: 支持 10,000 并发 (内存 ~2MB/连接)
- [ ] API Key + Token 从 env 读取, 缺失 → fail-fast

**边界/错误：**
- WS 连接超时 (10s) → 触发重连
- 鉴权失败 → 403 AUTH_FAILED + 审计日志
- ping pong 丢失 → 3 次无响应 → 断开 + 重连 (kernel.md §修复上限)
- 内存超限 → 池满 → LRU 驱逐最不活跃连接
- env 缺失 → 启动失败 (非运行时 panic, kernel.md §fail-fast)

### Task 2: 行情接收 + 缓存 + 事件发布

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/websocket/price-feed-cache.ts`, `src/tradingview/websocket/price-parser.ts`, `src/tradingview/websocket/price-event-publisher.ts` |
| 预估行数 | ~70 行 |
| 回滚方案 | `git checkout -- src/tradingview/websocket/price-feed-cache.ts` |

**验收标准：**
- [ ] 行情数据正确解析: symbol, price, change_24h, volume, timestamp
- [ ] 格式校验: price > 0, timestamp < now + 5s
- [ ] PriceFeed Redis 缓存: 热门 30s, 冷门 60s ±20% jitter
- [ ] PriceUpdate 事件发布: {event, symbol, price, timestamp}
- [ ] 延迟标记: <5s high, 5-30s medium, >30s low

**边界/错误：**
- 帧格式非法 → JSON parse fail → LOG_WARNING + 跳过 (不崩溃)
- 价格 ≤ 0 → LOG_ERROR + 丢弃
- 未来时间戳 (timestamp > now + 5s) → 截断为 now
- Redis SET 失败 → LOG_ERROR + 事件照发 (缓存降级)
- 事件发布失败 → 重试 3 次, 第 3 次 → 死信队列

### Task 3: 订阅管理 + 断线重连

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/websocket/subscription-manager.ts`, `src/tradingview/websocket/reconnect-handler.ts`, `src/tradingview/websocket/websocket-middleware.ts` |
| 预估行数 | ~70 行 |
| 回滚方案 | `git checkout -- src/tradingview/websocket/subscription-manager.ts` |

**验收标准：**
- [ ] subscribePrice/unsubscribePrice 正确 (幂等, 重复返回已有 sub_id)
- [ ] 断线重连: 1s→2s→4s→8s→16s→30s (max), 4 次→Open
- [ ] Open 态 → REST API polling (30s), confidence="medium"
- [ ] Half-Open: 每 60s 试探重连
- [ ] getPrice: cache → REST (经 rate-limit 中间件)

**边界/错误：**
- 重复订阅同一 symbol → 返回已有 subscription_id (非 400)
- 退订不存在的 subscription_id → 404 NOT_FOUND
- 重连中行情请求 → REST API 兜底 (数据标记 delayed)
- 第 4 次重连失败 → Open 态 + 审计日志
- 重连成功后 → 重新订阅所有 symbol (恢复连接池)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | priceParser + 格式校验 | Jest | 合法/非法帧 |
| 单元 | 心跳逻辑 | Jest | 30s ping, 3 次超时 |
| 集成 | WebSocket (mock server) | Jest | 连接/鉴权/重连/心跳 |
| 集成 | Redis 缓存 + TTL | Jest (redis-mock) | jitter ±20% |
| 集成 | 事件发布 (mock bus) | Jest | PriceUpdate 载荷 + 重试 |
| 集成 | 订阅/退订/幂等 | Jest | CRUD 正确 |
| 性能 | 10,000 连接模拟 | autocannon | 内存 < 20GB |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/tradingview/websocket/ws-manager.ts` | 新增 | 连接池管理 |
| `src/tradingview/websocket/ws-auth.ts` | 新增 | 鉴权 (env key) |
| `src/tradingview/websocket/heartbeat.ts` | 新增 | 心跳 ping/pong |
| `src/tradingview/websocket/price-parser.ts` | 新增 | 帧解析 + 校验 |
| `src/tradingview/websocket/price-feed-cache.ts` | 新增 | Redis 缓存 (TTL jitter) |
| `src/tradingview/websocket/price-event-publisher.ts` | 新增 | PriceUpdate 发布 |
| `src/tradingview/websocket/subscription-manager.ts` | 新增 | 订阅 CRUD |
| `src/tradingview/websocket/reconnect-handler.ts` | 新增 | exponential backoff |
| `src/tradingview/websocket/websocket-middleware.ts` | 新增 | 序列图/REST 网关 |

---

## 非范围

- 不实现技术指标计算（由 Indicator Data 负责）
- 不实现 AI 模式检测（由 Pattern Detection 负责）
- 不实现 API 速率限制（由 Rate Limit 负责）
- 不实现告警条件评估（由 Alert Engine 负责）
