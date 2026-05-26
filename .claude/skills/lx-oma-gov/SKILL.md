---
name: lx-oma-gov
description: OMA PRD 治理 — reconcile/propagate 增量同步、冲突裁决、漂移检测
version: v1.2.1
harness_version: ">=6.3.0"
status: mature
argument-hint: "init [path] | reconcile [path] | resolve <CONFLICT-ID> <verdict> [--reason] | propagate --dry-run|--execute [path] | status | audit [path]"
when_to_use: 主 PRD 变更需向下游 feature 增量同步、检测漂移、PRD 冲突需人工裁决、查看治理状态
triggers: ["/lx-oma-gov", "oma治理", "reconcile", "propagate", "漂移检测"]
role: "PRD governance — drift detection, reconciliation, propagation"
execution_mode: stepwise
---

# lx-oma-gov OMA PRD 治理

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| explore | `../../nodes/explore.md` | 扫描 feature 目录 |
| verifier | `../../nodes/verifier.md` | reconcile 质量验证 |

| 规范文档 | 用途 |
|---------|------|
| `governance-spec.md` | 完整规范（对象 ID/状态机/漂移规则） |
| `HUMAN-IN-THE-LOOP-GATE.md` | awaiting_human_decision 状态机 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/directory-structure.md` | init |
| `references/commands-reconcile.md` | reconcile/verifier/resolve/propagate |
| `references/commands-audit.md` | audit |
| `references/pipeline-integration.md` | pipeline |

> 共享 OMA 能力 `@../references/oma/`: degradation-escalation · decision-chain · execution-workflow · skill-chaining · observability

## 状态机

```
need_input
  → [init] → initialized
  → [reconcile] → reconciling
      → [no changes] → done
      → [L3 conflict] → awaiting_human_decision → [resolve] → reconciling
      → [changes ready] → verifying → propagating_dry_run
          → [confirmed] → propagating → done
  → [status] → done
  → [audit] → done
  → [error] → [repair → undone | reset → initialized]
```

## 命令

### init → `@references/directory-structure.md`
`/lx-oma-gov init [path]` — 创建 state/ + source-prds/ + snapshots/ + 日志

### reconcile / verifier / resolve / propagate → `@references/commands-reconcile.md`
变更检测（L1/L2/L3 分级）→ verifier 质量门禁 → resolve 人工裁决 → propagate 增量传播

### status — 治理状态面板
### audit → `@references/commands-audit.md`
四类漂移检测（ID 孤儿/版本落后/冲突定义/孤立变更）

## Pipeline 集成 → `@references/pipeline-integration.md`
只读 pipeline.yaml。命令执行后输出 governance-report.yaml 供 orch 消费。

## 治理质量自检

1. CHG-ID 完整性：格式 `CHG-YYYYMMDD-NNN`
2. CHG 分类正确性：L3 必须涉及 REQ-/DEC-/TERM- 修改
3. CONFLICT-ID 闭合性：已裁决标记 resolved
4. 幂等安全：重复 propagate 不产生重复内容
5. 引用一致性：propagate 后所有引用在 master 中存在
6. 同步状态：活跃 feature 同步时间 ≥ 最后 reconcile

## 降级策略
| 场景 | 主路径 | 降级 |
|------|--------|------|
| 治理目录不存在 | 报错 | 先运行 init |
| reconcile 无变更 | 报告"无差异" | fast path done |
| L3 冲突无裁决 | 挂起 + 提示 | 继续 L1/L2 |
| propagate 目标缺失 | 跳过 | 列出缺失 feature |
| 锁超时 | 自动释放 | 记录清除日志 |
