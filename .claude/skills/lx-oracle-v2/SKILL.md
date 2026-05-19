---
name: lx-oracle-v2
version: v2.0.0
description: "Oracle Agent v2 — 物理隔离独立审核。一般情况用旧 lx-oracle，复杂/重要才 spawn v2。"
when_to_use: |
  成本优先路由:
  - 日常审查/小变更/方向确认 → 旧 lx-oracle (零成本)
  - 架构决策/安全敏感/PRD终审/Release → lx-oracle-v2 (~70-110K tokens, 物理隔离)
argument-hint: "<审核对象路径> [--mode d|v]"
harness_version: ">=1.1.0"
status: beta
role: "Independent Oracle Auditor — 物理隔离，按需 spawn"
execution_mode: stepwise
triggers:
  - "/lx-oracle-v2"
  - "oracle review"
  - "Oracle 审核"
---

# lx-oracle-v2 — 物理隔离 Oracle（按需 spawn）

## 路由决策（先看这里）

> **默认旧 lx-oracle**。只有以下场景才 spawn v2（~70-110K tokens/次）:

| spawn v2 | 用旧 lx-oracle |
|----------|---------------|
| 架构决策（跨 ≥2 子系统） | 日常代码审查 |
| PRD/方案终审 | 单文件修改 |
| 安全敏感（rm -rf / force push） | 方向确认 |
| Release 门禁 | 轻量决策链 Level 2 |
| — | 不确定时→默认旧版 |

## 执行（3 步）

```
1. prepare:  bash .claude/skills/lx-oracle-v2/scripts/oracle-spawn.sh prepare --mode d|v --target <path>
2. spawn:    Agent(subagent_type="critic", prompt=<oracle-request.json + oracle-protocol.md>)
3. record:   bash .claude/skills/lx-oracle-v2/scripts/oracle-spawn.sh record --mode d|v --verdict-file <path> --target <path>
```

**协议详情**: spawn 时注入 `references/oracle-protocol.md`（Oracle-D 决策链 / Oracle-V A→B→A 双协议 + 故障恢复）。

## 裁决

| 裁决 | 行动 |
|------|------|
| approved / PASS | 继续 |
| rejected / FAIL | 阻断 |
| escalated / INCONCLUSIVE | 升级 Meta-Oracle |
| needs_clarification | 提问澄清（最多 2 轮） |

> 审核原则、YAML 输出格式、超时降级、故障恢复 → `references/oracle-protocol.md`
