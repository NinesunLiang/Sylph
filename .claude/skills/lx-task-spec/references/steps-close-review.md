# Step 4-5: 关闭 + 批次回顾

## Step 4: 关闭

**前置一致性检查**: "Step 2 的修复目标与 Step 3 的验证范围是否一致？"
不一致 → 回 Step 3 补充验证。

执行序列（Git 门禁遵循 `@../../nodes/behavior_rules.md` §1.4）：

```
1. 暂存变更文件（禁止 git add -A）
   git add <file1> <file2>

2. commit（需用户确认），message 格式：
   🐛→fix / ✨→feat / 🔧→refactor / 📝→docs

3. 更新 todo-queue.md：从"进行中"→"已完成"
```

输出：`✅ #[id] 完成 · 验证 ✅ · [commit hash] 📋 剩余 [N] 项 · 👉 /lx-todo`

## Step 5: 批次回顾 (`review`)

触发时机：每日收工前 或 ≥5 已完成项。

```
1. readFile .omc/state/todo-queue.md
2. 统计各区项数
3. 检查：
   ├─ P0/P1 >1 天未处理？→ 警告
   ├─ P2/P3 >7 天过期？→ 建议降级或关闭
   ├─ 已完成项系统性模式？→ 建议主分支重构
   └─ 升级项已被主分支接收？→ 确认
```

输出：

```
## Todo 批次回顾

### 统计
| 状态 | 数量 | 明细 |
|------|------|------|
| 待处理 | [N] | P0:[n] P1:[n] P2:[n] P3:[n] |
| 进行中 | [N] | #[ids] |
| 今日完成 | [N] | #[ids] |

### 告警
- ⚠️ P1 项 #[id] 已待处理 [N] 天
```
