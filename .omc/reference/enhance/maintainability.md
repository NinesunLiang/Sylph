# 可维护性增强 (C8)

> 跨维度 Code Quality: 类型标注 + 常量提取 + 代码去重
> 不改变行为，仅提升可读性和维护效率

## C8 硬化（v7.2+）

### 变更摘要

| 文件 | 改动 |
|------|------|
| `completion-gate.py` | 全量参数提取为模块级常量 `_DEFAULT_*` |
| `completion-gate.py` | 证据质量评分返回 `stats_dict`，代替 BLOCKED 路径中的重复计算（-40 行） |
| `completion-gate.py` | 内联字典 `{2: "降级模式", 3: "紧急模式"}` 提取为 `_FALLBACK_LEVELS_MAP` |
| `pretool-gate.py` | 全 gate 函数补 `-> str \| None` 返回类型注解 |
| `error_dna.py` | 新增 `from __future__ import annotations` |

### 模块级常量清单

```python
_DEFAULT_SOFT_COMPLETION_WORDS   # 软完成语列表（正则 UNION）
_DEFAULT_QUALITY_THRESHOLD       # 证据质量阈值 (75)
_DEFAULT_MIN_EVIDENCE_CHARS      # 最小证据字符 (20)
_DEFAULT_FRESHNESS_SEC           # 证据新鲜度 (300)
_DEFAULT_REQUIRED_KEYWORD        # 必有关键词 (VERIFIED)
_DEFAULT_EVIDENCE_DIR            # 证据目录 (.omc/state)
_FALLBACK_LEVELS_MAP             # 降级等级标签映射
```

### 去重收益

证据质量评估的 BLOCKED 输出路径原来对同一份 content 做完全相同的正则扫描和评分计算。使用 `stats_dict` 复用后：

- 消除冗余正则匹配约 10 次/blocked 事件
- 减少约 40 行重复代码（从 `fl = len(re.findall(...))` 到 `fl = quality_stats["fl_count"]`）

## 集成点

- `.claude/hooks/completion-gate.py` — 常量区 + `_evidence_quality_score()` 返回结构
- `.claude/hooks/pretool-gate.py` — 全函数类型标注
- `.claude/scripts/lib/error_dna.py` — annotations 导入
