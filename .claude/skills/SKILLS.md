# Carror OS Skill 体系

## 分层架构

```
Governance (治理)           Workflow (工作流)
  lx-oracle                   lx-pre-commit  lx-pre-push
                              lx-root-cause-analysis  lx-stepwise

Autonomous (自主)           Feature Dev (特性开发)
  lx-goal                     lx-rpe
  lx-ghost

Foundation (基础)
  lx-task-spec  lx-codebase-design  lx-domain-modeling
```

## 依赖关系

```
lx-goal ──→ lx-stepwise (子任务路由)
lx-ghost ──→ lx-oracle (自主计划审核)
lx-task-spec ──deep→ lx-stepwise (串行攻坚引擎)
```

## 共享基础设施

| 文件 | 被引用者 |
|------|---------|
| `references/oma/` | lx-rpe (残余引用，待清理) |
| `schemas/atomic/verdict.yaml` | ALL skills |
