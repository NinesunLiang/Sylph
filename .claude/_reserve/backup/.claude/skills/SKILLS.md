# Carror OS Skill 体系

## 分层架构

```
Governance (治理)           Workflow (工作流)
  lx-purify                  lx-todo  lx-code-review
  lx-oracle                  lx-test-gen  lx-pre-commit  lx-pre-push
  lx-validate-skill          lx-status  lx-sync  lx-dogfood
                             lx-root-cause-analysis  lx-stepwise

Autonomous (自主)           OMA Pipeline (管线)
  lx-goal                    lx-oma-hier → lx-oma-split → lx-oma-gov → lx-rpe
  lx-ghost                   lx-oma-orch (编排)
                             lx-race (并行执行引擎)

Foundation (基础)
  lx-task-spec  lx-learner  lx-skillify  lx-varlock  update-carror-os
```

## 依赖关系

```
lx-goal ──→ lx-race / lx-stepwise (子任务路由)
lx-ghost ──→ lx-oracle (自主计划审核)
lx-oma-orch ──→ lx-oma-hier / lx-oma-split / lx-oma-gov (管线编排)
lx-oma-split ──→ lx-oma-hier (依赖 hier 完成)
lx-oma-gov ──→ lx-oma-split (依赖 split 完成)
lx-task-spec ──→ lx-oma-orch (Enhanced 模式)
lx-purify ──→ lx-oracle (双法官审核)
```

## 共享基础设施

| 文件 | 被引用者 |
|------|---------|
| `references/oma/degradation-strategies.md` | hier, split, orch, gov |
| `references/oma/observability.md` | hier, split, orch, gov |
| `references/oma/pipeline-contract.md` | hier, split, orch, gov |
| `references/oma/direction-guide.md` | hier, split, rpe |
| `schemas/atomic/error_codes.yaml` | hier(HIER), split(SPLIT), orch(ORCH), gov(GOV) |
| `nodes/oracle_terminal.md` | orch, goal, ghost, purify |
| `nodes/mode_selector.md` | orch, goal, ghost |

## 废弃

| Skill | 替代 |
|-------|------|
| lx-oracle-v2 | → lx-oracle v2.0 |
