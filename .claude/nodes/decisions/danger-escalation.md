# danger-escalation — 三级危险裁决

> 决策节点。遇到危险操作时按三级链条裁决。引用 `@../../references/oma/decision-chain.md`。

## 输入

```yaml
operation: string       # 待执行的危险操作
risk_level: low | medium | high | critical
context: string         # 为什么需要执行
```

## 流程

1. 判定 risk_level
2. low/medium → L1: AGENTS.md 裁决（Philosophy → Iron Rules → Practices）
3. high → L2: Oracle 独立审核
4. critical → L3: 人类裁决
5. 硬边界操作 → 立即跳过，不裁决

## 输出

```yaml
level: L1 | L2 | L3 | HardBoundary
verdict: approved | rejected | skipped
authority: AGENTS | Oracle | Human | Blocked
reason: string
```

## 边界

| 不做 | 原因 |
|------|------|
| 硬边界操作走裁决链 | 硬边界 = 物理禁区，直接跳过 |
| L3 自行裁决 | 必须人类介入 |
