---

name: lx-todo

version: v4.0.0

description: "Lightweight todo workflow: capture, triage, fix, verify, close. 5-step single-terminal loop with quality gates and hard upgrade limits."

when_to_use: "Use when user says 'todo', 'quick fix', 'small bug', 'add todo', 'todo list', or wants to handle a minor task without full RPE flow."

model: sonnet

argument-hint: "add 🐛 P1 <desc> | do [#id] | next | list | review"

paths:

 - "*.go"

 - "go.mod"

harness_version: ">=1.1.0"

---

# Todo Branch — 轻量开发模式 v1.0

## 原子化声明

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机|
|------|------|----------|
|`scripts/todo_queue.py` | todo-queue.md 读写（list/add/start/complete/upgrade）| 所有子命令 |

> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|behavior_rules | `../../nodes/behavior_rules.md` | 研究/执行阶段行为约束（防编造/证据门禁/Git 门禁/修复上限）|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|task_input | `../../schemas/input/task_input.yaml` | 结构化任务输入（todo 项四要素）|
|acceptance_report | `../../schemas/output/acceptance_report.yaml` | Step 4 关闭时的验收报告格式|
|verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长 todo 处理会话的上下文总结 |

### 状态机
本 skill 使用**私有轻量状态机**（Capture → Triage → Execute → Verify → Close），不引用 `orchestrator.md` 的通用状态机。原因：todo 是单终端 5 步闭环，无需 need_clarification/planning/spec_review 等重型状态。
**核心状态映射**: need_clarification → executing → [Capture, Triage, Execute, Verify, Close] → done

### 私有节点
本 skill 无私有节点，全部逻辑内联于 SKILL.md。

---

## 角色与边界（C2 四要素）
- **我是谁**：单终端执行者（Claude Code），负责小范围代码变更的完整闭环- **在哪**：任何项目，独立运行，与 lx-rpe / lx-task-spec 互相独立- **做什么**：5 步闭环——捕获 → 分拣 → 执行 → 验证 → 关闭，处理 ≤3 文件的 bug/feature/refactor/docs- **不做什么**：不做需要设计阶段的新功能、不做 >3 文件的变更、不做安全架构设计——复杂任务升级到 lx-task-spec，大特性升级到 lx-rpe

## 会话目标锚定（静默执行，不输出给用户）
> AI 内部自检，不在界面显示。只在 Session 恢复时输出一行提示。
**AI 内部自检（每个操作前）**：- 变更文件数是否超过 3？是 → 停止，升级 lx-task-spec- 本步重试次数是否达到 2？是 → 停止，升级 lx-task-spec- 上一步完成标准是否满足？否 → 回到上一步

每个操作前检查（AI 内部静默）：1. 本操作是否偏离当前 todo 项目标？是 → 停止，重新对齐2. 变更文件数是否超过 3？是 → 停止，升级 lx-task-spec3. "本步重试次数是否已达 2？" 是 → 停止，升级 lx-task-spec

## 子命令路由
解析 `$ARGUMENTS` 第一个词：
| 子命令 | 动作 | 跳转 | 示例|
|--------|------|------|------|
|`add` | 捕获新 todo 项| → Step 0 | `/lx-todo add 🐛 P1 QueryTasks 空 slice 未做 len 检查`|
|`do #N` | 处理指定 todo 项 | → Step 1 | `/lx-todo do #3`|
|`next` | 处理最高优先级未完成项 | → Step 1 | `/lx-todo next`|
|`list` | 显示所有 todo 项 | → 直接输出 | `/lx-todo list`|
|`review` | 批次回顾 | → Step 5 | `/lx-todo review`|
|**无子命令** | **直接推进：执行 `next`（少即是多）** | **→ Step 1** | `/lx-todo`|
|非子命令但描述了 bug/feature | 自动识别为 `add` | → Step 0 | `/lx-todo QueryTasks 有 nil panic` |
**哲学：少，即是多**- `/lx-todo`（无参数）= 直接推进 todo 列表，等同于 `next`，不弹帮助，不问问题- 队列为空时才提示："当前无待处理任务，使用 `/lx-todo add` 添加"
**歧义处理**：无法判断子命令 → 询问用户 "你要添加还是处理？"，不猜测。

### 输入验证（Harness 模式）
当 `add` 缺少描述时，展示用途说明：

```📋 lx-todo 用途说明： 轻量开发模式：处理 ≤3 文件的 bug/小功能/重构，5 步闭环： 捕获 → 分拣 → 执行 → 验证 → 关闭 超限（>3 文件/需要设计/2 次修复失败）→ 自动升级 lx-task-spec
📖 用法：/lx-todo <子命令> [参数] 示例：/lx-todo add 🐛 P1 QueryTasks 空 slice panic 示例：/lx-todo # 直接推进（等同 next） 示例：/lx-todo do #3 # 指定处理某项 示例：/lx-todo list # 查看列表 示例：/lx-todo review # 批次回顾
```

