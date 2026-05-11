---
name: lx-task-spec
version: v5.1.0
harness_version: ">=1.1.0"
model: sonnet
description: 任务驱动机制（task_spec）：lx-todo 的升级目标，处理需要精确 AC 驱动但不需要完整 PRD 的中等复杂任务。引导式问答（3问）→ 结构化任务输入 → 澄清 → 规划 → 执行 → 验收。
complexity: intermediate
when_to_use: "Use when a task requires precise acceptance criteria but not a full PRD (mid-complexity); when lx-todo exceeds its limit (>3 files or 2 failures) and upgrades to task-spec; when user says '/lx-task-spec' with a task description."
role: "Task specification engine — structured task decomposition and execution"
execution_mode: stepwise
triggers:
  - "/lx-task-spec"
---

# lx-task-spec - 任务驱动机制
> 内在机制，按需触发。不触发时不加载任何 task_spec 相关文件。

## 原子化声明
> 本 skill 是 task_spec 参考实现，直接使用 task_sys/ 和 nodes/ 组件。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 引导式问答收集任务信息|
|target_resolver | `../../nodes/target_resolver.md` | 解析任务目标文件/范围|
|context_collector | `../../nodes/context_collector.md` | 收集项目上下文|
|generator | `../../nodes/generator.md` | 技术方案/验收标准生成|
|execute_node | `../../nodes/execute_node.md` | 执行改动|
|verifier | `../../nodes/verifier.md` | 验证执行结果|
|report_generator | `../../nodes/report_generator.md` | 生成验收报告|
|behavior_rules | `../../nodes/behavior_rules.md` | 行为约束 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|task_input | `../../schemas/input/task_input.yaml` | 结构化任务输入|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 任务目标定义|
|finding | `../../schemas/atomic/finding.yaml` | 执行发现的问题|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|orchestrator | `../../task_sys/orchestrator.md` | 状态机定义|
|loading_matrix | `../../task_sys/loading_matrix.md` | 加载映射|
|unified_delivery_schema | `../../task_sys/unified_delivery_schema.md` | 交付格式|
|context_guard | `../../task_sys/context_guard.md` | 上下文守卫 |

### 状态机
本 skill **就是 orchestrator 的直接入口**，引用 `.claude/task_sys/orchestrator.md` 定义的状态机。
**核心状态映射**: need_clarification → executing → [clarify → plan → execute → verify] → done
**执行模式**：- `stepwise`（默认）：逐步执行，每步确认后进入下一步- `race`：规划完成后并行执行独立子任务（后端由 lx-race 实现 — 注册→派发→收集→报告）

### 私有节点
本 skill 无私有节点。

## 触发条件与路由
**哲学：少，即是多**
| 输入 | 语义 | 行为|
|------|------|------|
|`/lx-task-spec`（无参数）| 继续当前 task-spec 工作 | 检测活跃任务 → 直接恢复，不过场|
|从 lx-todo 升级而来 | lx-todo 超限（>3文件/2次失败）触发 | 携带 lx-todo 上下文（已收集证据+排除假说）直接进入规划|
|`/lx-task-spec <描述>` | 创建新任务 | → 5 问引导|
|发送结构化 `task_input` YAML | 创建新任务（快速） | → 直接进入规划 |
**无参数时的恢复逻辑**：1. 检查 `.omc/state/` 是否有活跃 task-spec 状态2. 有 → 输出当前进度摘要 + 直接恢复执行，不打断3. 无 → 提示："当前无活跃任务，使用 `/lx-task-spec <描述>` 创建新任务"
以下情况也触发本 skill：- 用户说"启动 task_spec" / "用 task_spec 处理 XXX"（有任务描述 → 视为有参数）- lx-todo 升级（超限自动跳转，携带 todo 上下文）
**三种模式边界**：
| 模式 | 适用场景 | 升级方向|
|------|---------|---------|
|lx-todo | 零散小任务（≤3文件，快速闭环） | → lx-task-spec|
|lx-task-spec | 中等复杂（需精确 AC，>3文件或需设计）| → lx-rpe（如需完整 PRD）|
|lx-rpe | 大特性（有 PRD，完整 Research→Plan→Execute）| — |

## 触发后加载流程
触发后按顺序加载（仅加载当前阶段需要的文件）：
1. 加载 `@../../task_sys/loading_matrix.md` → 了解加载映射2. 加载 `@../../task_sys/orchestrator.md` → 启动状态机3. 根据 Orchestrator 路由结果，按需加载对应节点

## 引导式交互流程（有参数时）

---
用户输入 `/lx-task-spec` 后，AI **逐个问题引导**，每次只问一个：

### 第 1 问：任务名称

```📋 任务驱动模式已启动。
问题 1/3：任务名称是什么？（简短描述，如 "add-login-api"、"fix-memory-leak"）
```

### 第 2 问：任务目标

```问
题
2/3：要做什么？（描述具体需求，如 "在用户模块新增登录接口，支持手机号+验证码"）

```

### 第 3 问：验收标准

```问
题
3/3：如何验证任务完成？（描述可观测的验收标准，如 "1. 接口返回 200 2. 单元测试通过 3. 文档更新"）不确定？直接说"帮我生成"

```

**用户说"帮我生成" / "不确定" / 空回车** → AI 根据 Q1+Q2 立即生成 AC 草稿：

