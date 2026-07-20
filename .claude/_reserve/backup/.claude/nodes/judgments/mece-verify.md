# mece-verify — MECE 正交校验

> 审判节点。检查功能域拆解是否满足 MECE（Mutually Exclusive, Collectively Exhaustive）原则。

## 输入

```yaml
domains:
  - name: string
    responsibilities: [string]
    entities: [string]
parent_requirements: [string]  # 父需求全量列表
```

## 流程

1. **正交性**: 逐对检查域间职责重叠
2. **完整性**: 父需求 × 域覆盖矩阵，无遗漏
3. **实体唯一归属**: 确认每个实体只属于一个域
4. **接口解耦**: 域间接口数检查

## 输出

```yaml
verdict: pass | fail
orthogonal_pairs:       # 正交性矩阵
  - domain_a: string
    domain_b: string
    overlap: string | null   # 重叠点（null = 正交）
coverage:
  total: int
  covered: int
  missing: [string]     # 未覆盖的父需求
entity_conflicts: [string]   # 多域声明的实体
score: 0-100
```

## 边界

| 不做 | 原因 |
|------|------|
| 自动修复非正交 | 需要重新设计域边界 |
| 跳过失败项 | MECE 是硬门禁 |