## Todo 文件规范
→ 触发条件：`add` 且队列文件不存在时，加载 `@references/queue-format.md` 初始化格式

## 执行步骤

### Step 0 — 捕获（子命令：`add`）

解析用户输入，提取四要素：
| 要素 | 必填 | 缺失处理|
|------|------|---------|
|类型 | 是 | 从描述推断：含"bug/错误/panic/nil" → 🐛，含"添加/新增" → ✨，含"重构/拆分/优化" → 🔧，含"文档/注释" → 📝，无法推断 → 询问用户|
|优先级 | 否 | 默认 P2|
|描述 | 是 | 缺失 → 询问 "请用一句话描述要做什么"|
|来源 | 否 | 默认 `自发现` |\|
**执行**：

```bash
n
3 .claude/skills/lx-todo/scripts/todo_queue.py \ --action add --type {类型} --priority {优先级} \ --desc "{描述}" --source "{来源}"
bashpython3 .claude/skills/lx-todo/scripts/todo_queue.py \ --action add --type {类型} --priority {优先级} \ --desc "{描述}" --source "{来源}"
```
读取 JSON → 获取新建 todo 项的 id。1. 读取 `.omc/state/todo-queue.md`（不存在 → 创建初始模板）2. 分配下一个可用 ID（= 文件中最大 ID + 1）3. 追加到"待处理"区4. 写入文件
**完成标准**（全部满足才输出成功）：- ✅ todo-queue.md 文件已更新（`readFile` 验证写入内容）- ✅ 新项包含 ID + 类型 + 优先级 + 描述 + source + 日期
**输出模板**：

```✅ #[id] [类型][优先级] [描述]📋 待处理 [N] 项 · 👉 /lx-todo
✅ #[id] [类型][优先级] [描述]📋 待处理 [N] 项 · 👉 /lx-todo

```

---

### Step 1 — 分拣（30 秒决策）
**前置**：读取 todo 项 → 定位相关代码。

```bash
#
搜索关键词定位影响范围grep -rn "关键词" --include="*.go" -l | head -20

```
**工具降级**：grep 无结果 → 尝试 AST grep → 仍无结果 → 询问用户代码位置。
**决策矩阵**（严格执行，不可模糊判断）：
| 条件 | 判定 | 动作|
|------|------|------|
|影响文件 ≤3 且改动模式明确 | ✅ Todo 处理 | 更新状态为"进行中" → Step 2|
|影响文件 >3 | ❌ 升级 | → 升级 lx-task-spec|
|需要新增 API/接口/模块 | ❌ 升级 | → 升级 lx-task-spec（需要精确 AC 驱动）|
|不确定 → 花 ≤5 分钟读上下文 | 再判断 | `readFile` 相关文件 → 重新评估|
|读完仍不确定 | ❌ 升级 | → 升级协议（宁重不漏） |
**量化门禁**：影响文件数必须通过 `grep -l` 实际计数，不可目测估计。
**完成标准**（门禁格式，全部字段必填）：

```G
0
1 分拣门禁影响文件数：[N]（工具：grep -l 输出原文 → [粘贴]）判定结果：[Todo 处理 / 升级]判定依据：[引用决策矩阵中的具体行]todo-queue.md 状态：[已更新为"进行中" / 已升级]（工具：readFile 验证）
G01 分拣门禁影响文件数：[N]（工具：grep -l 输出原文 → [粘贴]）判定结果：[Todo 处理 / 升级]判定依据：[引用决策矩阵中的具体行]todo-queue.md 状态：[已更新为"进行中" / 已升级]（工具：readFile 验证）

```

---

### Step 2 — 执行（按类型分流）
**惯性断路器**（执行前自检）：> "我选择的执行路径（🐛/✨/🔧/📝）是否与 todo 项类型一致？"> 不一致 → 停止，回到 Step 1 重新分拣。
各类型执行逻辑：加载 `@references/execution-types.md`

### Step 3 — 快速验证
**验证深度矩阵**：
| 类型 | 测试范围 | 质量门禁 | 跳过条件|
|------|---------|---------|---------|
|🐛 bug | 受影响的测试 | `/lx-pre-commit` | 无，必须执行|
|✨ feat | 新功能单元测试 | `/lx-pre-commit` | 无，必须执行|
|🔧 refactor | 已有测试全跑 | `/lx-pre-commit` | 无，必须执行|
|📝 docs | 无 | 无 | **跳过本步** → Step 4 |\|
**执行序列**：

