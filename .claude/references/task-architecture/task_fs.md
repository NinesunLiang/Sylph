# Task Filesystem - 任务文件系统规范 [SUPERSEDED]

> 状态: SUPERSEDED — 请参考 `@.claude/references/current-task-architecture.md`
> 最后对齐: 2026-07-28
>
> 此文件为历史设计文档。实际路径格式已调整：
> - 日期格式: YYYY-MM-DD → **YYYYMMDD**（`strftime("%Y%m%d")`）
> - task_name → **task_id**（kebab-case slug，自动生成或手动指定）
> - 无 context/ 子目录（已合并到 TASK_DIR/state/）

---

## 实际路径

```
.omc/tasks/{YYYYMMDD}/{task_id}/
├── plan.md           # 计划（步骤清单）
├── executor.md       # 执行证据账簿（schema_version: v2）
├── research.md       # 调研笔记 / Phase 0 前置澄清
├── sub_task/         # 子任务目录
├── state/            # 运行时状态
│   └── audit/        # 审计日志
└── final-report.md   # 归档报告
```

**Token**: `.omc/tokens/{YYYYMMDD}/{task_id}.json`

## 关键代码

- `carros_base.py L101-103`: `_get_date_str()` 返回 `datetime.now(timezone.utc).strftime("%Y%m%d")`
- `carros_base.py L105-122`: `_init_task_paths()` — 按 task_id + 日期初始化所有路径
- `carros_base.py L148-175`: `_default_token()` — token 结构定义
