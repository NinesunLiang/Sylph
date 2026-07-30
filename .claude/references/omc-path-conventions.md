# .omc 路径规范

> Cross-platform (Mac/Windows/WSL)，纯 pathlib 路径，无 shell 依赖。

## 目录布局

```
.omc/
├── state/              # 运行时状态（.gitignore 排除）
│   ├── token.json      # 唯一运行状态源（schema_version v1.0）
│   ├── plan.md         # 唯一计划与验收规则源
│   ├── executor.md     # 唯一执行证据源
│   ├── session-handoff.md  # 唯一 compact/resume 摘要源
│   └── audit/          # 审计事件 *.jsonl
│       └── YYYYMMDD.jsonl
├── scripts/            # Python 工具
│   ├── carros_base.py  # 核心 6 命令
│   ├── omc_lint.py     # 统一 lint
│   └── init-omc.sh     # 初始化脚本（可选）
└── reference/          # 参考文档
    ├── token.schema.json        # token JSON Schema
    ├── omc-path-conventions.md   # 本文件
    ├── SUBAGENT.md              # SubAgent 派发契约
    └── enhance/                 # L2 Enhance 参考
```

## 路径规则

1. 所有路径使用 `pathlib.Path`（不用 os.path.join）。
2. `.omc/state/` 在 .gitignore 中排除（运行时状态不提交）。
3. `.omc/reference/` 提交到 git（参考文档）。
4. `.claude/scripts/` 提交到 git。
5. audit JSONL 按日分片：`YYYYMMDD.jsonl`。
6. 归档文件放在 `.omc/archive/` 中。

## 日期格式约定（Task7 Phase2 GREEN）

所有路径/文件名使用 `YYYYMMDD`（无分隔符），所有人类可读时间戳使用 `YYYY-MM-DD` (ISO 显示)。

| 场景 | 格式 | 示例 | 说明 |
|------|------|------|------|
| .omc/tasks/{date}/ | YYYYMMDD | 20260729 | 任务文档目录 |
| .omc/tokens/{date}/ | YYYYMMDD | 20260729 | token 存储目录 |
| audit *.jsonl | YYYYMMDD.jsonl | 20260729.jsonl | 审计日志文件名 |
| handoff 显示 | YYYY-MM-DD | 2026-07-29 | 人类可读时间戳 |
| Reader 兼容 | YYYY-MM-DD (legacy) | 2026-07-29 | 只读，不创建新目录 |

Reader API (lib/task_paths.py) 兼容 legacy `YYYY-MM-DD` 目录但不创建；
同 slug 跨格式冲突时报告且拒绝覆盖。
所有路径 Creator 仅使用 `YYYYMMDD`。

## 五源真相

| 源 | 路径 | 谁写 | 作用 |
|----|------|------|------|
| token.json | .omc/state/token.json | carros_base.py | 运行状态 |
| plan.md | .omc/state/plan.md | carros_base.py init | 计划 |
| executor.md | .omc/state/executor.md | 模型手动 | 执行证据 |
| session-handoff.md | .omc/session-handoff.md | compact 前写 | 恢复摘要 |
| audit | .omc/state/audit/*.jsonl | carros_base.py | 审计链 |
