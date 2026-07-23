# tasks/ — 运行时任务文档系统

> 每个任务一个子目录，按 `YYYYMMDD/task-name/` 组织。
> 由 `carros_base.py init` 创建初始骨架。

## 标准任务目录结构

```
tasks/20260723/my-task/
├── plan.md          ← 任务计划（steps, scope, exit criteria）
├── executor.md      ← 执行日志（每步执行记录）
├── handoff.md       ← 交接摘要（compact 前自动写入）
├── research.md      ← 调研笔记
├── evidence.jsonl   ← 验证证据 JSONL
├── working-set.yaml ← 工作集定义（Phase 1 L2）
├── artifacts/       ← 构建/测试产物（临时）
├── state/           ← 任务级运行时状态
│   ├── audit/       ← 任务审计 JSONL
│   └── session-handoff.md
└── sub_task/        ← 子任务定义
```

## 核心文件用途

| 文件 | 生成时机 | 消费者 |
|------|----------|--------|
| `plan.md` | init | 执行时读步骤 |
| `executor.md` | tick（追加） | 恢复时读进度 |
| `handoff.md` | compact 前 | 新会话注入恢复 |
| `evidence.jsonl` | verify | 验收证据存档 |
