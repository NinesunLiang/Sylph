# 目录结构约定

## Feature 目录

```
prd/{sub_prd}/{feature}/
  prd.md              ← feature PRD（治理目标）
  research.md         ← 技术调研
  plan.md             ← 实施计划
  executor.md         ← 执行记录
  state/
    progress.md       ← 状态追踪
  sync-notes.md       ← 同步记录（由 propagate 维护）
```

## init 创建的治理目录

```
./
  master-prd.md                 ← 主 PRD（权威源）
  source-prds/                  ← 原始输入 PRD
  state/
    sync-state.md               ← 最后 reconcile 快照
    pending-decisions.md        ← 待裁决队列
    feature-map.md              ← feature 注册表
  snapshots/                    ← 历史快照
  CONSOLIDATION-LOG.md          ← 变更日志
  PRD-INBOX.md                  ← 原始 PRD 收件箱
```
