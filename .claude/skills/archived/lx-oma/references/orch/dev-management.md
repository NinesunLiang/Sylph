# 并行开发管理

## dev list — 并行开发面板

列出所有 `stage: rpe_planned` 或 `stage: in_dev` 的 feature：

```
═══ Parallel Dev Dashboard ═══

Ready (rpe_planned):
  feat-alert-crud          🟢  /lx-rpe prd/alert-engine/feat-alert-crud
  feat-price-evaluation    🟢  /lx-rpe prd/alert-engine/feat-price-evaluation

In Progress (in_dev):
  feat-advanced-evaluation 🔵  终端3  (started 2026-05-08)

Complete (dev_done):
  feat-trigger-history     ✅  (completed 2026-05-08)

Launch commands (copy & paste to new terminals):
  /lx-rpe prd/alert-engine/feat-alert-crud
  /lx-rpe prd/alert-engine/feat-price-evaluation
```

## dev mark <feature-id> <status>

手动标记 feature 的 dev 进度：

`/lx-oma-orch dev mark feat-alert-crud dev_done`

更新 `state/pipeline.yaml` 中对应 `features[].stage = dev_done`。
当所有 feature 标记为 `dev_done` 后，自动设置 `stages.dev = completed`。
