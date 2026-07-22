---
name: lx-pre-push
version: v2.1.0
description: "推送前安全检查 — commit规范校验 + 安全扫描 + 变更审计。纯指令调用，不接入治理管线。每次push前执行。"
when_to_use: "Use before git push. Pure command trigger. One check per push."
argument-hint: "[--prod-commit <hash>]"
harness_version: ">=6.3.0"
status: stable
role: "Pre-push security gate — commit convention, security scan, change audit. Command-only."
execution_mode: stepwise
triggers:
  - "/lx-pre-push"
---
# lx-pre-push — 推送前安全检查

> 纯指令调用，不接入治理管线。每次 push 前执行一次重度检查。

## 流程

### Gate 0 — Commit Message 规范校验
- 检查待推送 commits 的 message 格式
- 不规范 → 提示修复

### Gate 1 — 安全扫描
- 按项目类型执行：
  - Go: `go vet ./...`
  - Node: `npm audit --production`
  - Python: `pip-audit` 或依赖检查
- 🔴 问题必须修复才能推送
- 🟡 记录不阻塞

### Gate 2 — 变更审计
- 检查是否有敏感文件（.env / 密钥 / token）被误提交
- 检查是否有大型二进制文件
- 检查是否有调试代码遗留

### 最终判定
```
📋 lx-pre-push 推送门禁结果
Gate 0 Commit格式:  ✅ {N} commits 全部通过
Gate 1 安全扫描:    🔴=0 🟡={N}
Gate 2 变更审计:    ✅ 无敏感文件
判定: [✅ 允许推送 / ❌ 阻塞推送]
```

## 降级

| 场景 | 降级 |
|------|------|
| 安全扫描不可用 | 跳过，标注"[已跳过]" |
| prod-commit 无效 | 提示用户重新提供 |
| 命令超时(>120s) | 超时后建议手动检查 |
