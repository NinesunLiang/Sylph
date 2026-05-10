# RPE Phase 详情 — 从 Phase 1→3 各阶段详细流程

> 被 lx-rpe/SKILL.md §新建流程 引用。SKILL.md 中仅保留阶段概要，具体流程在此。

---

## Phase 1 — Research（研究迭代循环）

**前置条件**：`prd.md` 已填充，`research.md` 已有 AI 初稿。

若 `new` 流程已生成初稿，从"用户审阅"直接开始；否则执行首次研究 Prompt。

**首次研究 Prompt**：
```
首先读取并内化治理文件（按优先级：AGENTS.md → CLAUDE.md），其中规则作为本次所有操作的最高优先级宪法。深入阅读此项目，围绕本需求做非常详细的研究。你必须经历一切关键调用链路与数据流，不接受仅函数签名级阅读。更新 research.md：调用链路、数据流、约束、风险、待确认问题、建议路径。暂时不要实施。
```

**执行序列**：
1. `readFile prd.md` → 理解需求
2. `readFile` AGENTS.md/CLAUDE.md → 内化规则
3. 深入阅读代码：grep/readFile/LSP 追踪关键调用链，读完整函数体，追踪数据流全路径
4. 更新 `research.md`：调用链路（file:line）、数据流图、约束、风险、待确认问题、建议路径
5. 输出研究摘要，等待用户审阅

**用户审阅迭代循环**：
```
循环：用户备注 → AI 逐条回应 → AI 检查完整性
  【未解答问题】→ 列出剩余问题，继续等待
  【Gate-R 通过】→ "research 已完整，进入 plan 阶段？"
用户确认 → 进入 Phase 2
```

**Gate-R**：加载 `@references/gate-checklist.md` → 自检通过后进入 Phase 2。

**完成标准**：
- ✅ research.md 完整填充（无空白骨架）
- ✅ 所有用户备注已逐条回应
- ✅ 调用链路引用实际代码（file:line）
- ✅ Gate-R 全部勾选 + 用户确认

**状态追踪**（写入 `state/progress.md`）：
```
## Phase 1 — Research
- 状态：✅ 已完成 / 🔄 迭代中（第 N 轮）
- 迭代次数：[N] · 用户确认：[是/否] · 关键发现：[摘要]
```

---

## Phase 2 — Plan（规划迭代循环）

**前置条件**：Phase 1 已确认完成。

**首次规划 Prompt**：
```
首先读取并内化治理文件（按优先级：AGENTS.md → CLAUDE.md），其中规则作为本次所有操作的最高优先级宪法。基于已批准的 research.md，更新非常详细的 plan.md。先读真实代码再规划。必须包含：任务分解、AC、测试策略、回滚方案、影响范围与非范围。暂时不要实施。
```

**执行序列**：
1. 加载 research.md → 读取真实代码 → 更新 plan.md
2. plan.md 内容：Task 列表（每个可独立验收）、AC、测试策略、回滚方案、影响范围、非范围
3. 输出规划摘要，等待用户审阅

**用户审阅迭代循环**：用户备注 → AI 回应 → Gate-P 自检 → 归纳确认

**Gate-R 附加检查**：自动调 lx-code-review（Go）或 lx-react-review（前端）评审 plan.md。P0/P1 必须修复。

**上下文锚点**（前置条件）：
```
📌 上下文锚点：
- 架构决策: [引用 ADR-NNN 或 CLAUDE.md 相关章节]
- 类似模块: [existing_file:line] 的 [模式名]
- 复用检查: [引用 lx-code-review 模式库匹配结果]
```
→ 未声明不得编码。

**Gate-X 预检**：
- [ ] 涉及 Schema/DB 变更？
- [ ] 涉及 API 契约变更？
- [ ] 涉及跨模块依赖变更？
- [ ] 涉及合规/安全敏感变更？
→ 任一为"是" → 回 Plan 二次批准，不进入 Phase 3

**完成标准**：
- ✅ plan.md 完整填充
- ✅ 每个 Task 有 AC + 测试策略 + 回滚方案
- ✅ 用户备注已回应 + Gate-P 通过 + Gate-X 无触发
- ✅ 用户确认

---

## Phase 3 — Execute（执行 → 进入主循环）

**前置条件**：Phase 2 已确认。不重复确认，直接进入。

**全程自动推进**，以下情况暂停：
- ⛔ **Gate-X 触发**：Schema/API/跨模块/合规变更 → 暂停 → 回 Phase 2 二次批准
- 🚫 **Blocker SLA**：3次不同策略失败 → 记录后询问
- 📤 **Step 6 验收**：自动验收结果 + 人工确认
- 🔴 **Step 8 git commit**：必须用户确认

**执行 Prompt**：
```
首先读取并内化治理文件（按优先级：AGENTS.md → CLAUDE.md），其中规则作为本次所有操作的最高优先级宪法。按已批准 plan.md 单步实施并逐项勾选，只允许执行"当前可执行 Task"。不得跨步、不得偏离方案。持续运行 typecheck/lint/tests。严格执行 Gate-X。遵守 Blocker SLA 与 Change Budget。不要 any；unknown 仅允许在边界并必须做类型收敛。失败必须留痕。
```

**复杂 Task sub-step 追踪**（≥3 子操作时）：
```
- [ ] N.1 {子操作} → AC → Rollback: {git restore / 删除 / 无}
- [ ] N.2 ...
```
完成一个立即标 `[x]`，禁止批量回标。

**Phase 3 → 主循环衔接**：
```
1. 读取 plan.md → 提取 Task 列表 → 写入 state/progress.md
2. → 进入主循环 Step 1（首个 Task）
3. 每个 Task 完成 Step [3]~[9] 后：
   → 更新 executor.md（Evidence + 回滚演练记录）
   → 更新 progress.md（状态）
```

**Blocker SLA（三态熔断）**：
| 状态 | 触发 | 处理 |
|------|------|------|
| Closed | 正常执行 | 继续 |
| Open | 同一阻塞超 2 次修复失败 | 标 BLOCKED + 通知用户 |
| Half-Open | 用户提供新信息后 | 单次试探 → 成功恢复 / 失败维持 Open + 回 Plan |

**完成标准**：
- ✅ 所有任务项已完成（`- [ ]` 全清）
- ✅ Gate-E 全部勾选 · executor.md Evidence 完整
- ✅ 所有 Blocker 已解决或获接受
