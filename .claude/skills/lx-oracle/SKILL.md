---
name: lx-oracle
description: Oracle quality gate system — static analysis (Oracle-D), runtime verification (Oracle-V), dual-agent review (Duo)
version: v2.0.0
harness_version: ">=6.3.0"
status: stable
argument-hint: >
  static <task-id> [--plan <path>] [--executor <path>] |
  runtime <task-id> [--token <path>] [--executor <path>] [--audit-dir <path>] |
  duo <task-id> [--plan <path>] [--executor <path>] [--token <path>] [--audit-dir <path>]
when_to_use: >
  static: verify/archive 前静态预检、架构终审、危险操作前置审核
  runtime: 执行后运行时验证、方案事前审核
  duo: 高风险场景双重验证、Release 门禁
triggers:
  - "/lx-oracle"
  - "/lx-oracle-agent"
  - "/lx-oracle-meta"
  - "/lx-oracle-review"
  - "oracle"
  - "oracle审核"
role: "Oracle gate — static (Oracle-D) + runtime (Oracle-V) + dual review"
execution_mode: stepwise
body_ref: references/body-duo.md
---

# lx-oracle — Oracle 质量门禁系统

> **合并技能**: 原 `lx-oracle-agent`(static) + `lx-oracle-meta`(runtime) + `lx-oracle-review`(duo)
> 保留旧触发器别名 `/lx-oracle-agent` `/lx-oracle-meta` `/lx-oracle-review` 以向后兼容。

三条执行模式：

| 模式 | 协议 | 倾向 | 角色 | 入口 |
|------|------|------|------|------|
| `static` | Oracle-D | 偏紧 · 广度优先 | 静态分析：scope/危险路径/file:line | `oracle_agent.py --mode static` |
| `runtime` | Oracle-V | 偏松 · 深度优先 | 运行时验证：token/失败/软完成/G1-G4 | `oracle_agent.py --mode runtime` |
| `duo` | Oracle-D+V | 互补 | 完整审核：静态+运行时+G1-G4 聚合 | `oracle_agent.py --mode duo` |

## 快速开始

```bash
# 静态分析（原 /lx-oracle-agent）
python3 .claude/scripts/oracle_agent.py review --task-id <task_id> --mode static --plan <path> --executor <path>

# 运行时验证（原 /lx-oracle-meta）
python3 .claude/scripts/oracle_agent.py review --task-id <task_id> --mode runtime --token <path> --executor <path> --logs <path>

# 双 Agent 完整审核（原 /lx-oracle-review）
python3 .claude/scripts/oracle_agent.py review --task-id <task_id> --mode duo --plan <path> --executor <path> --token <path> --logs <path>
```

## 公共审核原则

参见 `references/principles.md`。

## 各模式详情

| 文件 | 说明 |
|------|------|
| `references/principles.md` | 公共审核原则（哲学优先级、0信任、证据门禁、裁决留痕、裁决等级体系） |
| `references/body-static.md` | 静态分析模式详情（原 lx-oracle-agent body） |
| `references/body-runtime.md` | 运行时验证模式详情（原 lx-oracle-meta body） |
| `references/body-duo.md` | 双 Agent 审核模式详情（原 lx-oracle-review body） |