```1
. 测试执行（引用原始输出，不可描述性替代）： go test -v -run TestXxx ./affected/package
 ├─ PASS → 继续 └─ FAIL → 修复 → 重跑（计入重试次数）
2. 质量门禁： 调用 /lx-pre-commit（code-review + security + govulncheck）
 等待完成，读取结果。
```
**门禁结果处理**（严格遵循，不可自行降级；根因分析见 `@../../nodes/execute_node.md` 5-Why 法）：
| 结果 | 重试次数 | 动作|
|------|---------|------|
|通过 | - | → Step 4|
|P0/P1 auto-fix 修复 → re-scan 通过 | - | → Step 4|
|blocked | 第 1 次 | 修复 → 重新执行 Step 3|
|blocked | 第 2 次 | **必须升级 lx-task-spec**，不可第 3 次尝试 |
**关联问题捕获**：验证过程中发现的其他问题 → `readFile .omc/state/todo-queue.md` → 追加新 todo 项 → 不在本轮处理。
**完成标准**：- ✅ 测试通过（引用 `go test` 原始输出中的 PASS）- ✅ `/lx-pre-commit` 通过（引用门禁判定）- ✅ 重试次数 ≤2（记录：第 [X] 次验证）- ✅ 关联问题已捕获（如有）

---

### Step 4 — 关闭
**前置一致性检查**：> "Step 2 的修复目标 与 Step 3 的验证范围 是否一致？"> （修复了 A 但测试验证了 B → 停止，回到 Step 3 补充验证）
**执行序列**（Git 门禁遵循 `@../../nodes/behavior_rules.md` §1.4）：

```1
. 暂存变更文件（具体文件名，禁止 git add -A） git add <file1> <file2>
2. commit（需用户确认），message 格式： 🐛→fix / ✨→feat / 🔧→refactor / 📝→docs
3. 更新 .omc/state/todo-queue.md：从"进行中"→"已完成"，添加 done 日期 + files 数
```
**完成标准**：- ✅ git commit 成功（引用 git 输出）- ✅ todo-queue.md 已更新（`readFile` 验证）- ✅ 变更文件数记录准确
**输出模板**：

```✅ #[id] 完成 · 验证 ✅ · [commit hash 前7位]📋 剩余 [N] 项 · 👉 /lx-todo
✅ #[id] 完成 · 验证 ✅ · [commit hash 前7位]📋 剩余 [N] 项 · 👉 /lx-todo
```

---

### Step 5 — 批次回顾（子命令：`review`）
**触发时机**：每日收工前 或 积累 ≥5 已完成项后。
**执行**：

```1
. readFile .omc/state/todo-queue.md2. 统计各区项数3. 检查： ├─ P0/P1 待处理项是否有 >1 天未处理？→ 警告 ├─ P2/P3 是否有 >7 天过期？→ 建议降级或关闭 ├─ 已完成项是否有系统性模式？ │ （同一规则号反复出现 → 建议主分支重构） └─ 升级项是否已被主分支接收？→ 确认
1. readFile .omc/state/todo-queue.md2. 统计各区项数3. 检查： ├─ P0/P1 待处理项是否有 >1 天未处理？→ 警告 ├─ P2/P3 是否有 >7 天过期？→ 建议降级或关闭 ├─ 已完成项是否有系统性模式？ │ （同一规则号反复出现 → 建议主分支重构） └─ 升级项是否已被主分支接收？→ 确认
```
**完成标准**：- ✅ todo-queue.md 已读取，统计数据引用实际文件内容- ✅ 过期项已标注- ✅ 系统性模式已识别（如有）
**输出模板**：

```## Todo 批次回顾

### 统计| 状态 | 数量 | 明细 ||------|------|------|| 待处理 | [N] | P0:[n] P1:[n] P2:[n] P3:[n] || 进行中 | [N] | #[ids] || 今日完成 | [N] | #[ids] || 累计完成 | [N] | - || 已升级 | [N] | #[ids] |

### 告警- ⚠️ P1 项 #[id] 已待处理 [N] 天，建议尽快处理- ⚠️ P3 项 #[id] 已过期 [N] 天，建议关闭

### 模式发现[规则 H4 命中 3 次 → 建议主分支统一添加 slice 边界检查]

### 建议下一步- 👉 /lx-todo（继续处理下一个）
```

---

## 升级协议
→ 触发条件：超限（>3文件 / 2次失败），加载 `@references/upgrade-protocol.md` 执行升级流程

