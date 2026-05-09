# Plan: TradingView Pattern Detection

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: 规则引擎几何形态检测

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/patterns/pattern-detector.ts`, `src/tradingview/patterns/pattern-rules.ts`, `src/tradingview/patterns/data-sufficiency.ts` |
| 预估行数 | ~100 行 |
| 回滚方案 | `git checkout -- src/tradingview/patterns/` |

**验收标准：**
- [ ] 5 种形态可检测: Head & Shoulders, Double Top/Bottom, Triangle, Wedge, Flag
- [ ] 每种形态的几何规则正确 (看形态检测规则表)
- [ ] 数据量 < 200 点 → INSUFFICIENT_DATA
- [ ] detetectPattern 返回 {detected, pattern, confidence, description}

**边界/错误：**
- 数据量 200 点边缘 → 返回结果, 但 confidence -0.1 惩罚
- 多形态同时匹配 → 返回置信度最高的一条
- 无匹配 → detected: false, pattern: null
- symbol 无任何历史数据 → INSUFFICIENT_DATA (不开心的路径)
- pattern_types 为空数组 → 检测全部 5 种

### Task 2: 置信度评分 + [内部自检] 标注

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/patterns/confidence-scorer.ts` |
| 预估行数 | ~40 行 |
| 回滚方案 | `git checkout -- src/tradingview/patterns/confidence-scorer.ts` |

**验收标准：**
- [ ] 置信度评分 0-1, ≥0.6 有效
- [ ] 输出强制标注 `[内部自检，非行业标准]` (R27, 不可配置)
- [ ] 边缘检测 0.3-0.6: 记录但不触发

**边界/错误：**
- 置信度 = 0 → 形态检测完全失败, 不输出
- 置信度 = 1 → 理论上限, 实际不可能达到 (标注不可达)
- 多因子的权重和 ≠ 1 → 归一化校正
- R27 标注是静态字符串, 不可被配置覆盖 (hard-coded)

### Task 3: 批处理 + 缓存 + 冷却

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/tradingview/patterns/batch-detector.ts`, `src/tradingview/patterns/pattern-cache.ts`, `src/tradingview/patterns/pattern-store.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/tradingview/patterns/batch-detector.ts` |

**验收标准：**
- [ ] 50K 告警批处理 (Bull 队列, 10 并发 Worker, 每批 ≤100)
- [ ] PatternDetection 实体 CR 正确
- [ ] 检测冷却: 命中后 30min 不重复 (Redis TTL 1800s)
- [ ] 批处理遍历: 每 5min 活跃 symbol

**边界/错误：**
- 单个 symbol 检测失败 → 跳过, 不影响批次 (kernel.md §修复上限)
- 冷却中 → 返回已有缓存结果 (非 429)
- 缓存满 → LRU 驱逐最旧结果
- 批处理时间 > 5min → 等待完成, 不并发 (锁)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 5 种形态几何检测 | Jest | 模拟 K 线数据, 含边缘 |
| 单元 | 置信度评分 0-1 | Jest | ≥0.6, 归一化, 标注 |
| 集成 | 批处理 (Bull mock) | Jest | 50K, 10 Workers |
| 集成 | 冷却 + 缓存 | Jest (redis-mock) | 30min TTL, LRU |
| 安全 | R27 标注不可覆盖 | Jest | 静态字符串检查 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/tradingview/patterns/pattern-detector.ts` | 新增 | 检测主引擎 |
| `src/tradingview/patterns/pattern-rules.ts` | 新增 | 5 形态几何规则 |
| `src/tradingview/patterns/data-sufficiency.ts` | 新增 | 数据量 ≥200 检查 |
| `src/tradingview/patterns/confidence-scorer.ts` | 新增 | 置信度 0-1 + R27 标注 |
| `src/tradingview/patterns/batch-detector.ts` | 新增 | Bull 批处理 |
| `src/tradingview/patterns/pattern-cache.ts` | 新增 | Redis 缓存 (LRU) |
| `src/tradingview/patterns/pattern-store.ts` | 新增 | 持久化 |

---

## 非范围

- 不实现实时行情数据（由 WebSocket & Price Feed 负责）
- 不实现技术指标计算（由 Indicator Data 负责）
- 不实现 API 速率限制（由 Rate Limit 负责）
- 不实现 ML 模型（v2 计划）
