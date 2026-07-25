# AI Agent 数据收集质量提升方案 — 业界借鉴报告

> 创建：2026-07-25 | 用途：为 CarrorOS error-dna / edit-churn / telemetry 管线提供改进方向
> 调查范围：OpenLLMetry (Traceloop)、Arize Phoenix、Langfuse、Sentry、LangSmith

---

## 1. 核心发现：业界数据质量结构

### 1.1 OpenTelemetry LLM Semantic Conventions (OpenLLMetry)

**关键设计**：OpenTelemetry 的 LLM 语义约定（已正式合并）

```
Span Attributes (标准化的 key-value 结构):
  - gen_ai.request.model          → 模型
  - gen_ai.response.id            → 响应标识
  - gen_ai.usage.completion_tokens → token 计数
  - gen_ai.usage.prompt_tokens    → token 计数
  - gen_ai.system                 → 系统架构
```

**启示**：标准化 schema 比自由格式 JSON 更利于质量——error-dna.jsonl 的字段应当有固定 schema + 强类型校验。

### 1.2 Arize Phoenix — Trace + Eval + Dataset 三层

Phoenix 的核心模式是三层分离：

| 层 | 做什么 | CarrorOS 当前 |
|---|---|---|
| **Tracing** | 记录每次调用的完整链路（span tree+metadata） | ✅ 单层 error-dna |
| **Evaluation** | 用 LLM as judge 评估输出质量、文档检索质量 | ❌ 没有 |
| **Datasets** | 版本化数据集，支持回归/实验对比 | ❌ 没有 |

**可借鉴的 Phoenix 设计**：
- `px setup` 自动发现框架并注入 instrumentation  
- 每个 span 带 `status_code` (`OK|ERROR|UNSET`)  
- 不同事件类型有独立的 schema（LLM / Retriever / Agent / Tool）

### 1.3 Langfuse — Score 层的质量信号

Langfuse 在 trace 之上加了一层 **score**：
- 每个 trace/span/generation 都可以挂 score  
- Built-in score types: numeric (0-1), categorical, boolean  
- Evaluation runs 产生 scores 反馈到 trace

**关键**：score 是独立于 tracing 的质量面——数据收集的质量不应该只看"录了多少"，还要看"录得对不对"。

### 1.4 Sentry — Error Fingerprinting 精确去重

Sentry 的 fingerprint 系统是 error-dna 的直接对标：

```
fingerprint: ["myrpc", "POST", "/foo.bar"]
```

规则：
- fingerprint = 自定义分组键（可多个维度组合）  
- `{{ default }}` 占位符 = 保留默认分组再加入一个维度  
- 允许 SDK 端覆盖 + 服务端调整

**对比 error-dna 当前设计**：

| 维度 | Sentry | error-dna 当前 |
|---|---|---|
| 分组键 | 显式 fingerprint 数组 | 单字段 signature (MD5) |
| 默认值 | `{{ default }}` + 自定义组合 | 无默认模板 |
| 用户控制 | SDK set_fingerprint + InApp 规则 | 无（纯自动） |
| 去重粒度 | 可控 | MD5 碰撞风险 |

### 1.5 业界通用质量金字塔

```
          ┌──────────┐
          │  Score   │  ← 质量评价（LLM-as-judge / 人工）
         ┌┴──────────┴┐
         │  Dataset   │  ← 版本化集合（可回放、可对比）
        ┌┴────────────┴┐
        │  Trace/Span │  ← 链路追踪（上下文完整）
       ┌┴──────────────┴┐
       │   Event Log   │  ← 原始日志（error-dna / edit-churn）
       └───────────────┘
```

CarrorOS 当前全部在 Event Log 层，缺少上方三层。

---

## 2. 针对 CarrorOS 的具体改进建议

### 2.1 error-dna.jsonl — 引入结构化 Schema (P0)

**当前问题**：free-form JSON，无 schema 校验，字段可选

**借鉴 OpenTelemetry + Sentry**：

```json
{
  "ts": <int>,                 // 必须
  "signature": "<str>",        // 必须——指纹键
  "fingerprint": ["<str>"],    // 新增——显式分组（取代 signature 去重逻辑）
  "level": "error|warn|info",  // 新增——严重级别
  "span_id": "<str>",          // 新增——关联到 span tree
  "trace_id": "<str>",         // 新增——关联到 trace tree
  "cmd_type": "<str>",         // 新增——命令类型分类
  "cmd": "<str>",
  "exit_code": <int>,
  "error_type": "<str>",
  "message": "<str>",
  "stderr_snippet": "<str>",   // 新增——标准化截取长度
  "flow": "<str>",             // 新增——所属流程(build/test/git/...)
  "step": "<str>",
  "retry_count": <int>,
  "resolution": "auto|human|pending"  // 新增——解决状态
}
```

**核心改动**：
1. 引入 `fingerprint` 数组替代单字段 `signature`——允许多维度分组
2. 引入 `level` 区分 error/warn/info——当前所有记录都是 error 级别
3. 引入 `span_id`/`trace_id`——为将来的 span tree 预留
4. 引入 `resolution`——记录策略信号

### 2.2 引入 LLM-as-Judge 评分层 (P1)

**借鉴 Langfuse score / Arize evaluation**：

对每个重要的数据收集点，在 flywheel 回调中用轻量级 prompt 评估数据质量：

