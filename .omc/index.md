# .omc/ — 运行时目录

> AI 唯一读写域。所有任务文档、令牌、状态均在此目录下。

## 目录系统

| 目录 | 用途 |
|------|------|
| `tasks/` | 任务文档系统 — AI 任务的唯一落脚点 |
| `tokens/` | 令牌系统 — 任务/会话级令牌（goal、无人模式、AI 任务） |
| `archive/` | 已归档任务和令牌 |
| `audit/` | 审计日志 JSONL（pretool/posttool 门禁记录） |
| `knowledge/` | 升华管道数据 |
| `metrics/` | 基准测试数据 |

## tasks/ — 任务文档系统

```
.omc/tasks/{date}/{task_name}/
├── research.md              # Phase 0 调查 + 根因分析
├── plan.md                  # 执行计划（Steps + AC）
├── executor.md              # 每步证据块（action/file/command/output/status）
├── state/                   # 附属状态文件（checklist.md 等）
├── state.json               # 阶段追踪（draft → executing → completed）
└── sub_tasks/               # 子任务（可选）
    └── {sub_task_name}/
        ├── research.md
        ├── plan.md
        └── executor.md
```

## tokens/ — 令牌系统

```
.omc/tokens/{date}/{task_name}.json   # 任务令牌 — 含 plan_dir 指针 + 计数器 + 过期
```

令牌独立于 tasks 目录。compact 恢复时扫描 `.omc/tokens/` → 找到活跃 token → 读 `plan_dir` 字段 → 进入 `.omc/tasks/{date}/{task_name}/` 续跑。

## state/ — 运行时状态

```
.omc/state/
├── tokens/                                  # 会话级令牌（lx-goal.json, autonomous.active）
├── last-user-prompt.md                      # 最近用户请求
├── last-user-prompts/                       # 多终端用户 prompt 记录
├── snapshots/                               # PreCompact 快照
├── oracle/                                    # Oracle 统一裁决（static/runtime/meta/duo/bypass 按 type 区分）
├── oracle-audit/                              # Oracle 执行审计日志
