# RPE 9 步主循环详情

> 被 lx-rpe/SKILL.md §主循环 引用。SKILL.md 中保留流程总图，具体步骤在此。

---

## Step 1 — 读 RPE 任务项

加载 `@../../nodes/behavior_rules.md`（执行阶段行为约束）。

**执行前检查点（go/no-go）**：
- [ ] 当前有活跃的 RPE 任务项（progress.md 中标记为当前项）
- [ ] 上一步（如有前任务项）已完成并验收通过
- [ ] 当前任务项的影响范围已知（文件列表或 module）
- [ ] 不存在未解决的 BLOCKER
→ 全部 yes → **go** | 任一 no → 先解决再进入 Step 1

**执行**：
```
1. readFile state/progress.md → 第一个未完成的 RPE 任务项
2. grep 相关代码文件 → 预估影响范围
3. 调用脚本提取 AC：python3 scripts/extract_ac.py --feature {name} --task {id}
4. 输出任务概要
```

**完成标准**：
- ✅ 当前任务项 ID + 描述明确
- ✅ 影响范围已评估（引用 grep 输出）
- ✅ 进度文件中该项已标记为当前项

**输出**：`📋 RPE-xxx {描述} · 影响 [N] 文件 → Step 2 设计`

---

## Step 2 — 设计

加载 `@../../nodes/context_collector.md`。按项目类型加载编码规范（Go → `references/go-coding-rules.md` / 前端 → `references/frontend-coding-rules.md`）。

**执行前检查点（go/no-go）**：
- [ ] 当前任务项已从 progress.md 读取并确认
- [ ] 所需上下文（research.md + plan.md）已加载
- [ ] 设计方案前已阅读真实代码（grep/LSP 追踪关键路径）
- [ ] 未超出范围冻结（不修范围外问题，记 TODO）
→ 全部 yes → **go** | 任一 no → 先解决再进入 Step 2

**执行**：
```
1. 分析任务 → 拆解子任务
2. grep/readFile 同类实现 → 提取可复用模式
3. 设计方案：文件列表、变更概要、接口设计、数据流
4. 输出设计文档（不停下等用户，直接进 Step 3）
```

**完成标准**：
- ✅ 子任务列表明确 · 影响文件确定 · 接口设计符合 ISP（≤5 方法）
- ✅ 可复用模式已识别

**输出模板**：
```
## 设计方案：RPE-xxx
### 子任务
### 影响文件 | 文件 | 变更类型 | 概要
### 接口设计
### 可复用模式参考：[existing_file:line]
### 风险点
```

---

## Step 3 — 编码 + pre-commit 门禁

加载 `@../../nodes/auto_fixer.md`。lx-pre-commit 统一处理 Code Review + 测试 + 补测。

**执行前检查点（go/no-go）**：
- [ ] Step 2 设计已完成，影响文件列表已确定
- [ ] 编码规范已按项目类型加载（Go/frontend coding rules）
- [ ] 编译环境就绪（无残留编译错误）
- [ ] 修复上限未耗尽（当前任务修复轮次 < 3）
→ 全部 yes → **go** | 任一 no → 先解决再进入 Step 3

### Go 项目
1. 按设计逐文件实现。关键决策点主动说一句（复用模块、换策略等）
2. 每个文件后编译验证：`python3 scripts/build_and_test.py --type go --budget {N}`
3. 全部完成后 → 调用 lx-pre-commit（编译 → lx-code-review → go test -race → 补测）
4. 门禁通过后 → 生成实现文档写入 executor.md（变更概要 + 关键决策 + 已知限制）

### 前端项目
1. 按设计逐文件实现。关键决策点主动说一句
2. 每个文件后 `npx tsc --noEmit` 增量编译
4. 门禁通过后 → 生成实现文档写入 executor.md

**编译失败处理**：第 1 次修复 → 第 2 次分析设计 → 第 3 次回 Step 2

