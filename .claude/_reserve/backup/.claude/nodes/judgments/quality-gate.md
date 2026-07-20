# quality-gate — 质量门禁

> 审判节点。任务/特性完成后的自检清单，决定是否交付。

## 输入

```yaml
artifact: string        # 产出物路径/描述
checks:
  completeness: pass|fail   # 完整性
  correctness: pass|fail    # 正确性
  consistency: pass|fail    # 一致性
  evidence: pass|fail       # 证据充分性
```

## 流程

1. 逐项检查四维质量
2. 全部 pass → ACCEPT，可交付
3. 1-2 fail → REVISE，列出修复建议
4. 3+ fail → REJECT，退回重做

## 输出

```yaml
verdict: ACCEPT | REVISE | REJECT
checks:
  completeness: {result, detail}
  correctness: {result, detail}
  consistency: {result, detail}
  evidence: {result, detail}
score: 0-100
issues: [string]         # 待修复项
```

## 边界

| 不做 | 原因 |
|------|------|
| 自动修复质量问题 | 需要理解语义，非机械操作 |
| <65分 放行 | 低于阈值强制 REJECT |
