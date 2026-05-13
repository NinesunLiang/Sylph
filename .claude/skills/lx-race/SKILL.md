---
name: lx-race
description: "蜂群协调层：注册子任务 → 派发 → 收集 → 报告。复用 team skill 调度 + OMA Lock 写锁 + race_manager.sh 状态跟踪。不做调度引擎，只做协调。"
complexity: intermediate
version: v1.0.0
harness_version: ">=1.4.0"
model: sonnet
when_to_use: "Use when tasks have multiple independent sub-tasks that can run in parallel; when lx-task-spec identifies independent sub-tasks and routes to race mode; when user says '/lx-race' or '蜂群/并行执行'."
role: "Swarm coordinator — sub-task registration, dispatch, collection, conflict resolution"
execution_mode: race
triggers:
  - "/lx-race"
---

# lx-race — 蜂群协调层 (Swarm Coordination)

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| report_generator | `../../nodes/report_generator.md` | 聚合报告生成 |
| behavior_rules | `../../nodes/behavior_rules.md` | 派发/收集阶段行为约束 |

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `scripts/race_manager.sh` | 状态引擎：register/status/report | 4 步协调流程 |

### 状态机
本 skill 使用私有 4 步协调流程（Register → Dispatch → Collect → Report），不引用 `orchestrator.md` 的通用状态机。
**核心状态映射**: need_input → [register → dispatch → collect → report] → done

### 私有节点
本 skill 无私有节点。

## 降级策略
| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 无子任务可派发 | race_manager.sh register | 报告"无独立子任务"，退出 |
| Task() API 不可用（非 Claude Code） | Task 派发 | 回退到 run_in_background 并行执行 |
| 后台执行不可用 | run_in_background | 回退到顺序执行 |
| race_manager.sh 不存在 | 脚本执行 | 提示脚本缺失，建议重新安装 lx-race |
| 子任务全部失败 | 聚合报告 | 报告失败原因，不阻断父任务 |

> 核心哲学：Race 不做调度，只做**状态跟踪 + 冲突协调**。
> - 调度 → 复用 `team` skill / 平台原生 Task() API
> - 写锁 → 复用 OMA Lock (`pretool-write-lock.sh`)
> - 状态 → `race_manager.sh` (bash + 文件 I/O, **全平台通用**)

## 触发条件

| 输入 | 行为 |
|------|------|
| `lx-race` (skill 调用) | 自动检测上下文中的独立子任务 → 走 4 步协调流程 |
| `race` mode (lx-task-spec) | lx-task-spec 识别独立子任务后，调用 lx-race 作为后端 |

## 跨平台架构

```
                    ┌──────────────────────────────┐
                    │     lx-race SKILL.md          │
                    │  (协调层：注册→派发→收集→报告)  │
                    └──────┬───────────────┬───────┘
                           │               │
              ┌────────────┘               └────────────┐
              ▼                                          ▼
   ┌─────────────────────┐                  ┌──────────────────────┐
   │  Claude Code 路径    │                  │  其他 5 平台路径      │
   │  Task()/TeamCreate   │                  │  run_in_background   │
   │  原生子 Agent 派发    │                  │  顺序/后台执行        │
   └─────────┬───────────┘                  └──────────┬───────────┘
             │                                         │
             └──────────────┬──────────────┘
                            ▼
              ┌─────────────────────────────┐
              │   race_manager.sh           │
              │   (bash + 文件 I/O)          │
              │   全平台统一状态层            │
              └─────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │   OMA Lock                  │
              │   (pretool-write-lock.sh)    │
              │   worker 写文件时自动加锁     │
              └─────────────────────────────┘
```

## 4 步协调流程

### Step 1: 注册 (Register)

调用 `race_manager.sh register` 注册父任务和子任务列表：

```bash
bash .claude/scripts/race_manager.sh register <parent-id> \
  --subtasks "A,B,C" \
  --desc "父任务描述"
```

创建的状态树：
```
.omc/race/<parent>/
  ├── manifest.json          # 父任务元数据 + 子任务列表
  └── subtasks/
      ├── A/owner.json       # 子任务 A 状态 (registered)
      ├── B/owner.json
      └── C/owner.json
```

### Step 2: 派发 (Dispatch)

**根据平台选择派发策略：**

#### 路径 A — Claude Code (原生 Task() API)

使用 `Task()` / `TeamCreate` 派发独立子 Agent，每个 Agent 执行独立的子任务：

```python
# 伪代码 — 实际由 lx-race skill 调用时在 Claude Code 中执行
import subprocess
import json

parent_id = "<parent-id>"
subtasks = ["A", "B", "C"]

for sid in subtasks:
    # 为每个子任务派发独立 Agent
    Task(description=f"""
    执行子任务: {sid}
    父任务: {parent_id}

    工作协议:
    1. 读取 .omc/race/{parent_id}/subtasks/{sid}/owner.json 获取任务定义
    2. 执行子任务 (读/写/修改文件)
    3. 将 RACE_SUBTASK_PATH 设为 .omc/race/{parent_id}/subtasks/{sid}
    4. 完成后写入 result.json:
       echo '{{"status": "completed", "output": "..."}}' > "$RACE_SUBTASK_PATH/result.json"
    5. 失败时写入:
       echo '{{"status": "failed", "output": "..."}}' > "$RACE_SUBTASK_PATH/result.json"
    """)
```

#### 路径 B — 其他 5 平台 (run_in_background / 顺序执行)