**完成标准（Go）**：
- ✅ `go build ./...` 通过（exit 0）
- ✅ lx-pre-commit 通过 · P0 = 0 · 测试全部 PASS
- ✅ Change Budget 未超标 · 技术债已记录 · 实现文档已写入

**完成标准（前端）**：
- ✅ `npx tsc --noEmit` 通过（exit 0）
- ✅ lx-pre-commit 通过 · 测试全部 PASS · Change Budget 未超标
- ✅ 实现文档已写入 executor.md

---

## Step 4 — Security Review

加载 `@../../nodes/scanner.md` + `@references/security-scan-rules.md`。

**执行前检查点（go/no-go）**：
- [ ] Step 3 编码 + pre-commit 门禁已全部通过
- [ ] 安全扫描规则已加载
- [ ] 变更文件列表已知且已确认扫描范围
→ 全部 yes → **go** | 任一 no → 先解决再进入 Step 4

### Go 项目

### 前端项目
三层：npm audit → ESLint security → 静态模式扫描（eval/innerHTML/硬编码密钥）

**门禁规则**：✅ 通过 → Step 5；🚫 阻塞 → 修复重扫（max 2 次）

---

## Step 5 — 实现文档 + 验收准备

Step 3 已写入实现摘要（文档 A），此处直接引用，生成文档 B（测试方案）+ 文档 C（验收清单）。

**文档 C 示例**：
```
## 验收清单：RPE-xxx
### 自动验收
- [x] 编译：{输出}
- [x] 测试：{输出}
- [x] Code Review：{判定}
- [x] Security：{判定}
### 人工验收
- [ ] [功能点]：[验证方法]
```

**完成标准**：
- ✅ 文档 A 已引用 · 文档 B/C 已生成
- ✅ 内容与实际变更一致

---

## Step 6 — 验收（AI 自动 + 用户确认）

AI 先自动执行可自动化部分 → 结果 + 人工部分 → 给用户确认。

**单 AI 模式**：
```
📋 RPE-xxx 验收清单
自动验收（已完成）：
  ✅ 编译：go build ./... 通过
  ✅ 测试：go test -race — N passed
人工验收（需要你做）：
  1. {功能点} → 命令 → 期望
你可以：自己跑命令 / "帮我跑" / "通过"
```

**完成标准**：
- ✅ 自动验收已执行 · 用户已确认
- ✅ 未收到确认不推进到 Step 7

---

## Step 7 — 判定验收结果

加载 `@../../nodes/verifier.md`。

| 判定 | 问题类型 | 回退 | 动作 |
|------|---------|------|------|
| ✅ 通过 | 无 | → Step 8 | 继续 |
| ❌ 功能缺失 | 缺功能 | → Step 3 | 补充实现 |
| ❌ 逻辑缺陷 | 有 bug | → Step 3 | 修复 |
| ❌ 规范问题 | 风格/命名 | → Step 3 | minor fix |

回退限制：第 1-2 次正常修复，第 3 次暂停讨论。

---

## Step 8 — Git Commit

加载 `@references/commit-convention.md`。必须用户确认后才执行。

```
1. --dry-run 展示给用户：commit message + 变更文件 + diff 统计
2. 等待用户明确确认
3. 确认后去掉 --dry-run 执行：python3 scripts/git_commit.py
```

**铁律**：必须用户明确确认后才执行实际提交。

---

## Step 9 — 写进度摘要

加载 `@../../nodes/report_generator.md`。

**更新文件**：`state/progress.md` + `executor.md`

```
1. 调用 scripts/update_progress.py 更新状态
2. 任务项标记为已完成 [x]
3. executor.md 补充 Evidence + 回滚演练记录 + Gate-E 状态
```

**完成标准**：
- ✅ progress.md 已更新 · executor.md Evidence 已记录
- ✅ 当前任务完成 · 下一步已明确
