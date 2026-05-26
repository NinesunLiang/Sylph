# hard-boundary-check — 硬边界检查

> 审判节点。检查操作是否触碰硬边界（物理禁区）。引用 `@../../references/oma/decision-chain.md`。

## 输入

```yaml
operation:
  command: string         # 待执行的命令
  target: string          # 目标文件/路径
  reason: string          # 执行原因
```

## 流程

1. 匹配硬边界规则：
   - 破坏性文件操作（rm/dd/mkfs）
   - Git 写操作（commit/push/rebase/reset --hard）
   - 敏感文件（.env/.pem/.key/token/credentials）
   - API Key 明文
2. 命中 → 立即阻断，不裁决
3. 未命中 → 放行

## 输出

```yaml
verdict: blocked | pass
boundary_hit: string | null   # 命中的边界规则
protocol: skip | report       # 阻断 → skip+report
```

## 边界

| 不做 | 原因 |
|------|------|
| 尝试绕过或 workaround | 硬边界 = 物理禁区 |
| 裁决后放行 | 不可裁决，不可绕过 |
