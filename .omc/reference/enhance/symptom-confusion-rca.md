# 症状混淆防线 (E5)

> L2 Enhance Gate: completion-gate 根因分析门禁 + error-dna 错误去重
> 防AI治标不治本（仅处理症状，未消除根因）

## 触发条件

| 条件 | 阈值 | 行为 |
|------|------|------|
| RCA 结构字段不足 | <2/5 字段 | BLOCKED |
| RCA 模板化（占位符） | ≥1 处 | BLOCKED |
| RCA 深度评分不足 | <4 分 | BLOCKED |
| 同错误签名跨步重复 | ≥3 个不同步骤 | BLOCKED |
| error-dna 同模式重复 | 同 step 重试 ≥3 次 | BLOCKED |

## E5 硬化（v7.2+）

### 变更摘要

| 项 | 旧行为 | 新行为 |
|----|--------|--------|
| RCA 字段检测 | 仅检查存在性（结构化字段 ≥2/5） | **深度评分** (rca_depth_score ≥4) |
| 深度维度 | 无 | file:line(+2) + 量化数据(+2) + 验证命令(+1) + 复现证据(+1) |
| 跨步去重 | 无 | 检测 error-dna 中同签名 ≥3 步骤重复 |
| error-dna 工具函数 | 仅 retry-gate | + `collect_gate_blocks()` + `find_error_dedup()` |

### RCA 深度评分

```python
rca_depth_score = 0
# file:line 代码引用（RCA 落地到具体代码位置）
if content 含 [a-zA-Z0-9_./-]+\.[a-z]+:\d+ → +2
# 量化验证数据
if content 含 计数/比率/通过数 → +2
# 验证性命令输出
if content 含 verified...exit/PASS/通过 → +1
# 复现证据（test-first）
if content 含 FAIL/exit非零/Traceback + 复现字段 → +1

# 通过条件: rca_depth_score >= 4
```

### 跨步错误去重

```python
# 读取 .omc/state/error-dna.jsonl
# 按 error[:40] 签名聚类
# 同一签名出现在 ≥3 个不同 step → BLOCK
# 输出: 重复步骤列表 + 要求全局根因分析
```

### 错误分析工具函数

新增在 `error_dna.py` 中的工具函数：

| 函数 | 用途 |
|------|------|
| `collect_gate_blocks(project_root, n=50)` | 从 audit 收集最近 BLOCK 事件 |
| `find_error_dedup(project_root, n=30, min=2)` | 聚类分析重复错误模式 |

## 集成点

- `.claude/hooks/completion-gate.py` — E5 根因分析门禁段
- `.claude/scripts/lib/error_dna.py` — `collect_gate_blocks()` / `find_error_dedup()`
- `.omc/state/error-dna.jsonl` — 错误 DNA 记录
- `.omc/audit/` — gate BLOCK 事件源

## 配置

深度评分阈值 4 硬编码。跨步检出阈值 3 步骤硬编码。
