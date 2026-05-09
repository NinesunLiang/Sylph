# Research: Advanced Evaluation

> 基于 `prd/alert-engine/feat-advanced-evaluation/prd.md` · 2026-05-09
> Feature 职责：技术指标 + AI 模式告警评估（Premium 专属）

---

## 关键调用链路

```
入站事件: IndicatorUpdate (symbol, indicator, value, confidence, timestamp) from TradingView
  └─→ evaluateIndicator(alert_id, indicator_values)
        ├─→ Redis 检查: tier:{user_id} == premium (服务端强制门禁, 引用 AGENTS.md §难度分级)
        │     ├─→ 非 Premium → TIER_RESTRICTED
        │     └─→ Premium → 继续
        ├─→ 按指标类型路由 (指标路由表)
        │     ├─→ RSI(14): 计算 value < 30 → oversold; > 70 → overbought
        │     ├─→ MACD(12/26/9): 信号线 (EMA_12 - EMA_26) 与 signal EMA_9 交叉
        │     ├─→ SMA/EMA(20/50/200): 当前价格穿越均线
        │     ├─→ BB(20,2σ): 价格超出 (SMA±2σ) 通道
        │     ├─→ STOCH(14/3/3): %K 穿越 %D
        │     ├─→ ATR(14): 波幅突破 N 倍 ATR
        │     ├─→ ICHI(9/26/52): 价格穿越云层
        │     ├─→ VPROF: 成交量 > μ+2σ
        │     └─→ FIBO(0.236-0.786): 价格穿越关键回调位
        ├─→ 组合条件评估 (AND/OR combinator)
        │     ├─→ v1: 单层 AND (全满足) 或 OR (任一满足)
        │     └─→ v2: 任意括号嵌套 (A AND (B OR C))
        ├─→ triggered → 发布 AlertConditionMet 事件
        └─→ 返回 {triggered: boolean, value, interpretation}

detectPattern(symbol, pattern_types[])
  └─→ 获取历史 K 线数据 (≥200 根, TradingView API)
        └─→ 规则引擎几何匹配:
              ├─→ Head & Shoulders: 三峰对称度 (左右峰差 < 2%) + 颈线突破
              ├─→ Double Top/Bottom: 双峰差值 < 1%, 间距 > 10 根 K 线
              ├─→ Triangle: 斜率收敛 (10 根 K 线连续振幅递减)
              ├─→ Wedge: 同向收敛 (5 根 K 线内)
              └─→ Flag: 剧烈单边后窄幅震荡 (量缩)
              └─→ 置信度评分: 0.0-1.0, ≥0.5 才触发

指标缓存策略:
  ├─→ IndicatorCache: symbol+indicator 维度
  ├──→ RSI/MACD/SMA: TTL 30s (高频)
  ├─→ BB/STOCH/ATR: TTL 60s (中频)
  ├─→ ICHI/VPROF/FIBO: TTL 300s (低频)
  └─→ 缓存更新模式: IndicatorUpdate 事件驱动刷新 + TTL 兜底 (三层缓存架构)

教育上下文生成 (v1):
  ├─→ 模板映射: {indicator_type, interpretation} → 预定义文字
  ├─→ RSI > 70: "RSI 进入超买区 (>{threshold})，可能面临回调压力"
  ├─→ MACD 金叉: "MACD 信号线向上穿越，短期动能偏多"
  └─→ v2: 动态模板 (含当前数值)
```

## 指标路由表