OpenCode / Codex CLI / Gemini CLI / Qwen Code / Cursor 不支持原生子 Agent 派发，使用 `run_in_background` 或顺序 bash 执行：

```bash
# run_in_background 并行派发 (平台支持 background 时)
for sid in A B C; do
  RACE_SUBTASK_PATH=".omc/race/<parent>/subtasks/$sid" \
  bash -c '
    # 执行子任务
    # ...
    # 完成后写入 result.json
    python3 -c "
import json
with open(\"$RACE_SUBTASK_PATH/result.json\", \"w\") as f:
    json.dump({\"status\": \"completed\", \"output\": \"...\"}, f)
"
  ' &
done
wait  # 等待所有后台任务完成
```

```bash
# 顺序执行 (平台不支持 background 时)
for sid in A B C; do
  RACE_SUBTASK_PATH=".omc/race/<parent>/subtasks/$sid"
  # 执行子任务...
  # 写入 result.json
done
```

### Step 3: 收集 (Collect)

使用 `race_manager.sh status --all` 轮询所有子任务状态：

```bash
# 人工或自动轮询
bash .claude/scripts/race_manager.sh status <parent-id> --all

# 输出示例:
# RACE:<parent-id> (swarm)
#   progress:  2/3 completed, 0 running, 0 failed, 1 registered
#   subtasks:
#     ✅ A [completed]
#     🔄 B [running]
#     ○ C [registered]
```

### Step 4: 报告 (Report)

全部完成后输出聚合报告：

```bash
bash .claude/scripts/race_manager.sh report <parent-id>

# 输出示例:
# ==========================================
#   Race Report: <parent-id>
# ==========================================
#   Description: ...
#   Progress:    3/3 completed, 0 failed
#   --- subtask: A [completed] ---
#     output: ...
#   --- subtask: B [completed] ---
#     output: ...
```

## Worker 协议

每个子任务的工作 Agent 必须遵守以下协议：

### 环境变量

| 变量 | 说明 | 设置者 |
|------|------|--------|
| `RACE_PARENT_ID` | 父任务 ID | dispatch 阶段 |
| `RACE_SUBTASK_ID` | 子任务 ID | dispatch 阶段 |
| `RACE_SUBTASK_PATH` | 子任务工作目录 (绝对路径) | dispatch 阶段 |

### 完成契约

Worker 完成后**必须**在 `$RACE_SUBTASK_PATH/result.json` 写入：

```json
{
  "race_id": "<parent>/<subtask>",
  "status": "completed",     // 或 "failed"
  "completed_at": "2026-05-04T12:00:00Z",
  "output": "执行摘要，关键结果，证据引用"
}
```

### 失败约定

- 一个子任务失败不影响其他子任务
- 父任务最终状态由所有子任务的聚合结果决定
- OMA Lock 在失败时**不会**自动释放锁文件 — `posttool-write-lock.sh` 负责清理

## 与 OMA Lock 协同

| 场景 | 谁保护 | 机制 |
|------|--------|------|
| 两个 worker 同时写同一个文件 | OMA Lock | `pretool-write-lock.sh` 自动加锁 |
| worker A 不知道 worker B 在做什么 | Race | `race_manager.sh status --all` 可见 |
| worker B 改了 worker A 依赖的文件 | OMA Lock + Race | 锁阻止同时写入，Race 标记依赖冲突 |

OMA Lock 已通过 Bootstrap 安装，无需额外配置：
- hook: `pretool-write-lock.sh` — 写入前原子检查锁文件 (O_EXCL)
- hook: `posttool-write-lock.sh` — 写入后清理锁状态

## 跨平台支持矩阵

| 平台 | 子 Agent 派发 | race_manager.sh | OMA Lock | 备注 |
|------|:-------------:|:---------------:|:--------:|------|
| Claude Code | ✅ Task()/TeamCreate | ✅ bash | ✅ Hook 协议 | 原生支持子 Agent |
| OpenCode | ❌ 无子 Agent | ✅ bash | ✅ AGENTS.md | 退化为后台/顺序 |
| Codex CLI | ❌ 无子 Agent | ✅ bash | ✅ AGENTS.md | 退化为后台/顺序 |
| Gemini CLI | ❌ 无子 Agent | ✅ bash | ⚠️ 有限 Hook | 事件模型最弱 |
| Qwen Code | ❌ 无子 Agent | ✅ bash | ✅ AGENTS.md | 二级平台中最强 |
| Cursor | ❌ 无子 Agent | ✅ bash | ⚠️ 仅 Prompt | 仅 2 个 Hook |

## 文件概览

| 文件 | 行数 | 说明 |
|------|:----:|------|
| `SKILL.md` | ~250 | 本文件 — 协调层定义 |
| `scripts/race_manager.sh` | ~867 | 状态引擎：register/status/report |
| 测试 | ~384 | `.claude/scripts/test_race.sh` |

## 限制与边界

- **不做调度引擎**：调度由平台原生 API (Task/TeamCreate) 或 bash 后台管理
- **不做写锁**：写保护由 OMA Lock 提供
- **不做 Hook**：不需要新增 Hook，复用现有 pretool/posttool write-lock
- **不造新文件协议**：复用 `owner.json` + `result.json` 格式
- **子任务粒度**：建议每个子任务独立可验收，避免依赖链
- **冲突检测**：当前为被动模式（通过 OMA Lock 阻止），主动冲突预测为未来能力