```python
# 示例：error-dna 记录的质量评分
def score_error_record(record: dict) -> dict:
    """对 error-dna 记录打分"""
    # 评估标准：
    # 1. message 信息量是否足够（>20字符且有具体内容）
    # 2. error_type 分类是否准确
    # 3. stderr_snippet 是否包含根本原因
    score = 0
    issues = []
    if len(record.get("message", "")) < 20:
        score -= 1
        issues.append("message_too_short")
    if record.get("error_type") in ("runtime", "unknown"):
        score -= 1
        issues.append("type_too_generic")
    if record.get("stderr_snippet", ""):
        score += 1
    return {"score": max(0, score), "issues": issues}
```

**注**：不调 LLM 评分浪费 token，这里用规则评分就够——关键是明确评分维度。

### 2.3 edit-churn-log 加入编辑模式分类 (P1)

**当前问题**：edit-churn-log 只有 sig hash，不知道编辑类型

**借鉴 Arize Phoenix span type 分类**：

```json
{
  "ts": <int>,
  "file_path": "<str>",
  "tool_name": "Edit|Write",
  "edit_mode": "insert|replace|refactor|revert",  // 新增
  "edit_scope": "small|medium|large",              // 新增（按字符数）
  "sig": "<hash>",
  "is_revert": <bool>,
  "edit_count": <int>,
  "content_hash": "<str>",
  "patience_score": <float>                        // 新增——多次编辑同一文件的收敛速度
}
```

**核心改动**：
1. `edit_mode` — 区分增改回退——当前只检测 revert_of
2. `edit_scope` — 按编辑量分档——小型编辑 vs 大规模重写
3. `patience_score` — 收敛指标（编辑次数 / 唯一内容hash数）— 越低越好

### 2.4 添加数据质量守护进程 (P1)

**借鉴 OpenTelemetry 的 batch processor + sampling**：

```python
# 每小时运行一次的数据质量检查器
def data_quality_check():
    """检查 error-dna.jsonl + edit-churn-log.jsonl 的数据质量"""
    report = {"total": 0, "issues": []}
    
    for path in [ERROR_DNA_PATH, EDIT_CHURN_PATH]:
        if not path.exists():
            report["issues"].append(f"{path.name}: MISSING")
            continue
        report["total"] += 1
        
        with open(path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        
        # 1. 重复检测
        sigs = [l.get("signature", l.get("sig", "")) for l in lines]
        dup_count = len(sigs) - len(set(sigs))
        if dup_count > 0:
            report["issues"].append(f"{path.name}: {dup_count} dups")
        
        # 2. 空字段检测
        for field in REQUIRED_FIELDS.get(path.name, []):
            empty = [l for l in lines if not l.get(field)]
            if empty:
                report["issues"].append(f"{path.name}: {len(empty)} rows missing '{field}'")
        
        # 3. 异常值检测
        min_ts = int(time.time()) - 86400
        stale = [l for l in lines if l.get("ts", 0) < min_ts]
        if stale:
            report["issues"].append(f"{path.name}: {len(stale)} stale rows")
    
    return report
```

### 2.5 数据管线分层架构 (P2)

借鉴 OpenTelemetry 的 processor chain + Langfuse 的 hierarchy：

```
原始事件流 (pretool/posttool hooks)
    │
    ├──→ Enricher（补充上下文：flow/step/session_id/span_id）
    │
    ├──→ Classifier（error_type / edit_mode 分类）
    │
    ├──→ Deduplicator（fingerprint 去重，合并 retry_count）
    │
    ├──→ Sampler（高频事件降采样，>5/min 以 rate 记录）
    │
    └──→ Writer（写入 jsonl + 触发 flywheel）
```

当前的写法是 classifer + writer 写在一起，缺少 enricher 和 sampler。

### 2.6 数据质量仪表指标 (P2)

借鉴 Datadog/Arize 仪表盘：

| 指标 | 来源 | 意义 |
|---|---|---|
| `error_dna.capture_rate` | error-dna.jsonl / total-ops | 错误捕获率 |
| `error_dna.unique_types` | error_type 去重 | 错误多样性 |
| `error_dna.signature_retry` | retry_budget retry_count | 相同错误重试 |
| `error_dna.avg_message_length` | message 字段 | 信息量 |
| `edit_churn.patience_avg` | patience_score 均值 | 编辑收敛速度 |
| `edit_churn.revert_rate` | is_revert 比例 | 编辑稳定性 |

---

## 3. 优先级线路图

```
P0 （立即实施）:
  ┌ error-dna: 引入 fingerprint + level 字段
  └ 数据质量守护进程

P1 （本轮 sprint）:
  ├ error-dna: 引入 resolution + span_id 预留字段
  ├ edit-churn: 加入 edit_mode + patience_score
  └ 规则评分（不调 LLM）

P2 （后续迭代）:
  ├ 引入 sampler 减少高频噪音
  ├ enricher 加入外部上下文
  └ 仪表指标输出到 flywheel

P3 （远期）:
  ├ LLM-as-Judge 深度评估
  ├ Dataset 版本化
  └ Trace/Span tree 完整链路
```

---

## 4. 参考项目

| 项目 | 地址 | 可借鉴 |
|---|---|---|
| OpenLLMetry | github.com/traceloop/openllmetry | OTEL semantic conventions, auto-instrumentation |
| Arize Phoenix | github.com/Arize-AI/phoenix | Trace+Eval+Dataset 三层, status_code, span types |
| Langfuse | langfuse.com/docs | Score 层独立于 trace, observation hierarchy |
| Sentry | develops.sentry.dev | Fingerprint 精确去重, 可覆盖分组 |
| LangSmith | docs.smith.langchain.com | Dataset/experiment 对比, feedback 机制 |
