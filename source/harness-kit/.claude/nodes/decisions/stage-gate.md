# stage-gate — 阶段门禁裁决

> 决策节点。检查当前阶段完成标准是否满足，决定推进/回退/阻塞。

## 输入

```yaml
stage: string          # 当前阶段名
completion_criteria:   # 完成标准列表
  - check: string      # 检查项描述
    result: pass|fail
evidence: string       # 证据摘要
```

## 流程

1. 逐条检查 completion_criteria
2. 全部 pass → ACCEPT，推进到下一阶段
3. 部分 fail → REVISE，列出未通过项和修复建议
4. 全部 fail → REJECT，回退到上一阶段

## 输出

```yaml
verdict: ACCEPT | REVISE | REJECT
reasons: [string]     # 裁决理由
pending: [string]     # 待修复项（REVISE 时）
next_stage: string    # 下一阶段（ACCEPT 时）
```

## 边界

| 不做 | 原因 |
|------|------|
| 自动修复失败项 | 那是调用方 skill 的职责 |
| 跳过未通过项 | 硬门禁，不可绕过 |
