# 4 步协调流程

## Step 1: Register

```bash
bash .claude/scripts/race_manager.sh register <parent-id> \
  --subtasks "A,B,C" --desc "父任务描述"
```

创建状态树：
```
.omc/race/<parent>/
  ├── manifest.json          # 父任务元数据 + 子任务列表
  └── subtasks/
      ├── A/owner.json       # 子任务状态 (registered)
      ├── B/owner.json
      └── C/owner.json
```

## Step 2: Dispatch

### 路径 A — Claude Code (Task() API)
```
for sid in subtasks:
    Task(description="执行子任务 {sid}，读取 owner.json → 执行 → 写入 result.json")
```

### 路径 B — 其他 5 平台 (run_in_background / 顺序)
```
for sid in A B C; do
  RACE_SUBTASK_PATH=".omc/race/<parent>/subtasks/$sid"
  bash -c '执行... → 写入 result.json' &
done
wait
```

## Step 3: Collect

```bash
bash .claude/scripts/race_manager.sh status <parent-id> --all

# 输出: RACE:<parent-id> (swarm)
#   progress: 2/3 completed, 0 running, 0 failed, 1 registered
#   ✅ A [completed]  🔄 B [running]  ○ C [registered]
```

## Step 4: Report

```bash
bash .claude/scripts/race_manager.sh report <parent-id>

# 聚合所有子任务 result.json → 统一报告
```
