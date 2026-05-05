# Loading Matrix - 渐进式披露加载映射表

>
> 定义"什么阶段加载什么文件"，确保按需加载，避免上下文膨胀
> 版本：v5.1.0

---

## 加载层级

| 层级 | 名称 | 加载时机 | 最大行数|
|------|------|---------|---------|
|**L1** | 会话启动 | 始终 | \~120 行|
|**L2** | 阶段加载 | 进入特定阶段时 | 按需|
|**L3** | 精确加载 | 执行具体操作时 | 按需 |

---

## L1：会话启动（始终加载）

| 文件 | 行数 | 内容|
|------|------|------|
|`AGENTS.md` / `CLAUDE.md` | \~120 | Project 宪法 + 6 条铁律 + 外置路径索引（AGENTS.md 优先，CLAUDE.md 为 @-include 跳板）|
**目标**：首次加载 ≤120 行，仅包含高层约束和索引。

---

## L2：阶段加载（按需触发）

| 阶段 | 触发条件 | 加载文件 | 说明|
|------|---------|---------|------|
|**研究阶段** | 需要行为准则（防编造/证据门禁/Git 门禁等） | `@../nodes/behavior_rules.md` | 行为约束规则|
|**任务驱动** | 用户触发 `/lx-task-spec` | `@../task_sys/orchestrator.md`<br>`@../task_sys/unified_delivery_schema.md` | 状态机 + 输出格式|
|**执行阶段** | 需要实施改动 | `@../nodes/execute_node.md` | 5-Why 根因 + 执行|
|**验证阶段** | 执行完成，需要验证 | `@../nodes/verifier.md` | re-scan 验证|
|**报告阶段** | 需要生成报告 | `@../nodes/report_generator.md` | 结构化报告 |

### 节点路由表

| 节点文件 | 何时加载|
|---------|---------|
|`interactive_prompt.md` | 引导式问答收集信息|
|`target_resolver.md` | 解析目标文件/范围|
|`context_collector.md` | 收集项目上下文|
|`scanner.md` | 按规则集扫描代码|
|`auto_fixer.md` | P0/P1 自动修复|
|`verifier.md` | 修复后验证|
|`generator.md` | 生成代码/文档/方案|
|`execute_node.md` | 执行改动（含根因分析）|
|`gate_checker.md` | Gate 判定|
|`report_generator.md` | 生成报告|
|`behavior_rules.md` | 行为约束（研究/执行阶段）|
|`orchestrator.md` | 状态机参考（设计新 skill 时） |

---

## L3：精确加载（操作触发）

| 操作 | 触发条件 | 加载文件 | 说明|
|------|---------|---------|------|
|**创建任务文件** | 需要创建模板文件 | `@../task_sys/templates/{模板}.md` | 8 种模板|
|**修改代码** | 需要编码规范 | `@../kernel.md`（对应章节） | 架构铁律/命名/错误处理/测试|
|**上下文 >40%** | 触发总结 | `@../task_sys/context_guard.md` | 上下文守卫流程|
|**回归测试** | 修改治理文件后 | `@../task_sys/mechanism_evals.md` | 机制评估 |

---

## 加载规则

1. **L1 必须始终加载**：CLAUDE.md 是入口，不可跳过
2. **L2 按需加载**：进入对应阶段时才 Read，不要预加载
3. **L3 精确加载**：只加载当前操作需要的部分，不要全量 Read
4. **@引用优先**：文本中出现 `@path` 时，必须先 Read 该文件
5. **禁止越级加载**：L1 阶段不要预加载 L2/L3 内容

### @ 引用 vs 普通路径（核心规则）

| 语法 | 示例 | 行为 | 是否加载内容 | 适用场景|
|------|------|------|-------------|---------|
|**@引用** | `@.claude/task_sys/orchestrator.md` | 触发文件读取，注入上下文 | ✅ **是** | 必须读取规则/模板/节点时|
|**普通路径** | `.claude/task_sys/orchestrator.md` | 仅作文本描述，不读取 | ❌ **否** | 提及文件位置/索引时 |
**渐进式披露执行策略**：
- CLAUDE.md 中的 `@` 引用是**索引**，仅在触发 skill 或进入对应阶段时才执行读取。
- 未触发 skill 时，CLAUDE.md 保持轻量，**不加载**任何 L2/L3 文件。
- 触发 skill 后，按本映射表，**仅加载当前阶段需要的文件**。

---

## 当前架构统计

| 层级 | 文件数 | 总行数 | 首次加载行数|
|------|--------|--------|-------------|
|L1 | 1 | ~120 | ~120|
|L2 | 12 | ~800 | 0（按需）|
|L3 | 8 | ~300 | 0（按需）|
|**总计** | **21** | **~1220** | **~120** |
**首次加载从 394 行 → \~120 行，减少 70%。**

---

## 已删除节点（v5.0.0 Oracle 评审精简）

| 原节点 | 删除理由 | 替代方案|
|--------|---------|---------|
|`plan_node.md` | 0 引用，规划逻辑内联到 skill | generator.md|
|`a0_clarifier.md` | 0 引用，澄清合并到 interactive_prompt | interactive_prompt.md|
|`spec_generator.md` | 0 引用，generator.md 已覆盖 | generator.md|
|`fallback_exploration.md` | 0 引用，降级触发在 execute_node 中 | execute_node.md|
|`fallback_framework.md` | 0 引用，同上 | execute_node.md|
|`judge.md` | 0 引用，verdict schema 已定义判定结构 | report_generator.md |
