# conflict-resolution — 冲突分级裁决

> 决策节点。遇到冲突时按 L1/L2/L3 分级裁决。

## 输入

```yaml
conflict:
  id: string
  type: L1_resolvable | L2_ambiguous | L3_core_conflict
  parties: [string]     # 冲突双方
  context: string       # 冲突背景
```

## 流程

1. 判定冲突级别
   - L1: 数据/格式不一致，有明确权威源 → 自动裁决
   - L2: 语义分歧，无单一权威源 → Oracle 审核
   - L3: 核心需求/架构冲突 → 升级人类裁决
2. 按级别执行裁决协议
3. 记录裁决留痕

## 输出

```yaml
level: L1 | L2 | L3
verdict:
  resolution: string    # 裁决结果
  authority: AGENTS | Oracle | Human
  reason: string
```

## 边界

| 不做 | 原因 |
|------|------|
| L3 冲突自行裁决 | 必须人类介入 |
| 跳过裁决直接执行 | 违反铁律 #6（0信任） |