| 指标 | 周期参数 | 触发条件 | 置信度 | 缓存 TTL |
|------|---------|---------|--------|---------|
| RSI | 14 | >70 超买 / <30 超卖 | 偏离度 = \|value-50\|/50 | 30s |
| MACD | 12/26/9 | 信号线交叉 (金叉/死叉) | 交叉角度 (用 atan2) | 30s |
| SMA/EMA | 20/50/200 | 价格穿越均线 | 穿越深度 = \|price-MA\|/MA | 30s |
| BB | 20, 2σ | 价格出上下轨 | 通道外距离 = \|price-轨道\|/σ | 60s |
| STOCH | 14/3/3 | %K 穿越 %D | 交叉强度 | 60s |
| ATR | 14 | 波幅突破 N×ATR | 倍数 = 波幅/ATR | 60s |
| ICHI | 9/26/52 | 云层穿越 (领先线A/B) | 穿越深度 | 300s |
| VPROF | — | 成交量 > μ+2σ | 标准差倍数 | 300s |
| FIBO | 0.236-0.786 | 价格穿越关键回调位 | 精确度到 0.1% | 300s |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 评估延迟 | 条件满足后 < 30 秒 | prd.md §非功能要求 |
| 技术栈 | TradingView API + 规则引擎 (v1 非 ML) | prd.md §技术约束 |
| 用户限制 | 仅 Premium | prd.md §功能边界 |
| 模式检测 | 最少 200 根 K 线 | prd.md |
| 组合条件 | v1 单层 AND/OR, v2 任意嵌套 | prd.md |
| 缓存 TTL | 按指标类型 30s~300s | prd.md §性能 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 组合条件嵌套深度？ | v1 单层 AND/OR, v2 任意括号嵌套 |
| Q2 | 教育上下文来源？ | 静态模板映射表, 按 indicator_type + interpretation 匹配 |
| Q3 | 模式检测最低 K 线数？ | 200 根 (统一阈值) |
| Q4 | 多指标同时触发 → 去重？ | 同一 alert 多个指标同时触发 → 合并为单条 AlertConditionMet |
| Q5 | 置信度阈值可配置？ | v1 硬编码 0.5, v2 per-alert 配置 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 假阳性过高 | 🟡 P1 | 规则引擎误判形态 | 置信度 ≥ 0.5, 报告标注 confidence |
| Premium 门禁绕过 | 🔴 P0 | Free 用户调指标接口 | 服务端 tier 校验 (Redis + 回源) |
| 数据不足 | 🟡 P2 | 新 symbol 历史数据不足 | 返回 INSUFFICIENT_DATA |
| 组合逻辑歧义 | 🟡 P2 | AND/OR 优先级 | 括号强制分组 + 验证 |
| 缓存 TTL 抖动 | 🟢 P3 | 高频指标缓存 miss | IndicatorUpdate 事件驱动刷新 |
| 模式检测 CPU 高 | 🟡 P2 | 全量扫描 5 种形态 | 异步 Worker, 不阻塞指标评估 |

## 项目特定引用

### AGENTS.md §三重门 映射
- Tier 门禁: 每次 evaluateIndicator 前检查 tier:{user_id} cache (服务端强制)
- 修复上限 3 轮: 指标评估连续 3 次测试失败 → BLOCKED
- A→B→A: 模式检测置信度阈值决策需三重门验证 (L4)

### kernel.md §错误处理铁律
- 组合评估器 panic → catch → 返回 PARTIAL_EVALUATION + 审计日志
- Error DNA: 各指标评估异常分类记录

### 反模式防范 (claude-next.md §R27)
- R27: 置信度评分报告不能自称"行业标准", 标注 `[内部自检，非行业标准]`
- R24: Bash 助手脚本避免 unquoted glob

## 实现路径建议

1. **Phase 1**: 指标评估引擎 + IndicatorUpdate 消费 (前 4 指标: RSI, MACD, SMA, EMA + 缓存 30s)
2. **Phase 2**: 扩展至全 10 指标 + 各指标 TTL 缓存策略
3. **Phase 3**: AND/OR 组合条件 (v1 单层)
4. **Phase 4**: 模式检测 (5 种几何匹配 + 置信度评分 ≥0.5)
5. **Phase 5**: 教育上下文生成 (模板映射) + 多指标去重合并
