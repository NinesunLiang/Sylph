# Race 文档即信物 — 终稿 v10

> 10 轮迭代完成，双法官审查通过 ✓
> 审查得分 8.8/10，3 个待修复问题已在终稿中纳入

---

## 方案摘要

**核心思想**：main ↔ subagent 不直接对话，通过文件系统（文档即信物）交接。

**路径**：`.omc/plan/{date}/{taskid}_{time}/task.md`

**工具链**：
- `race-tool.py` — 新建，~250 行，管理 task.md 的创建/读取/报告
- `lx-plan.py` — 扩展 +40 行，增加 race-init/race-report/race-scan 子命令
- `race-subagent-protocol.md` — 新建，subagent 执行契约

**状态机**：pending → assigned → running → done/failed/timeout → retry → blocked

---

## 终稿设计方案

### 目录结构

```
.omc/plan/{YYYY-MM-DD}/
├── manifest-{batch}.json      # 可选，批次清单
├── {taskid}_{HHMMSS}/
│   └── task.md                # 唯一文件（YAML frontmatter + markdown body）
├── {taskid}_{HHMMSS}/
│   └── task.md
└── ...
```

### task.md 格式

```yaml
---
task_id: "fix-config-3_143021"
batch: "feature-abc"
status: "pending"              # pending | assigned | running | done | failed | timeout | blocked
created_at: "2026-06-09T14:30:21+08:00"
deadline: "2026-06-09T15:00:21+08:00"
assigned_at: null
completed_at: null
retry_count: 0
max_retries: 3
subagent: null
error: null
task_dir_rel: ".omc/plan/2026-06-09/fix-config-3_143021"  # 跨机器兼容
---
# Task: fix-config-3

## Goal

...

## Context

...

## Completion Criteria

- [ ] AC1
- [ ] AC2

## Result

### Output

...

### Evidence

[已验证: file:line] ...

### Error（仅失败时）

...
```

### main agent 流程

```
1. race-tool.py init <batch> --tasks A,B,C
   → 为每个子任务创建 task.md

2. delegate_task 分批派发（每批最多 max_concurrent 个）
   context 按 RDP 协议：
     protocol: race-document-token/v1
     task_dir: <绝对路径>
     task_dir_rel: ".omc/plan/..."  # 跨机器兼容
     batch: <batch>
     task_ids: ["A"]
     retry_attempt: 1（重试时）
     previous_error: "..."（重试时）

3. 轮询 task.md
   while not all done:
     for td in task_dirs:
       status = read_frontmatter(td/task.md)['status']
       if status == 'done': collect
       elif status == 'failed' and retry_count < 3: retry
       elif status == 'running' and deadline expired: retry
       elif status == 'running' and deadline ok: wait
     sleep 5

4. race-tool.py report <batch>
   → 聚合报告
   → 检测"假 done"（status=done 但 Result 为空 → inconsistent）
   → 追加到 HISTORY.md

重试时 subagent 的调整策略：
  retry_attempt=2 + previous_error="timeout"
  → subagent 应缩小工作范围、减少重操作
  retry_attempt=2 + previous_error="permission denied"
  → subagent 应换路径或降级
```

### subagent 契约

1. 解析 context → 提取 task_dir
2. 读 task.md → 只有 status=pending 才执行
3. 更新 frontmatter → status=running
4. 处理任务
5. 写入 Result
6. 更新 frontmatter → status=done/failed

---

## 与现有体系的关系

```
完整文档体系（多文件）:
  stepwise:  .omc/plan/{date}/{slug}/  (prd/executor/progress + checkpoints)
  RPE:        rpe/{name}/              (proposals/executor/postmortem)

轻量单文件:
  race:       .omc/plan/{date}/{taskid}_{time}/task.md
```

---

## 产出物清单

### 新建文件

| # | 文件 | 说明 | 优先级 |
|:--|------|------|:------:|
| 1 | `.claude/scripts/race-tool.py` | task.md 管理工具 | P0 |
| 2 | `.claude/reference/race-subagent-protocol.md` | subagent 执行契约 | P0 |

### 修改文件

| # | 文件 | 改动 | 优先级 |
|:--|------|------|:------:|
| 3 | `.claude/skills/lx-race/SKILL.md` | 重写，指向文档即信物模式 | P0 |
| 4 | `.claude/skills/lx-race/references/body.md` | 重写 4 步流程 | P0 |
| 5 | `.claude/scripts/lx-plan.py` | 新增 race-init/race-report/race-scan | P1 |
| 6 | `AGENTS.md` | 路由索引更新 | P1 |
| 7 | `.claude/reference/execution-modes.md` | race 描述更新 | P2 |
| 8 | `.claude/skills/lx-task-spec/references/body.md` | race 引用更新 | P2 |

### 不改的文件

| 文件 | 原因 |
|------|------|
| `race_manager.sh` | 保留旧接口兼容 |
| `settings.json` | 不涉及 hook |
| `task-workspace.sh/.py` | 已有功能不动 |
| `orchestrator.md` | 独立状态机 |

---

## 双法官结论

```
Oracle 审查  : ✅ PASS（静态一致性 + 文件路径检查通过）
Meta-Oracle  : ✅ PASS（8.8/10，3 个 minor 问题已纳入终稿）
  修正项:
    1) context 中增加 task_dir_rel 字段 ✓
    2) 聚合时检测"假 done" ✓
    3) 补充重试行文指引 ✓
```

等待 Boss 审批后开始执行。