## 输出模板汇总
| 场景 | 模板位置 | 触发条件|
|------|---------|---------|
|捕获成功 | Step 0 输出模板 | `add` 完成|
|处理完成 | Step 4 输出模板 | `do`/`next` 全流程完成|
|批次回顾 | Step 5 输出模板 | `review`|
|升级到主分支 | 升级输出模板 | 任一升级触发点命中|
|列表展示 | 直接输出 todo-queue.md 内容 + 统计 | `list` 或无参数|
|todo 清零 | `🎉 Todo 清零！无待处理项。` | `next` 但无待处理|
|ID 不存在 | `❌ Todo #[id] 不存在。当前有效 ID：#[列表]` | `do #N` 但 N 无效|
|非 Go 项目 | `⏭️ 非 Go 项目，lx-todo 不适用。` | 无 go.mod |

## 跨 Skill 联动
| 方向 | Skill | 触发条件 | 数据契约|
|------|-------|---------|---------|
|内部调用 | `/lx-debug-spec` | Step 2 🐛 根因不明显 | 传递：todo 描述 + 相关代码位置；接收：Phase 1 定位结果 + Phase 4 修复|
|内部调用 | `/lx-golang-test` | Step 2 🔧 需补测试 | 传递：重构目标函数名 + 测试类型 unit|
|内部调用 | `/lx-pre-commit` | Step 3 质量门禁 | 传递：变更文件范围；接收：code-review + security 判定|
|上游来自 | `/lx-code-review` | 审查中 P2/P3 非阻塞项 | 接收：规则号 + file:line + 问题描述 → 自动 `add`|
|上游来自 | `/lx-security-review` | 🟢 Low 警告 | 接收：漏洞类型 + file:line → 自动 `add`|
|上游来自 | 主分支 | 技术债 / 非阻塞 bug / 规范小问题 | 接收：问题描述 + 来源步骤|
|下游传至 | `lx-task-spec` | 升级的 todo 项 | 传递：升级输出模板（含进展 + 建议入口） |

## 错误恢复与升级路径
> 根因分析统一遵循 `@../../nodes/execute_node.md`（5-Why + 降级触发矩阵），修复上限 2 轮（见 `@../../nodes/behavior_rules.md` §1.6，本 skill 更严格）。
| 场景 | 检测机制 | 回退协议 | 重入点 | 升级路径|
|------|---------|---------|--------|---------|
|Step 2 编译失败 | `go build` exit code ≠ 0 | 修复编译错误 | Step 2 重新编译 | 2 次 → 升级|
|Step 3 测试失败 | `go test` FAIL | 修复缺陷 → 重跑 | Step 3 重新测试 | 2 次 → 升级|
|Step 3 门禁 blocked | lx-pre-commit 报告 | 按报告修复 → 重跑 | Step 3 重新验证 | 2 次 → 升级|
|修复引入新问题 | re-scan 新增命中 | `git checkout -- <file>` 回退 | Step 2 重新修复 | 计入重试次数|
|todo-queue.md 损坏/缺失 | `readFile` 失败或格式异常 | 从 git history 恢复或重建 | Step 0 重新创建 | 无法恢复 → 询问用户|
|git 不可用 | `git status` 失败 | 仅执行代码变更，跳过 commit | Step 4 手动记录 | 提示用户手动 commit|
|🐛 debug 轮次耗尽 | 轮次计数 = 2 | 停止 debug | 升级协议 | 传递已收集证据 [4a] |

## 上下文保持
长 todo 处理会话中，在以下时间点保存关键发现：
| 时间点 | 保存内容|
|--------|---------|
|Step 1 完成后 | `<remember>Todo #[id] 分拣结果：[Todo处理/升级]，影响文件：[列表]</remember>`|
|Step 2 debug 失败时 | `<remember>Todo #[id] debug 第 [N] 轮失败，已排除：[假说列表]</remember>`|
|Step 3 门禁失败时 | `<remember>Todo #[id] 门禁第 [N] 次失败，blocked 项：[规则号列表]</remember>` |

## 中止条件
| 条件 | 输出|
|------|------|
|`$ARGUMENTS` 为空 | 显示 list + 帮助文本|
|`add` 无描述 | 询问 "请用一句话描述要做什么"|
|`do #N` 但 N 不存在 | `❌ Todo #N 不存在。` + 显示有效 ID|
|`next` 但待处理为空 | `🎉 Todo 清零！`|
|📝 docs 类型 | 跳过 Step 3 → 直接 Step 4|
|非 Go 项目（无 go.mod） | `⏭️ 不适用`|
|Step 2 变更超 3 文件 | 立即停止 → 升级协议|
|任一步骤重试达 2 次 | 立即停止 → 升级协议 |

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|todo_queue.py 执行失败 | 脚本操作 | 直接读写 .omc/state/todo-queue.md 文本|
|go build 失败超2次 | 修复 | 停止，升级 lx-task-spec（记录已尝试方案）|
|lx-pre-commit 不可用 | 调用 skill | 手动运行 go build && go test，记录输出|
|变更文件超过3个 | 继续 | 停止，提示升级 lx-task-spec |
