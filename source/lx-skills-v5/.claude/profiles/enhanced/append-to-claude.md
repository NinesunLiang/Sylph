# Enhanced 模式激活补丁

> >
> 将本文件内容追加到项目 CLAUDE.md 末尾以激活 Enhanced 模式
> >
> 命令：`cat .claude/profiles/enhanced/append-to-claude.md
> CLAUDE.md`
> 激活后可使用三种任务驱动模式 + plan-gate 门禁

---

## Enhanced 模式：三种任务驱动

### 激活后可用能力

```plan
e
: true — Research Gate → Plan Gate 两阶段强制门禁（已自动开启）lx-rpe — 模式一：大模块特性完整生命周期lx-todo — 模式二：小任务随时捕获与处理lx-task-spec — 模式三：重要/复杂任务严格 Spec 驱动
plan_gate: true — Research Gate → Plan Gate 两阶段强制门禁（已自动开启）lx-rpe — 模式一：大模块特性完整生命周期lx-todo — 模式二：小任务随时捕获与处理lx-task-spec — 模式三：重要/复杂任务严格 Spec 驱动
```

---

## 三模式路由决策
收到任务时，按以下规则路由：

```任务
规
模 ≤3 文件 且 边界清晰？ → 是：/lx-rpe todo add ... 或 /lx-todo add ...（模式二）
任务有产品文档（PRD）/ 需要完整研究-规划-执行生命周期？ → 是：/lx-rpe new（模式一）
任务规模 >3 文件 且 没有 PRD / 需要精确 AC 驱动？ → 是：/lx-task-spec（模式三） 严格模式（stepwise）→ 高风险变更、跨模块重构 并发模式（race） → 多文件独立修改、批量重构
```

---

## 模式一：/lx-rpe — 大模块特性开发
**适用**：新 API / 新功能模块 / 架构重构 / 需要完整文档体系的特性
**工作流**：

```1
. /lx-rpe new → 创建 rpe/{feature}/ 目录结构 → 填写 prd.md（或 AI 引导式收集） → AI 自动生成 research.md 草稿（关键调用链 + 风险）
2. Phase 1 Research — 用户审阅迭代 → AI 读 prd.md → 深度研究代码库 → 输出 research.md → 用户添加备注 → AI 逐条回应 → 循环直到用户确认
3. Phase 2 Plan — 用户审批 → AI 基于 research 生成 plan.md（任务拆分 + AC + 测试策略） → 用户审阅/调整 → 明确批准后锁定
4. Phase 3 Execute — 自主执行（无人化） → AI 按 plan 逐 Task 执行 9 步主循环 → 每 Task：编码 → pre-commit 门禁 → security → 等验收 → commit → 用户只需在 Step 6 验收和 Step 8 确认 commit
5. /lx-rpe status — 随时查看全局进度面板
```
**Todo 接口**（小任务捕获）：

```/lx-rpe todo add 🐛 P1 <描述> ← 等同于 /lx-todo add/lx-rpe todo next ← 等同于 /lx-todo next
/lx-rpe todo add 🐛 P1 <描述> ← 等同于 /lx-todo add/lx-rpe todo next ← 等同于 /lx-todo next

```

---

## 模式二：/lx-todo — 小任务队列
**适用**：≤3 文件的 bug fix / 配置调整 / 小功能 / 随时冒出的任务
**状态文件**：`.omc/state/todo-queue.md`（与 turn-counter.sh 共享，每 10 轮自动注入）

```/lx-todo add 🐛 P1 <描述> ← 捕获，写入 .omc/state/todo-queue.md/lx-todo next ← 处理最高优先级项（5步闭环：分拣→执行→验证→提交→关闭）/lx-todo do #3 ← 处理指定项/lx-todo list ← 查看队列/lx-todo review ← 批次回顾（模式发现 + 过期清理）
/lx-todo add 🐛 P1 <描述> ← 捕获，写入 .omc/state/todo-queue.md/lx-todo next ← 处理最高优先级项（5步闭环：分拣→执行→验证→提交→关闭）/lx-todo do #3 ← 处理指定项/lx-todo list ← 查看队列/lx-todo review ← 批次回顾（模式发现 + 过期清理）

```
**升级触发**（自动路由到模式一）：- 影响文件 >3- 需要设计阶段- 2 次修复失败

---

## 模式三：/lx-task-spec — 复杂任务严格执行
**适用**：跨模块重构 / 需要精确 AC / 高风险变更 / 重要功能
**两种执行模式**：

```stepwise
e
（逐步，默认） → 规划 → 子任务1验证 → 子任务2验证 → ... → 最终验收 → 每步确认，适合：架构变更 / 有依赖关系 / 高风险 → 用户体验：每个关键节点暂停确认
race（并发） → 规划 → 并行执行所有独立子任务 → 合并验证 → 注意：Claude Code 单线程，race 是"任意顺序"而非真并发 → 适合：多文件独立修改 / 批量格式整理 / 无依赖的测试补全
```
**启动**：

```/lx-task-spec→ AI 逐个提问（5 问：名称/目标/AC/执行模式/优先级）→ 确认 task_input YAML → 规划 → 执行 → 验收报告
/lx-task-spec→ AI 逐个提问（5 问：名称/目标/AC/执行模式/优先级）→ 确认 task_input YAML → 规划 → 执行 → 验收报告

```

**直接发送 YAML**（跳过引导）：

```yaml
t
: task_name: "refactor-auth-module" target: "将 auth 模块从 monolith 拆分为独立 service" pass_criteria: - id: AC-1 description: "所有现有 auth 测试通过" how_to_check: "go test ./pkg/auth/..." expected: "PASS" executor_mode: stepwise priority: p0
yamltask_input: task_name: "refactor-auth-module" target: "将 auth 模块从 monolith 拆分为独立 service" pass_criteria: - id: AC-1 description: "所有现有 auth 测试通过" how_to_check: "go test ./pkg/auth/..." expected: "PASS" executor_mode: stepwise priority: p0
```

---

## Enhanced 配置变更
激活本文件后，harness.yaml 将自动启用：

```yam
l
#
已通过 append-to-claude.md 激活plan_gate: true # Research Gate → Plan Gate 两阶段强制门禁 # 仅对 rpe/{feature}/executor.md 和 plan.md 生效 # 无 rpe/ 目录时自动 fail-open（不影响普通开发）
```
> >
> **注意**：plan_gate 只在编辑 `rpe/*/executor.md` 或 `rpe/*/plan.md` 时触发，
> 普通开发文件不受影响，Base 模式用户无感知。

---

## 无人化程度对比
| 模式 | 用户介入点 | 无人化程度|
|------|-----------|-----------|
|模式一 lx-rpe Phase 3 | 每 Task 的 Step 6 验收 + Step 8 commit 确认 | ★★★★|
|模式二 lx-todo | 最终 commit 确认 | ★★★★★|
|模式三 stepwise | 每个子任务验证 | ★★★|
|模式三 race | 最终合并验收 | ★★★★ |
> 最高无人化：todo 队列 + turn-counter 驱动，用户只需维护 `.omc/state/todo-queue.md`

---
**Enhanced 模式版本：v1.0 | 2026-04-24 | 配合 harness-kit v5.2.2+**
