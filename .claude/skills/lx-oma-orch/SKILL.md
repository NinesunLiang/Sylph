---
name: lx-oma-orch
description: Pipeline Orchestrator — 4-skill 管线编排（状态查看/阶段推进/Oracle 门禁/并行开发管理）
version: v1.2.2
harness_version: ">=6.3.0"
status: stable
argument-hint: "status | advance [--force] | gate <og-id> approve|reject [--reason \"...\"] | run <target> | dev list | dev mark <feature-id> <status>"
when_to_use: |
  查看 PRD 全生命周期管线进度、推进到下一阶段、裁决 Oracle 门禁、直接路由到子 skill、管理并行开发进度
triggers: ["/lx-oma-orch", "pipeline", "管线状态", "orchestrate"]
role: "Pipeline orchestrator — 4-skill lifecycle orchestration with Oracle gates"
execution_mode: stepwise
---

# lx-oma-orch Pipeline Orchestrator

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| oracle | `../../nodes/oracle_terminal.md` | 阶段转移门禁裁决 |
| mode_selector | `../../nodes/mode_selector.md` | 执行模式路由 |

| 子 skill | 用途 |
|---------|------|
| lx-oma-hier | Level 1 分层拆解 |
| lx-oma-split | Level 2 特性拆解 |
| lx-oma-gov | 治理 reconcile/propagate |
| lx-rpe | 特性级开发计划 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/status-panel.md` | status |
| `references/advance-flow.md` | advance |
| `references/oracle-gate.md` | gate |
| `references/dev-management.md` | dev |
| `references/pipeline-contract.md` | pipeline 更新 |
| `references/error-codes.md` | error codes |
| `references/observability.md` | observability |
| `references/interface-contract.md` | 接口契约 |
| `references/manual-review.md` | 人工审核 |

> 共享 OMA 能力 `@../reference/oma/`: degradation-escalation · decision-chain · execution-workflow · skill-chaining

## 状态机

```
idle → [status] → done
     → [advance] → checking_oracle_gate
         → [blocked] → awaiting_decision → [approve/reject] → advance/abort
         → [passed] → calling_skill → update_pipeline → done
     → [gate <id> approve|reject] → update_pipeline → done
     → [run <target>] → route_to_skill → done
     → [dev list|mark] → done
```

## 命令

### status — 管线全景 → `@references/status-panel.md`
### advance — 推进阶段 → `@references/advance-flow.md`
检查→路由→执行→更新→人工确认。

### gate — Oracle 门禁 → `@references/oracle-gate.md`
`/lx-oma-orch gate <og-id> approve|reject [--reason "..."]`

### run — 直接路由（绕过阶段检查）
| 目标 | 路由 |
|------|------|
| Sub PRD | lx-oma-hier |
| Feature | lx-oma-split |
| 治理 | lx-oma-gov |
| RPE | lx-rpe |

### dev — 并行开发 → `@references/dev-management.md`

## Pipeline 更新 → `@references/pipeline-contract.md`
原子写入（tmp→rename）+ 更新规则 + Oracle gate 创建。

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| advance 失败 | 检查管线状态，手动修复 |
| gate 不可用 | 跳过 Oracle 门禁，标注 [无Oracle审核] |
| Pipeline 写入失败 | 降级为手动状态跟踪 |
