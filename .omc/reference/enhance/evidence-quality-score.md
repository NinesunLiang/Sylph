# 证据质量评分 (C4)

> L2 Enhance Gate: completion-gate 结构化证据块校验
> 5 维度评分: file:line(35) + test/cmd(25) + multi-aspect(20) + quant(10) + struct(10)

---

## C4 硬化（v7.2+）— 证据质量评分 60→75 + 结构化字段 6/6 强制

### 变更摘要

| 项 | 旧值 | 新值 | 原因 |
|----|------|------|------|
| quality_threshold | 60 | 75 | 防低质量证据通过；对应 harness.yaml |
| 结构化字段满分条件 | ≥5/6 字段 | **6/6 字段必填** | 防 AI 省略字段后的伪验证 |
| 模板格式校验 | 无 | `VERIFIED: <action> → <result>` | 防"看起来没问题"等软完成语假冒验证 |
| 评分返回 | `(score, details)` | `(score, details, stats)` | C8 可维护性：BLOCKED 路径复用返回值，消除重复计算 |

### 评分维度

| 维度 | 权重 | 检测方式 |
|------|------|---------|
| file:line 引用 | 35 | `[\w./-]+\.[a-z]+:\d+` 正则，需 ≥3 处 |
| test/cmd 标记 | 25 | exit.code/PASS/FAIL/VERIFIED/build 等，需 ≥4 种 |
| 多角度验证 | 20 | 百分比/ms/coverage/edge.case 等，需 ≥3 种 |
| 量化数据 | 10 | 计数/比率/PASS×FAIL 等，需 ≥2 种 |
| **结构化证据块** | **10** | 6 字段检测: action/file/command/output/status + 块标题 |

### 结构化字段清单

证据块必须包含**全部 6 字段**才可拿满 10 分：

| # | 字段名 | 正则匹配 | 变量名 |
|---|--------|---------|--------|
| 1 | 块标题 | `\*\*证据块\|证据块：\|evidence.block\|##+\s*EV-\|###\s*EV-` | 证据块标题 |
| 2 | action | `(?m)^\s*[-*+]\s*\`?action\`?\s*:` | action |
| 3 | file | `(?m)^\s*[-*+]\s*\`?file\`?\s*:` | file |
| 4 | command | `(?m)^\s*[-*+]\s*\`?command\`?\s*:` | command |
| 5 | output | `(?m)^\s*[-*+]\s*\`?output\`?\s*:` | output |
| 6 | status | `(?m)^\s*[-*+]\s*\`?status\`?\s*:` | status |

每一字段的命中/未命中记录在 `struct_bits` 字典中，供 BLOCKED 输出指导改进方向。

### VERIFIED 模板格式校验

证据中必须包含如下格式的有效验证断言（自 v7.2 C4 硬化新增）：

```
VERIFIED: <action> → <result>
VERIFIED: <action> -> <result>
```

如果未命中此模板，**在结构化评分基础上扣 3 分**（min=0）。这是防 AI 写出"看起来没问题"类伪验证的核心防线之一。

### 阈值

| 条件 | 裁决 |
|------|------|
| total ≥ 75 | 通过 |
| total < 75 | BLOCKED，输出各维度分解和字段命中表 |

### 评分函数签名

```python
def _evidence_quality_score(content: str) -> tuple[int, list[str], dict]:
    """返回 (score, details_list, stats_dict)"""
    # stats_dict 含:
    #   fl_count, fl_score — file:line 统计
    #   cmd_hits, cmd_score — 测试标记
    #   multi_hits, multi_score — 多角度
    #   quant_hits, quant_score — 量化数据
    #   struct_fields, struct_score — 结构化字段
    #   struct_bits — 6 字段的逐项命中/未命中
```

### 集成点

- `.claude/harness.yaml` — `completion_gate.quality_threshold: 75`
- `.claude/hooks/completion-gate.py` — `_evidence_quality_score()` 函数
- `main()` 中 E3 增强段调用
- 返回的 `stats_dict` 复用至 BLOCKED 输出路径，消除重复计算
