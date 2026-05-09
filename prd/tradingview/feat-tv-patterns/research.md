# Research: TradingView Pattern Detection

> 基于 `prd/tradingview/feat-tv-patterns/prd.md` · 2026-05-09
> Feature 职责：AI/规则引擎模式检测 — 5 种关键图表形态识别

---

## 关键调用链路

```
客户端请求模式检测 (detectPattern)
  └─→ POST /api/pattern/detect {symbol, pattern_types[]}
        ├─→ 数据收集: PriceFeed 历史数据 + 指标数据 (RSI/MACD 辅助判断)
        │     └─→ 数据点 ≥ 200? (约 3.3h @1min 粒度)
        │           ├─→ 否 → INSUFFICIENT_DATA (claude-next.md: 断言真实)
        │           └─→ 是 → 继续
        ├─→ 逐类型检测 (规则引擎几何匹配):
        │     ├─→ Head & Shoulders: 三峰识别, 左右峰高差 < 2%, 颈线突破
        │     ├─→ Double Top/Bottom: 双峰差值 < 1%, 间距 > 10 根 K 线
        │     ├─→ Triangle: 10 根 K 线连续振幅递减 (斜率收敛)
        │     ├─→ Wedge: 同向收敛 (5 根 K 线内)
        │     └─→ Flag: 剧烈单边后窄幅震荡 (量缩)
        ├─→ 置信度评分 (0-1):
        │     ├─→ ≥ 0.6 → 有效检测 (v1 硬阈值, v2 可配置)
        │     ├─→ 0.3-0.6 → 边缘检测 (记录但暂不触发)
        │     └─→ < 0.3 → 丢弃
        ├─→ 写入 PatternDetection 缓存 (Redis, TTL 30min 冷却)
        ├─→ 返回 {detected, pattern, confidence, description}
        └─→ 置信度标注: `[内部自检，非行业标准]` (R27 防伪诚信剧场)

批处理 (Bull 队列, 50K 告警):
  └─→ 定时任务 (每 5min) → 遍历活跃 symbol → 批量检测
        ├─→ symbol 已检测且在冷却期 (30min) → 跳过
        ├─→ 按 symbol 分组, 每批 ≤100, 10 并发 Worker
        └─→ 结果合并 → 更新 PatternDetection 缓存

检测冷却:
  ├─→ 命中后 30min 内不重复检测同一 symbol 同一形态
  └─→ Redis: pattern_cooldown:{symbol}:{type}, TTL 1800s
```

## 形态检测规则

| 形态 | 数据要求 | 几何规则 | 置信度因子 | v1 方法 |
|------|---------|---------|-----------|--------|
| Head & Shoulders | ≥200 点 | 3 峰, 中峰最高, 左右峰高差 < 2% | 对称度 + 颈线清晰度 | 规则引擎 |
| Double Top | ≥150 点 | 2 峰, 峰差 < 1%, 间距 ≥10K | 峰高度一致性 | 规则引擎 |
| Double Bottom | ≥150 点 | 2 谷, 谷差 < 1%, 间距 ≥10K | 谷深度一致性 | 规则引擎 |
| Triangle | ≥100 点 | 振幅连续递减 (10K 内斜率收敛) | 收敛角度 + K 线数 | 规则引擎 |
| Wedge | ≥80 点 | 同向收敛 (5K 内) | 收敛速度 | 规则引擎 |
| Flag | ≥50 点 | 剧烈单边后窄幅震荡 (量缩) | 量价配合度 | 规则引擎 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| API 速率 | 100 req/min (共享) | prd.md §非功能要求 |
| 批处理 | 50K 告警 | prd.md §非功能要求 |
| 降级 | 数据不足 → INSUFFICIENT_DATA | prd.md §非功能要求 |
| 冷却 | 命中后 30min 不重复检测 | prd.md §性能 |
| 置信度 | ≥0.6 有效, [内部自检] 标注 | claude-next.md §R27 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | AI/ML vs 规则引擎？ | v1 规则引擎 (几何形态分析), v2 ML 模型 |
| Q2 | 最小数据量？ | 200 个数据点 (约 3.3h @1min) |
| Q3 | 检测频率？ | symbol 活跃: 每 5min, 命中后冷却 30min |
| Q4 | 置信度阈值？ | v1 硬编码 0.6, v2 per-alert 可配置 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 假阳性过高 | 🟡 P1 | 规则引擎误判形态 | 置信度 ≥ 0.6, [内部自检] 标注 |
| 假阴性 | 🟢 P3 | 规则引擎遗漏真实形态 | v2 ML 模型升级 |
| 数据不足 | 🟢 P3 | 新 symbol 无足够历史 | INSUFFICIENT_DATA |
| 批处理延迟 | 🟡 P2 | 50K 告警批量检测慢 | 分页 + 并发 Worker |
| R27 违规 | 🟡 P1 | 置信度冒充行业标准 | 强制标注 [内部自检] |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | 检测规则基于技术分析文献, 不自创 |
| 断言真实 | 置信度评分必须标注 [内部自检，非行业标准] (R27) |
| 证据门禁 | "检测正确" 必须 VERIFIED: 与标注数据集对齐 |

### kernel.md §错误处理铁律
- Hook 不阻塞: 批处理 Worker 单个 symbol 失败 → 跳过, 不影响批次
- Error DNA: 检测异常分类记录至 error-dna.jsonl

### 反模式防范 (claude-next.md)
- R27: 置信度评分 `[内部自检，非行业标准]` — 强制标注, 不自颁诚信标签
- R24: 批处理脚本 `for x in $ACTIVE_SYMBOLS` → `set -f`

## 实现路径建议

1. **Phase 1**: 规则引擎几何形态检测 (5 种) + 数据量检查 ≥200 点
2. **Phase 2**: 置信度评分 (0-1, ≥0.6 有效) + [内部自检] 标注
3. **Phase 3**: 批处理 50K 告警 (Bull 队列, 10 并发 Worker) + 结果缓存
4. **Phase 4**: 检测冷却 30min (Redis TTL) + 触发避让