```基于你的任务目
标
，建议以下验收标准：
AC-1 [功能]：{核心功能可正常调用} 验证：{具体命令或操作} 期望：{预期结果}
AC-2 [测试]：{单元/集成测试通过} 验证：{测试命令} 期望：PASS
AC-3 [边界]：{关键边界场景}（如有） 验证：{边界验证方式} 期望：{期望行为}
这样可以吗？（回车确认 / 补充修改）
```
生成规则：- AC-1 对应 Q2 描述的核心功能（必有）- AC-2 对应测试验证（必有，类型按项目类型：Go→go test / 前端→npm test）- AC-3 对应 Q2 中能识别的边界场景（可选，识别不到则省略）- 所有 AC 必须可观测、可执行，不接受"代码合理"这类主观描述
> >
> 3 问收集完毕后直接开始。执行模式默认 stepwise，优先级默认 p1。
> 需要调整可在执行中说：「用 race 模式」或「这是 p0」

### 收集完成后
AI 自动生成完整的 `task_input` YAML 并展示：

```yam
l
✅ 任务信息已收集：
task_input: task_name: "add-login-api" target: "在用户模块新增登录接口，支持手机号 + 验证码" pass_criteria: - id: "AC-1" type: test description: "接口返回 200" how_to_check: "curl -X POST /api/login | jq .status" expected: "200" - id: "AC-2" type: test description: "单元测试通过" how_to_check: "go test ./pkg/user/..." expected: "PASS" - id: "AC-3" type: doc description: "API 文档更新" how_to_check: "grep -c 'login' docs/api.md" expected: "≥ 1" executor_mode: stepwise # 默认，可说「用 race 模式」调整 priority: p1 repo_root: "."
确认无误后开始执行？（回复"开始"或指出需要修改的地方）
```
用户确认后进入 **规划 → 执行 → 验收** 流程。

## 执行模式详解

### stepwise（逐步模式）

```规
划
→ 子任务 1 → 验证 → 子任务 2 → 验证 → ... → 最终验收

```
- 每个子任务完成后立即验证- 验证失败则修复后重新验证- 适合：有依赖关系的任务、复杂架构变更

### race（并行模式 — 后端 lx-race）

```
规划
→ [lx-race 注册: 子任务 1, 子任务 2, 子任务 3] → 并行派发 → 收集 → 合并 → 最终验收
```

- 规划阶段识别独立子任务
- 调用 `race_manager.sh register` 注册子任务
- 并行派发所有独立子任务（Claude Code: Task() / 其他平台: run_in_background）
- Worker 写文件时 OMA Lock 自动防护并发冲突
- 全部完成后 `race_manager.sh report` 聚合结果
- 适合：多文件独立变更、无依赖的批量修复

## 向后兼容：直接发送 YAML
如果用户直接发送完整的 `task_input` YAML，跳过引导流程，直接进入澄清/规划阶段。

## 节点路由速查
| 阶段 | 加载文件 | 说明|
|---------- | ---------------------------------------------------------------------------- | -------------------|
|引导收集 | `.claude/nodes/interactive_prompt.md` | 5 问引导式收集|
|目标解析 | `.claude/nodes/target_resolver.md` | 解析目标文件/范围|
|上下文收集 | `.claude/nodes/context_collector.md` | 收集项目上下文|
|规划 | `.claude/nodes/generator.md` + `.claude/task_sys/unified_delivery_schema.md` | 制定计划|
|执行 | `.claude/nodes/execute_node.md` | 实施改动|
|验证 | `.claude/nodes/verifier.md` | 验证执行结果|
|报告 | `.claude/nodes/report_generator.md` | 生成验收报告|
|行为约束 | `.claude/nodes/behavior_rules.md` | 研究/执行阶段需要时|
|上下文守卫 | `.claude/task_sys/context_guard.md` | 上下文 >40% 时 |\|

## 路径语义规则
| 方式 | 示例 | 行为 | 是否加载内容|
|------------ | ---------------------------------- | ------------------------ | ------------|
|**普通路径** | `.claude/task_sys/orchestrator.md` | 仅作文本描述，不读取 | ❌ **否**|
|**@引用** | `@.claude/kernel.md` | 触发文件读取，注入上下文 | ✅ **是** |\|
**task_spec 渐进式披露规则**：
- `AGENTS.md` / `CLAUDE.md` 中 task_spec 相关的普通路径只是索引，不会自动触发加载。- 只有明确触发本 skill 后才开始加载。- 触发本 skill 后，按 `loading_matrix.md` 的映射表，**仅加载当前阶段需要的文件**。

## 状态机

```js引导
收
集
→ need_clarification → ready → planning → executing → done ↑ ↑ ↑ ↑ └────── blocked ────────┘ └─ fallback ┘ ↓ need_clarification

```

## 版本历史
| 版本 | 日期 | 变更摘要|
|------|------|---------|
|v1.0 | 2026-04-17 | 初始版本：5问引导 + orchestrator 状态机 + stepwise/race 双模式|
|v1.1 | 2026-04-24 | 5问→3问（去掉执行模式/优先级，默认 stepwise+p1）；Q3 加 AI 自动生成 AC 草稿|
|v1.2 | 2026-04-24 | 无参数=继续当前 task-spec（少即是多）；明确作为 lx-todo 升级目标；补三模式边界说明 |

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|orchestrator 加载失败 | 状态机驱动 | 直接执行 3 问引导，跳过状态机|
|无活跃任务（无参数时）| 恢复任务 | 提示"当前无活跃任务，用 /lx-task-spec <描述> 创建"|
|AC 无法自动生成 | Q3 AI草稿 | 提供 AC 模板让用户填写 |


