# Plan: Advanced Evaluation

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: 指标评估引擎 (前 4 指标 + Premium 门禁)

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/advanced-eval/indicator-evaluator.ts`, `src/alert-engine/advanced-eval/computations/rsi.ts`, `src/alert-engine/advanced-eval/computations/macd.ts`, `src/alert-engine/advanced-eval/computations/sma.ts`, `src/alert-engine/advanced-eval/computations/ema.ts`, `src/alert-engine/advanced-eval/tier-gate.ts` |
| 预估行数 | ~140 行 |
| 回滚方案 | `git checkout -- src/alert-engine/advanced-eval/` |

**验收标准：**
- [ ] RSI(14), MACD(12/26/9), SMA(20/50/200), EMA(12/26) 评估正确 (与已知数据集对齐)
- [ ] IndicatorUpdate 事件消费 + 触发评估
- [ ] Premium 门禁: tier:{user_id} 服务端校验, Free → TIER_RESTRICTED
- [ ] 缓存失效: IndicatorCache TTL 30s, 事件驱动刷新

**边界/错误：**
- tier cache miss → 回源 PostgreSQL, 更新 Redis cache (TTL 5min)
- Tier 门禁 Redis 不可用 → 降级放过 (stale-while-revalidate)
- 指标计算精度: Decimal.js, 与 TradingView 数据格式对齐
- IndicatorUpdate payload 缺少字段 → 400 VALIDATION_ERROR
- 缓存 TTL: RSI/MACD/SMA 30s, 用 IndicatorUpdate 事件续期

### Task 2: 全 10 指标 + AND/OR 组合

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/advanced-eval/computations/bb.ts`, `src/alert-engine/advanced-eval/computations/stoch.ts`, `src/alert-engine/advanced-eval/computations/atr.ts`, `src/alert-engine/advanced-eval/computations/ichi.ts`, `src/alert-engine/advanced-eval/computations/vprof.ts`, `src/alert-engine/advanced-eval/computations/fibo.ts`, `src/alert-engine/advanced-eval/combinator.ts` |
| 预估行数 | ~160 行 |
| 回滚方案 | `git checkout -- src/alert-engine/advanced-eval/computations/` |

**验收标准：**
- [ ] 全 10 指标评估正确 (BB, STOCH, ATR, ICHI, VPROF, FIBO)
- [ ] 各指标缓存 TTL 按类型配置 (30s~300s)
- [ ] AND/OR 组合逻辑正确 (单层: A AND B, A OR B)
- [ ] 多指标同时触发 → 合并为单条 AlertConditionMet (避免重复)
- [ ] 组合条件优先级: 括号强制分组, 无歧义

**边界/错误：**
- 组合条件为空 → 400 VALIDATION_ERROR
- 组合条件中单个指标评估失败 → 该条件为 false (不阻断整个评估)
- ICHI 云层数据不足 (新 symbol < 52 根 K 线) → INSUFFICIENT_DATA
- VPROF 无成交量历史 → 跳过成交量分析, 不阻断
- 全 10 指标评估总耗时 > 500ms → 拆分异步, 不阻塞事件循环

### Task 3: 模式检测 + 教育上下文

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/alert-engine/advanced-eval/pattern/pattern-detector.ts`, `src/alert-engine/advanced-eval/pattern/recognizers/hs.ts`, `src/alert-engine/advanced-eval/pattern/recognizers/double-top-bottom.ts`, `src/alert-engine/advanced-eval/pattern/recognizers/triangle.ts`, `src/alert-engine/advanced-eval/pattern/recognizers/wedge.ts`, `src/alert-engine/advanced-eval/pattern/recognizers/flag.ts`, `src/alert-engine/advanced-eval/education/education-context.ts` |
| 预估行数 | ~180 行 |
| 回滚方案 | `git checkout -- src/alert-engine/advanced-eval/pattern/` |

**验收标准：**
- [ ] 5 种形态识别正确 (含置信度 ≥ 0.5 才触发)
- [ ] 数据不足 (< 200 根 K 线) → INSUFFICIENT_DATA
- [ ] 教育上下文: 模板映射表, 含当前数值 (引用 claude-next.md §R27: 标注 `[内部自检，非行业标准]`)
- [ ] 模式检测异步 Worker, 不阻塞指标评估

**边界/错误：**
- K 线数据获取失败 → 跳过模式检测, 返回 PATTERN_UNAVAILABLE
- 置信度 0.0-1.0 范围, < 0.5 不触发 (配置硬阈值)
- 多形态同时满足 → 返回置信度最高的一条
- 模式检测耗时 > 2s → 超时中断, 返回 TIMEOUT
- 置信度评分 `[内部自检，非行业标准]` (R27 防伪诚信剧场)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 各指标评估逻辑 | Jest | 与 TradingView 已知数据集对齐 |
| 单元 | 组合条件 (AND/OR) | Jest | 单层 + 多条件合并 |
| 集成 | IndicatorUpdate 消费 | Jest (mock event bus) | 事件→评估→发布 |
| 集成 | 模式检测 | Jest (mock K 线数据) | 5 形态识别 + 置信度 |
| 安全 | Premium 门禁 | Jest | Free → TIER_RESTRICTED, 无绕过 |
| 证据 | 置信度评分来源 | Jest | `[内部自检，非行业标准]` 标注 |
| 性能 | 全指标评估 | autocannon | < 500ms/alert |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/alert-engine/advanced-eval/indicator-evaluator.ts` | 新增 | 指标评估入口 |
| `src/alert-engine/advanced-eval/tier-gate.ts` | 新增 | Premium 门禁 (Redis + 回源) |
| `src/alert-engine/advanced-eval/computations/rsi.ts` | 新增 | RSI(14) |
| `src/alert-engine/advanced-eval/computations/macd.ts` | 新增 | MACD(12/26/9) |
| `src/alert-engine/advanced-eval/computations/sma.ts` | 新增 | SMA(20/50/200) |
| `src/alert-engine/advanced-eval/computations/ema.ts` | 新增 | EMA(12/26) |
| `src/alert-engine/advanced-eval/computations/bb.ts` | 新增 | BB(20,2σ) |
| `src/alert-engine/advanced-eval/computations/stoch.ts` | 新增 | STOCH(14/3/3) |
| `src/alert-engine/advanced-eval/computations/atr.ts` | 新增 | ATR(14) |
| `src/alert-engine/advanced-eval/computations/ichi.ts` | 新增 | ICHI(9/26/52) |
| `src/alert-engine/advanced-eval/computations/vprof.ts` | 新增 | VPROF |
| `src/alert-engine/advanced-eval/computations/fibo.ts` | 新增 | FIBO(0.236-0.786) |
| `src/alert-engine/advanced-eval/combinator.ts` | 新增 | AND/OR 组合 |
| `src/alert-engine/advanced-eval/pattern/pattern-detector.ts` | 新增 | 模式检测入口 |
| `src/alert-engine/advanced-eval/pattern/recognizers/*.ts` | 新增 | 5 形态识别器 |
| `src/alert-engine/advanced-eval/education/education-context.ts` | 新增 | 教育上下文 |

---

## 非范围

- 不实现价格告警评估（由 Price Evaluation 负责）
- 不实现 ML 模型训练（v1 规则引擎）
- 不实现 TradingView 数据接入（由 TradingView Integration 负责）
