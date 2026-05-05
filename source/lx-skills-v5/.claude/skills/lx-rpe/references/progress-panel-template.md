## RPE 进度面板 — {date}

### 活跃特性| 特性 | Phase | 当前 Task | 状态 | 最近 Commit ||------|-------|-----------|------|------------|| {name1} | Phase 3 | RPE-007 | 🔄 Step 6 | abc1234 (2h ago) || {name2} | Phase 2 | - | ✅ Plan 完成 | - |

### 阻塞项（需要你的决策）

1. 🔴 {feature}/{task}: {阻塞原因} → 建议: {AI 建议} → 已尝试: {已采取的步}

### 今日 Todo（≤3 文件轻量任务）| ID | 类型 | 优先级 | 描述 | 来源 ||----|------|--------|------|------|| #5 | 🐛 | P1 | QueryTasks 空 slice 未检查 | code-review-H4 || #6 | ✨ | P2 | 日志加 requestID 上下文 | 自发现 |

### 未提交变更| 文件 | 变更类型 | 行数 ||------|---------|------|| rpc/internal/logic/xxx.go | M | +45 -12 || pkg/executor/yyy.go | A | +89 |

### 质量快照

- 测试覆盖率: {N}%（{feature} 变更包）
- Code Review: P0={n} P1={n}（最近一次）
- Security: 🔴={n} 🟠={n}（最近一次）

### 今日建议

1. 先解除 {feature} 的阻塞项（预计 {时间}）
2. 推进 {feature}/RPE-xxx（下一步: {Step 描述}）
3. 处理 Todo #{id}（{描述}）
👉 操作: • 继续开发: /lx-rpe {feature} • 处理 Todo: /lx-todo do #{id} • 批量验收: /lx-rpe batch-accept

```
**完成标准**：
- ✅ 所有 RPE 实例的 state/progress.md 已读取
- ✅ executor.md 最近 3 个 Task 已提取
- ✅ 未提交变更已统计
- ✅ 面板中每个数据点有来源（readFile/grep 输出引用）

### 批量验收（子命令：`batch-accept`）
**职责**：一次性验收所有"已完成开发、等待验收"的 RPE 任务项，减少逐个确认的开销。
**前置条件**：至少有一个 RPE 任务项处于 Step 6（已同步，等待验收）。
**执行**：
```
1
. 扫描所有 RPE 实例的 state/progress.md
2. 筛选处于 Step 6（同步完成，等待验收）的任务项
3. 对每个候选任务项： a. 读取 plan.md 中的 AC 列表 b. 读取 executor.md 中的 Evidence 记录 c. 编译验证（Go: `go build ./...` / 前端: `npx tsc --noEmit`） d. 测试验证（Go: `go test -race` / 前端: `npm test`） e. 调用 /lx-pre-commit 验证门禁
4. 生成批量验收报告
1. 扫描所有 RPE 实例的 state/progress.md
2. 筛选处于 Step 6（同步完成，等待验收）的任务项
3. 对每个候选任务项： a. 读取 plan.md 中的 AC 列表 b. 读取 executor.md 中的 Evidence 记录 c. 编译验证（Go: `go build ./...` / 前端: `npx tsc --noEmit`） d. 测试验证（Go: `go test -race` / 前端: `npm test`） e. 调用 /lx-pre-commit 验证门禁
4. 生成批量验收报告

```
**验收报告模板**：
```
mar
k
d
o
w
n
