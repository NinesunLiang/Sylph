# Token Schema

**位置**: `.omc/reference/token.schema.json`（完整版）
**运行时实例**: `.omc/state/token.json`

## 核心字段

| 字段 | 类型 | 说明 | 必须 |
|:---|:---|:---|:---:|
| schema_version | string | Schema 版本号 (v1.0) | ✅ |
| session.id | string | sess_YYYYMMDD_NNNN | ✅ |
| session.level | string | L1_BASE / L2_ENHANCE | ✅ |
| session.model | string | 当前模型 | ✅ |
| task.id | string | task_YYYYMMDD_NNNN | ✅ |
| task.status | string | planning/executing/verifying/blocked/archiving/completed/failed | ✅ |
| task.phase | string | plan/step/verify/archive | ✅ |
| task.current_step | string | S1/P1.S1 格式 | ✅ |
| task.scope | string[] | 允许的文件路径列表 | |
| task.blocked | object|null | 阻塞原因 | |
| stats.done | int | 已完成 step 数 | ✅ |
| stats.total | int | 总 step 数 | ✅ |
| context.watermark_level | string | low/medium/high/unknown | |
| audit[] | object[] | 关键状态变更审计链 | |

## 生命周期

```
plan → step (done=1) → verify → step (done=2) → ... → archive → completed
                    ↑              |
                    └── failed → blocked/retry
```
