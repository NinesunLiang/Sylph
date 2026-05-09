# Research: Price Evaluation

> 基于 `prd/alert-engine/feat-price-evaluation/prd.md` · 2026-05-09
> Feature 职责：价格水平告警条件实时评估（above/below/crosses）

---

## 关键调用链路

```
入站事件: PriceUpdate (symbol, price, timestamp) from TradingView Integration
  └─→ throttle 300ms (高波动期行情节流)
        └─→ batchEvaluate(active_alert_ids[], prices)
              ├─→ 从 Redis 读取该 symbol 的活跃告警 ID 列表 (symbol:{symbol}:active_alert_ids)
              │     └─→ cache miss → 查询 PostgreSQL: SELECT id FROM alerts WHERE symbol=$1 AND status='active'
              ├─→ 分批评估 (每批 ≤1000 条, 10 并发 worker)
              │     ├─→ price_above: current_price > threshold → triggered
              │     ├─→ price_below: current_price < threshold → triggered
              │     └─→ price_crosses_above/below:
              │           ├─→ Redis: GET price:{alert_id}:previous (存上次评估价格)
              │           ├─→ prev ≤ threshold < current → crosses_above
              │           ├─→ prev ≥ threshold > current → crosses_below
              │           └─→ 更新 Redis: SET price:{alert_id}:previous current_price EX 300 (5min TTL)
              ├─→ triggered → 冷却检查 (Redis: cooldown:{alert_id})
              │     ├─→ 冷却中 → 跳过, 返回 {action: "cooldown", remaining_sec}
              │     └─→ 未冷却 → 发布 AlertConditionMet 事件
              │           {alert_id, symbol, price, condition_type, triggered_at}
              └─→ 返回 {evaluated: N, triggered: M, errors: K}

调度策略（降级补偿 — 三态熔断，引用 AGENTS.md §修复上限）:
  ├─→ 正常态: 每收到 PriceUpdate 事件立即触发 batchEvaluate
  │     └─→ 熔断条件: 连续 3 次评估报错 → Open 态
  ├─→ Open 态: 切换定时轮询
  │     ├─→ P0 告警: 每 10s
  │     ├─→ P1 告警: 每 30s
  │     └─→ P2 告警: 每 60s
  └─→ Half-Open 态: 每 30s 试探一次事件驱动, 成功→Closed

浮点数比较策略 (kernel.md §精度要求):
  ├─→ 所有 threshold 和 price 以 Decimal 类型存储 (非 float)
  ├─→ 比较: price.minus(threshold).signum() — 避免 0.1 + 0.2 = 0.30000000000000004
  └─→ crosses 方向: (prev.minus(threshold).signum() != current.minus(threshold).signum()) → crossed
```

## 数据流

| 步骤 | 输入 | 处理 | 输出 | 存储 | 缓存 |
|------|------|------|------|------|------|
| 价格接收 | PriceUpdate | 按 symbol 路由 → Redis 读活跃告警 | alert_ids[] | Redis (symbol→alert_ids) | TTL 60s, jitter ±20% |
| 条件评估 | alert_id, current_price | Decimal 比较 threshold + 方向 | triggered/false | — | — |
| crosses 检测 | alert_id, current_price | 读 prev → 比较 → 写 prev | triggered/false | Redis (price:{id}:previous) | TTL 300s |
| 冷却检查 | alert_id | Redis TTL GET → 已冷却/未冷却 | pass/block | Redis (cooldown:{id}) | 5min |
| 事件发布 | triggered count | 发布 AlertConditionMet | — | Redis Pub/Sub | — |
| 行情节流 | PriceUpdate 流 | 300ms throttle (高水位丢弃) | — | 内存 | 窗口计数器 |
| 背压控制 | 评估队列 | >50K 待评估 → 丢弃 P2 | — | 内存 | 水位标记 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 评估延迟 | 条件满足后 < 30 秒触发 | prd.md §非功能要求 |
| 并发评估 | 1,000 评估/秒 | prd.md §非功能要求 |
| 总容量 | 50,000+ 告警 | prd.md §非功能要求 |
| 冷却窗口 | 5 分钟（同一告警去重） | prd.md §非功能要求 |
| 精度 | Decimal 浮点数比较 | kernel.md §精度要求 |
| 行情节流 | 300ms throttle | prd.md §性能 |
| 总容量 | 最多同时 50K 活跃告警 | prd.md §非功能要求 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | crosses 方向精度？ | 需要前次评估价格 (Redis 存最近 1 个价格点, TTL 5min) |
| Q2 | 批量评估上限？ | 单批次 ≤1000, 超限分页, 每页 10 并发 worker |
| Q3 | PriceUpdate 漏处理 → 兜底？ | 事件驱动 + 定时轮询 (三态熔断) |
| Q4 | 浮点数比较？ | Decimal.js, threshold×100 整数比较 |
| Q5 | 行情节流策略？ | 300ms throttle, 高水位时丢弃 P2 告警 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| PriceUpdate 风暴 | 🟡 P1 | 高波动期大量 tick 涌入 | 300ms throttle + P2 丢弃 (背压) |
| 冷却窗口绕过 | 🟡 P2 | 并发请求同时通过冷却 | Redis Lua atomic GET+SET |
| crosses 精度 | 🟡 P2 | 浮点数误差导致误判 | Decimal.js 全量比较 |
| 评估队列积压 | 🟡 P1 | CPU 跟不上评估速率 | 10 并发 worker + 水位告警 |
| 熔断错误恢复 | 🟢 P3 | Open 态无法自动回归 | Half-Open 30s 试探 |

## 项目特定引用

### AGENTS.md §三重门 映射
| 门禁 | 应用 |
|------|------|
| Gate-X | 熔断策略变更需二次批准 |
| 修复上限 3 轮 | 评估引擎连续 3 次测试失败 → BLOCKED 升级 |
| 证据门禁 | 每次 batchEvaluate 必须 VERIFIED: 评估延迟 |

### kernel.md §错误处理铁律 映射
- Hook 永不阻塞: throttle 模块不允许 exit 2
- Error DNA: 评估异常自动记录至 error-dna.jsonl
- 降级: Redis 不可用 → 降级为纯直接比较 (放弃 crosses 方向检测)

### 反模式防范 (claude-next.md §R24)
- R24: 调度器 Bash 脚本中 `for alert_id in $ACTIVE_IDS` 必须加双引号或 `set -f`

## 实现路径建议

1. **Phase 1**: 单条价格评估引擎 (above/below/crosses) + Decimal.js 比较
2. **Phase 2**: crosses 方向检测 (Redis 历史价格追踪, TTL 5min)
3. **Phase 3**: PriceUpdate 事件消费 + 批量评估 (1K/batch, 10 workers)
4. **Phase 4**: 冷却窗口 (Redis Lua atomic) + AlertConditionMet 发布
5. **Phase 5**: 行情节流 (300ms) + 三态熔断调度 + 背压控制
