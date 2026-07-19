---
name: lx-rpe
version: v4.0.0
description: "RPE 系统性特性开发 — 9 步闭环：TDD → code-review → security → acceptance → graded rollback"
complexity: advanced
when_to_use: "Use when user says 'rpe', 'feature dev', '/lx-rpe', or begins systematic feature development"
argument-hint: "new [name] [需求描述] | [feature name] | [path] | status | batch-accept"
harness_version: ">=6.3.0"
status: mature
role: "RPE-driven feature development — 9-step closed loop with quality gates"
execution_mode: stepwise
triggers:
  - "/lx-rpe"
---
# lx-rpe — 主分支系统性开发

## 原子化声明

| 节点 | 路径 |
|------|------|
| scanner | `../../nodes/scanner.md` |
| auto_fixer | `../../nodes/auto_fixer.md` |
| verifier | `../../nodes/verifier.md` |
| report_generator | `../../nodes/report_generator.md` |
| behavior_rules | `../../nodes/behavior_rules.md` |

| 脚本 | 用途 |
|------|------|
| `scripts/git_commit.py` | Git 提交 |
| `scripts/update_progress.py` | 进度更新 |
| `scripts/extract_ac.py` | AC 提取 |
| `scripts/build_and_test.py` | 编译+测试门禁 |

Schema: scan_target / finding / scan_report / fix_record / verdict

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/batch-accept-template.md` | batch accept template 阶段 |
| `references/commit-convention.md` | commit convention 阶段 |
| `references/frontend-coding-rules.md` | frontend coding rules 阶段 |
| `references/gate-checklist.md` | gate checklist 阶段 |
| `references/go-coding-rules.md` | go coding rules 阶段 |
| `references/progress-file-template.md` | progress file template 阶段 |
| `references/progress-panel-template.md` | progress panel template 阶段 |
| `references/recovery-flow.md` | recovery flow 阶段 |
| `references/rpe_main_loop.md` | rpe_main_loop 阶段 |
| `references/rpe_phases.md` | rpe_phases 阶段 |
| `references/security-scan-rules.md` | security scan rules 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
Read Task → Design → Code+Pre-commit → Security → Sync → Wait Acceptance → Judge → Commit → Summary
```

## 硬性约束

- NEVER 做验收决策（用户执行）
- NEVER 混入 todo 概念 — 只有 Step
- ALWAYS 按项目类型路由（Go: go-zero / 前端: React+TS）

## 入口路由

| 子命令 | 动作 |
|--------|------|
| 无参数 | 自动恢复最近活跃 RPE |
| `new` | 初始化新特性 → `@references/rpe_phases.md` |
| `[name]` | 继续指定特性 |
| `[path]` | OMA 目录路径 |
| `status` | 结构化进度面板 → `@references/progress-panel-template.md` |
| `batch-accept` | 批量验收 → `@references/batch-accept-template.md` |

## 新建流程 → `@references/rpe_phases.md`

Phase 1 Research → 用户审阅 → Gate-R → Phase 2 Plan（Task+AC+测试+回滚）→ Gate-P/X → Phase 3 Execute → 主循环

## 恢复流程 → `@references/recovery-flow.md`

自动检测恢复点 → 上下文校验（research/plan/任务完整性）→ 恢复摘要 → 进入阶段

## 主循环 → `@references/rpe_main_loop.md`

```
[1]读任务→[2]设计→[3]编码+pre-commit→[4]Security→[5]同步→[6]等待验收→[7]判定→[8]Commit→[9]摘要
```

回退：编译失败 3 次→回 Step 2 | 验收不通过→按类型回退 | 回退 3 次→暂停

## Pipeline 集成

编排由 `lx-oma-orch` 统一管理。`lx-rpe` 不做 `pipeline.yaml` 读写，仅接收 `BASE_DIR`。

`lx-rpe` 收到 `--pipeline` 时必须拒绝执行并返回参数错误；调用方必须先由 `/lx-oma split --pipeline <id>` 解析状态，再只传递 `BASE_DIR`。

## 降级策略

> 共享降级: `@../references/oma/degradation-escalation.md`

| 场景 | 主路径 | 降级 |
|------|--------|------|
| build_and_test.py 失败 | 脚本 | go build && go test |
| git_commit.py 失败 | 脚本 | git add + git commit（需确认） |
| Gate-X 频繁 >3次 | 暂停 | 回 Phase 2 重审 |
| Phase 迭代 >5轮 | 继续 | 暂停，简化需求 |
