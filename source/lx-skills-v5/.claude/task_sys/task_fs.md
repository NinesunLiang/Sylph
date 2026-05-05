# Task Filesystem - 任务文件系统规范

>
> `.omc/state/` 目录/文件规范
> 版本：v2.0.0（模板已外置到 templates/）

---

## 目录结构

```
.omc/state/└── {YYYY-MM-DD}/ └── {task_name}/ ├── input/ │ └── task_input.yaml # 结构化任务输入（见 templates/task_input.yaml） ├── output/ │ ├── clarifier.md # A0 澄清产出 │ ├── plan.md # 计划（见 templates/plan.md） │ ├── criteria.md # 验收标准（见 templates/criteria.md） │ ├── executor.md # 执行记录（见 templates/executor.md） │ ├── acceptance_report.md # 验收报告（见 templates/acceptance_report.md） │ └── summary.md # 任务总结（见 templates/summary.md） └── context/ ├── research.md # 调研笔记 └── lessons.md # 本轮教训（可选）
```

## 命名约定

| 元素 | 规则 | 示例|
|------|------|------|
|`{date}` | `YYYY-MM-DD` | `2026-04-03`|
|`{task_name}` | kebab-case，≤50 字符 | `add-user-auth`|
|文件扩展名 | `.md` / `.yaml` | `plan.md` |

## 清理策略

- 已完成任务（state=done）：保留 30 天
- 被阻断任务（state=blocked）：保留 7 天，超时归档
- 手动清理：用户可删除 `.omc/state/` 下任意目录
