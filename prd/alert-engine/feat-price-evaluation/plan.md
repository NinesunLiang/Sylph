# Plan: Price Evaluation

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: 价格评估引擎 + crosses 检测

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/price-eval/evaluator.ts`, `src/alert-engine/price-eval/cross-detector.ts`, `src/alert-engine/price-eval/history-tracker.ts` |
| 预估行数 | ~150 行 |
| 回滚方案 | `git checkout -- src/alert-engine/price-eval/` |

**验收标准：**
- [ ] above/below/crosses_above/crosses_below 全部正确 (Decimal.js 比较)
- [ ] crosses 方向检测需历史价格 (Redis: price:{alert_id}:previous, TTL 5min)
- [ ] 每条评估延迟 < 10ms
- [ ] 浮点数精度: Decimal.js, threshold ×100 整数存储

**边界/错误：**
- threshold = current_price (精确相等) → 不触发 (非 above 也非 below)
- crosses: prev = threshold (前值恰好在阈值上) → 按方向判断
- 历史价格 Redis miss → crosses 降级为 above/below 比较, 不报错
- symbol 格式非法 → 404 (由 TradingView Integration 校验, 本层不重复)

### Task 2: 批量评估 + PriceUpdate 消费 + 行情节流

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/price-eval/batch-evaluator.ts`, `src/alert-engine/price-eval/scheduler.ts`, `src/alert-engine/price-eval/price-update-consumer.ts`, `src/alert-engine/price-eval/throttle.ts` |
| 预估行数 | ~120 行 |
| 回滚方案 | `git checkout -- src/alert-engine/price-eval/` |

**验收标准：**
- [ ] 批量评估 1,000 告警/秒 (每批 ≤1K, 10 并发 worker)
- [ ] PriceUpdate 事件正确消费 (from TradingView Integration)
- [ ] 300ms 行情节流 (高水位丢弃 P2)
- [ ] 三态熔断调度: P0 10s, P1 30s, P2 60s 轮询补偿
- [ ] 事件驱动 + 定时轮询双通道 (引用 kernel.md §降级策略)

**边界/错误：**
- PriceUpdate 缺失 → 定时轮询兜底 (Closed→Open 熔断)
- 连续 3 次评估失败 → Open 态 (引用 AGENTS.md §修复上限)
- Half-Open 每 30s 试探, 成功→Closed
- 评估队列 >50K → 丢弃 P2 告警 (背压, 记录审计日志)
- Redis symbol→alert_ids miss → 回源 PostgreSQL 查询

### Task 3: 冷却窗口 + AlertConditionMet 发布

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/price-eval/cooldown.ts`, `src/alert-engine/price-eval/cooldown.lua`, `src/alert-engine/price-eval/event-publisher.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/alert-engine/price-eval/` |

**验收标准：**
- [ ] 5 分钟冷却窗口正确拦截 (Redis TTL, Lua atomic GET+SET)
- [ ] AlertConditionMet 事件正确发布 (含 alert_id, symbol, price, condition_type, triggered_at)
- [ ] 冷却 Redis TTL 精确到秒
- [ ] 并发请求不绕过冷却 (Lua 原子操作)

**边界/错误：**
- 冷却中 → 返回 {action: "cooldown", remaining_sec}, 不发布事件
- Redis 不可用 → 降级放过 (宁可多发, 不可漏发告警)
- 事件发布失败 → 重试 max 3 次 (1s 间隔), 第 3 次失败 → 写死信队列
- delivery_id 格式: `aev_{uuid_v4_short}` (kernel.md §命名强制)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 4 种条件逻辑 × 边界值 | Jest | Decimal 精度, 0 值, 负值 |
| 单元 | crosses 方向检测 | Jest | prev=threshold 边缘 |
| 集成 | 批量评估 + 冷却 | Jest + redis-mock | 并发下冷却原子性 |
| 集成 | PriceUpdate 消费 | Jest (mock event bus) | 事件→评估→发布链路 |
| 集成 | 三态熔断 | Jest (mock timer) | Closed→Open→Half-Open 转换 |
| 性能 | 1,000 eval/s | autocannon | P95 < 1ms/eval |
| 证据 | 每次声明必须 VERIFIED: | Jest expect | 引用 kernel.md §证据门禁 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/alert-engine/price-eval/evaluator.ts` | 新增 | 评估核心 (Decimal.js) |
| `src/alert-engine/price-eval/cross-detector.ts` | 新增 | crosses 方向检测 |
| `src/alert-engine/price-eval/history-tracker.ts` | 新增 | 历史价格追踪 (Redis) |
| `src/alert-engine/price-eval/batch-evaluator.ts` | 新增 | 批量评估 (1K/batch) |
| `src/alert-engine/price-eval/scheduler.ts` | 新增 | 三态熔断调度器 |
| `src/alert-engine/price-eval/price-update-consumer.ts` | 新增 | PriceUpdate 消费 |
| `src/alert-engine/price-eval/throttle.ts` | 新增 | 行情节流 300ms |
| `src/alert-engine/price-eval/cooldown.ts` | 新增 | 冷却检查 |
| `src/alert-engine/price-eval/cooldown.lua` | 新增 | Redis Lua 原子操作 |
| `src/alert-engine/price-eval/event-publisher.ts` | 新增 | AlertConditionMet 发布 |

---

## 非范围

- 不实现指标/AI 评估（由 Advanced Evaluation 负责）
- 不实现触发后处理（由 Trigger History 负责）
- 不实现告警 CRUD（由 Alert CRUD 负责）
- 不实现 TradingView 行情接入（由 TradingView Integration 负责）
