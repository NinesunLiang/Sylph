# Carror OS Skill 体系

## 分层架构

```
Governance (治理)           Workflow (工作流)
  (暂无)                      lx-todo  lx-code-review
  (soft ref: lx-oracle)       lx-pre-commit  lx-pre-push
  lx-validate-skill           lx-dogfood
                              lx-root-cause-analysis  lx-stepwise

Autonomous (自主)           OMA Pipeline (管线)
  lx-goal                    lx-oma-hier → lx-oma-split → lx-oma-gov → lx-rpe
  lx-ghost                   lx-oma-orch (编排)

Foundation (基础)
  lx-task-spec  lx-learner  lx-skillify  lx-varlock
```

## 依赖关系

```
lx-goal ──→ lx-stepwise (子任务路由)
lx-ghost ──→ lx-oracle (自主计划审核)
lx-oma-orch ──→ lx-oma-hier / lx-oma-split / lx-oma-gov (管线编排)
lx-oma-split ──→ lx-oma-hier (依赖 hier 完成)
lx-oma-gov ──→ lx-oma-split (依赖 split 完成)
lx-task-spec ──→ lx-oma-orch (Enhanced 模式)
```

## 共享基础设施

| 文件 | 被引用者 |
|------|---------|
| `references/oma/degradation-strategies.md` | hier, split, orch, gov |
| `references/oma/observability.md` | hier, split, orch, gov |
| `references/oma/pipeline-contract.md` | hier, split, orch, gov |
| `references/oma/direction-guide.md` | hier, split, rpe |
| `schemas/atomic/error_codes.yaml` | hier(HIER), split(SPLIT), orch(ORCH), gov(GOV) |
| `nodes/oracle_terminal.md` | orch, goal, ghost |
| `nodes/mode_selector.md` | orch, goal, ghost |

## 归档

| Skill | 归档原因 | 路径 |
|-------|---------|------|
| lx-purify | 低频思想纯度审计 | `archived/lx-purify/` |
| lx-sync | 变更后一致性检查 | `archived/lx-sync/` |
| lx-race | 并行执行，有独立CLI | `archived/lx-race/` |
