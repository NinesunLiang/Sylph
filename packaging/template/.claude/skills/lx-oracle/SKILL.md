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
  # 双审(duo)
  - "双法官"
  - "双审"
  # Oracle agent(static, Oracle-D)
  - "oracle"
  - "oracle agent"
  - "oracle-agent"
  - "oracle审核"
  # Mate Oracle(runtime, Oracle-V)
  - "mate oracle"
  - "mate-oracle"
  - "mate"
role: "Oracle gate — static (Oracle-D) + runtime (Oracle-V) + dual review"
execution_mode: stepwise
body_ref: references/body-duo.md
---

# lx-oracle — Oracle 质量门禁系统

> **合并技能**: 原 `lx-oracle-agent`(static) + `lx-oracle-meta`(runtime) + `lx-oracle-review`(duo)
> 保留旧触发器别名 `/lx-oracle-agent` `/lx-oracle-meta` `/lx-oracle-review` 以向后兼容。

## 触发词路由

| 用户说 | 模式 | 角色 |
|---|---|---|
| **双法官 / 双审** | `duo` | 双审(static + runtime 互补,高风险/Release) |
| **Oracle / Oracle agent / oracle** | `static` | Oracle-D 静态分析(消耗小,默认必出) |
| **Mate-Oracle / Mate / mate** | `runtime` | Oracle-V 运行时 TDD(消耗大,Mate 按需升级才出) |

> 例:「双法官审一下」→ duo;「oracle 审 plan」→ static;「mate 复核」→ runtime。

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

## 审判闭环(按需调用,不内嵌工作流)

> Oracle 审阅不强制进入 verify/report 流程,按需触发。组件化设计: 能力在 skill + CLI,人类/AI 在关键点调用。

**入口**（2026-10-24 人类裁决 D-015：`carros_base.py oracle*` 已物理删除，统一走 `oracle_agent.py`）:
- `python3 .claude/scripts/oracle_agent.py review --task-id <ID> --mode static` — 静态审（plan/executor）
- `python3 .claude/scripts/oracle_agent.py review --mode runtime|duo` — 运行时 / 双审
- `python3 .claude/scripts/oracle_agent.py status` — 探活

**闭环流程**（多轮打回单随 `oracle-plan` 一并删除，现由调用方自行循环）:
```
Oracle 审 → ACCEPT 放行 / ADVISORY 记录放行
          └ REJECT  → 按 reasons 修复 → 重新 review
                → 连续 3 轮仍 REJECT → 升级人工(ESCALATE)
```

**触发建议**:
- 高危/架构/不可逆任务: plan 前 + report 前必审
- 一般 L2: 按需
- 熔断: Oracle 不可用 → UNVERIFIED 标记 → archive 阻塞(fail-closed,不降级放行)

**顺序约束（2026-10-24 人类裁决 D-019）**:
- **Mate-Oracle（runtime / duo）只在必要时使用**：方案评审、审核改动；不进入日常命令审批。
- **必须先有 Oracle 静态通过记录**（同 task-id 的 ACCEPT / ADVISORY），否则 `--mode runtime|duo` 直接拒绝（exit 2，`mate_requires_static_pass`）。
- 单条命令的审批走另一条链：AI 自决 → Oracle 静态（建议）→ JEV 决策模型 → 人类。

**组件底层**(carros_base.py / carros_core.py 保留,供 skill 调用):
- `_run_oracle_staged(token, mode, label)` → (verdict, rc, reasons),熔断 fail-closed
- `_aggregate_verdicts(v1, v2)` → 更严者(duo 聚合纯函数)
- `_build_backcard_guidance(reasons)` → 打回修复指引 (carros_core.py, design-doc 15 M0 迁移)
- `_write_unverified_marker(task_id)` → 熔断标记

## 公共审核原则

参见 `references/principles.md`。

## 各模式详情

| 文件 | 说明 |
|------|------|
| `references/principles.md` | 公共审核原则（哲学优先级、0信任、证据门禁、裁决留痕、裁决等级体系） |
| `references/body-static.md` | 静态分析模式详情（原 lx-oracle-agent body） |
| `references/body-runtime.md` | 运行时验证模式详情（原 lx-oracle-meta body） |
| `references/body-duo.md` | 双 Agent 审核模式详情（原 lx-oracle-review body） |
