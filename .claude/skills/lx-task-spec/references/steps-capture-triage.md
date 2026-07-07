# Step 0-1: 捕获 + 分拣

## Step 0: 捕获 (`add`)

解析四要素（类型/优先级/描述/来源）：

| 要素 | 必填 | 缺失处理 |
|------|------|---------|
| 类型 | 是 | 从描述推断：bug→🐛 feat→✨ refactor→🔧 docs→📝 |
| 优先级 | 否 | 默认 P2 |
| 描述 | 是 | 缺失 → 询问用户 |
| 来源 | 否 | 默认 `自发现` |

执行：
```bash
python3 .claude/skills/lx-todo/scripts/todo_queue.py \
  --action add --type {类型} --priority {优先级} --desc "{描述}" --source "{来源}"
```

**完成标准**：✅ todo-queue.md 已更新（readFile 验证）✅ 新项含 ID+类型+优先级+描述+日期

输出：`✅ #[id] [类型][优先级] [描述] 📋 待处理 [N] 项 · 👉 /lx-todo`

## Step 1: 分拣（30 秒决策）

搜索定位影响范围：
```bash
grep -rn "关键词" --include="*.go" -l | head -20
```

决策矩阵：

| 条件 | 判定 | 动作 |
|------|------|------|
| 影响文件 ≤3 且改动明确 | ✅ Todo | 更新为"进行中" → Step 2 |
| 影响文件 >3 | ❌ 升级 | → lx-task-spec |
| 需新增 API/接口/模块 | ❌ 升级 | → lx-task-spec |
| 不确定 → ≤5min 读上下文 | 再判断 | readFile → 重评 |
| 读完仍不确定 | ❌ 升级 | 宁重不漏 |

**量化门禁**：影响文件数必须通过 `grep -l` 实际计数，不可目测。
