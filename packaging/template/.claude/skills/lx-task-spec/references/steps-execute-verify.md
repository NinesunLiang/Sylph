# Step 2-3: 执行 + 验证

## Step 2: 执行（按类型分流）

**惯性断路器**（执行前自检）：选择的路径（🐛/✨/🔧/📝）是否与 todo 项类型一致？不一致 → 回 Step 1。

各类型执行逻辑 → `@references/execution-types.md`

## Step 3: 快速验证

验证深度矩阵：

| 类型 | 测试范围 | 质量门禁 | 跳过条件 |
|------|---------|---------|---------|
| 🐛 bug | 受影响测试 | `/lx-pre-commit` | 无 |
| ✨ feat | 新功能单元测试 | `/lx-pre-commit` | 无 |
| 🔧 refactor | 已有测试全跑 | `/lx-pre-commit` | 无 |
| 📝 docs | 无 | 无 | **跳过本步** |

执行序列：
```
1. go test -v -run TestXxx ./affected/package
   ├─ PASS → 继续
   └─ FAIL → 修复 → 重跑（计入重试次数）

2. /lx-pre-commit（code-review + security + govulncheck）
```

门禁结果处理：

| 结果 | 重试 | 动作 |
|------|------|------|
| 通过 | - | → Step 4 |
| P0/P1 auto-fix 修复后通过 | - | → Step 4 |
| blocked | 第 1 次 | 修复 → 重跑 |
| blocked | 第 2 次 | **升级 lx-task-spec** |

**关联问题捕获**：验证过程中发现的其他问题 → readFile todo-queue.md → 追加新项 → 不在本轮处理。
