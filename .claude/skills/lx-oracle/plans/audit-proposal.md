# lx-oracle 审计方案

## 问题一：迁移路径断裂

`oracle_spawn.py`(L2) 和 `static_oracle_agent.py`(L2) 均标记 DEPRECATED：
```
# DEPRECATED - 保留向后兼容，建议迁移到 oracle_agent.py (--mode duo)
```

但 `oracle_agent.py` **不存在于** `.claude/scripts/` 中。

影响：
1. `oracle_spawn.py` (116行) 调度 static + runtime → 调 meta_oracle.py aggregate
2. `static_oracle_agent.py` (231行) 做静态分析，也标记 DEPRECATED
3. 无 `oracle_agent.py` 意味着 duo 模式无法正常工作
4. SKILL.md 中 trio 入口全部引用了这四个脚本

## 问题二：整体质量评估

待三模型给出材料要求后分析。

## 调查清单

1. 确认 oracle_agent.py 是否存在于其他路径
2. 检测所有 DEPRECATED 标记的引用链
3. 检查三个 body 文件（static/runtime/duo）与实际脚本的匹配度
4. 检查 meta_oracle.py 完整性
