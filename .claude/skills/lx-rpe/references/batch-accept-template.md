## 批量验收报告 — {date}

### 待验收任务| Task | 功能描述 | 编译 | 测试 | pre-commit | AC 覆盖 | 判定 ||------|---------|------|------|-----------|---------|------|| RPE-005 | GetTagDetail API | ✅ | ✅ 12/12 | ✅ P0=0 | 4/4 AC | ✅ 建议通过 || RPE-006 | TagAnalysis 聚合 | ✅ | ❌ 9/12 | ✅ P0=0 | 3/4 AC | ⚠️ 部分通过 || RPE-007 | BatchTagExport | ✅ | ⏭️ 无测试 | ⚠️ 测试缺口 | 0/3 AC | ❌ 测试不足 |

### 失败明细#### RPE-006 部分通过- 未通过 AC: AC-03（边界场景: 空标签列表）- 失败原因: 返回 nil 而非空切片- 修复建议: 统一返回 []而非 nil

#### RPE-007 测试不足- 变更包: pkg/executor（无 *_test.go）- 建议: 补测试（/lx-golang-test 或 /lx-frontend-test）

### 验收建议- ✅ 可通过: RPE-005- ⚠️ 需修复: RPE-006（预计 5min）- ❌ 需补测: RPE-007（预计 15min）
👉 操作: • 确认通过: "验收通过 RPE-005" • 修复后重验: "/lx-rpe batch-accept"（修复后重新运行）

```
**验收规则**：
| 条件 | 判定 | 动作|
|------|------|------|
|编译 ✅ + 测试 ✅ + pre-commit ✅ + AC 全覆盖 | ✅ 建议通过 | 列入通过清单|
|编译 ✅ + 测试部分通过 + AC 部分覆盖 | ⚠️ 部分通过 | 列出未通过 AC + 修复建议|
|编译 ❌ 或 测试全失败 | ❌ 不通过 | 列失败原因 + 修复入口|
|无测试 + 无预提交门禁通过 | ❌ 测试不足 | 建议补测试（Go: /lx-golang-test / 前端: /lx-frontend-test ） |
**完成标准**：- ✅ 所有候选任务项已执行编译 + 测试 + 门禁验证- ✅ 每个任务项有明确判定（✅/⚠️/❌）- ✅ 未通过项有具体失败原因 + 修复建议- ✅ 报告输出后等待用户确认，不自动标记通过

---

### 新建流程（`new`）

#### 0. 初始化目录与文件

```1
. 解析输入，支持两种方式：
 方式 A（一行带入，推荐）： /lx-rpe new user-login 用户手机号登录，JWT，涉及 users 表 → feature_name = "user-login"，其余文字作为需求描述 → AI 直接生成 prd.md，无需逐问，跳到步骤 3
 方式 B（逐步引导）： /lx-rpe new # 只有 new，无其他参数 → AI 问：特性名称是什么？ → 再问：用一句话描述这个特性要做什么？ → 若描述够清晰 → 直接生成 prd.md → 若描述模糊 → 补问最多 2 个关键问题（问题/约束/标准中最不清楚的） → 写入 prd.md
 方式 C（已有 prd.md）： → 用户已有 prd.md → 直接跳到步骤 3
3. 创建目录结构： rpe/{feature_name}/ ├── prd.md # 已填充（引导式收集 或 用户提供） ├── research.md # AI 自动从 prd.md 生成初稿（见下方） ├── plan.md # 计划文档（Phase 2 AI 生成） ├── executor.md # 执行记录（Phase 3 AI 逐步更新） └── state/ ├── progress.md # 进度追踪文件 └── evidence/ # Evidence 存放目录
4. 【自动生成 research.md 草稿】 AI 读取 prd.md → 基于需求扫描代码库 → 写入 research.md 初稿： - 关键调用链路（grep + readFile 追踪，带 file:line） - 数据流路径（从入口到存储到返回） - 潜在风险点（依赖/并发/边界） - 待确认问题（模糊假设列表） - 初步实现路径建议 → 输出"AI 初稿已就绪，请审阅并补充"
5. 初始化其余文件： plan.md → 骨架模板 executor.md → 骨架模板 state/progress.md → 初始化进度模板
6. 输出初始化摘要

```
**输出模板**：
```✅ RPE 特性已初始化：{feature_name}
📁 目录：rpe/{feature_name}/📄 文件： - prd.md → ✅ 已填充（{N} 行） - research.md → ✅ AI 初稿已生成（关键调用链 + 风险点 + 待确认问题） - plan.md → 骨架就位，待 Phase 2 规划 - executor.md → 骨架就位，待 Phase 3 执行 - state/ → 状态追踪
👉 下一步：审阅 research.md，添加备注后输入 /lx-rpe {feature_name} 进入 Phase 1 Research 迭代

```
#### Phase 1 — Research（研究迭代循环）
**前置条件**：`rpe/{feature_name}/prd.md` 已填充（引导式收集或用户提供），`research.md` 已有 AI 初稿。
> > 若 `new` 流程已生成 research.md 初稿，Phase 1 从"用户审阅迭代"直接开始，跳过首次研究 Prompt。
> 若直接进入 Phase 1（无初稿），则执行首次研究 Prompt。
**首次研究 Prompt**（无 research 初稿时执行）：
```首先读取并内化治理文
件
（按优先级：AGENTS.md → CLAUDE.md，取先存在的），其中规则作为本次所有操作的最高优先级宪法。深入阅读此项目，围绕本需求做非常详细的研究。你必须经历一切关键调用链路与数据流，不接受仅函数签名级阅读。更新 rpe/{feature_name}/research.md：调用链路、数据流、约束、风险、待确认问题、建议路径。暂时不要实施。
首先读取并内化治理文件（按优先级：AGENTS.md → CLAUDE.md，取先存在的），其中规则作为本次所有操作的最高优先级宪法。深入阅读此项目，围绕本需求做非常详细的研究。你必须经历一切关键调用链路与数据流，不接受仅函数签名级阅读。更新 rpe/{feature_name}/research.md：调用链路、数据流、约束、风险、待确认问题、建议路径。暂时不要实施。

```

**执行序列**：
```1
. readFile rpe/{feature_name}/prd.md → 理解需求2. readFile AGENTS.md（若存在）或 readFile CLAUDE.md（若存在）→ 内化规则（AGENTS.md 优先）3. 深入阅读项目代码： - grep / readFile / LSP 追踪关键调用链路 - 不接受仅函数签名级阅读，必须读完整函数体 - 追踪数据流全路径（入口 → 处理 → 存储 → 返回）4. 更新 rpe/{feature_name}/research.md： - 调用链路（含 file:line 引用） - 数据流图 - 约束条件 - 风险识别 - 待确认问题 - 建议实现路径5. 输出研究摘要，等待用户审阅
1. readFile rpe/{feature_name}/prd.md → 理解需求2. readFile AGENTS.md（若存在）或 readFile CLAUDE.md（若存在）→ 内化规则（AGENTS.md 优先）3. 深入阅读项目代码： - grep / readFile / LSP 追踪关键调用链路 - 不接受仅函数签名级阅读，必须读完整函数体 - 追踪数据流全路径（入口 → 处理 → 存储 → 返回）4. 更新 rpe/{feature_name}/research.md： - 调用链路（含 file:line 引用） - 数据流图 - 约束条件 - 风险识别 - 待确认问题 - 建议实现路径5. 输出研究摘要，等待用户审阅

```

**用户审阅迭代循环（AI 主动判断完整性）**：
```循
环
： 用户在 research.md 中添加备注/修改 → 用户触发继续（输入任意指令或 /lx-rpe） → AI 逐条回应备注，更新 research.md → AI 主动检查完整性：
 【有未解答问题】→ 列出剩余问题，继续等待： "还有 N 个问题待确认： · {问题1} · {问题2}"
 【所有问题已解答，Gate-R 自检通过】→ AI 主动推进： "research 已完整，进入 plan 阶段？ （回车确认 / 说说还有什么补充）"
 用户回车 → 进入 Phase 2 用户有补充 → 继续迭代

```
> **不需要用户说"好了"**——AI 判断完整后主动提出，用户只需确认。
**Gate-R 检查（Phase 1 退出门禁，强制）**：加载 `@scripts/../references/gate-checklist.md` → 逐项自检 Gate-R，全部通过后方可进入 Phase 2。- [ ] 链路完整且可解释（来源已标注，非纯推断）- [ ] 约束完整（技术/业务/合规三类均已评估）- [ ] 风险可解释并有缓解（含触发条件）- [ ] 未决问题已处理或阻断已标注- [ ] 待验证假设含证伪处置规则- [ ] （Handover）进度快照已核实
**Phase 1 完成标准**：- ✅ research.md 已完整填充（无空白骨架段落）- ✅ 所有用户备注已逐条回应- ✅ 调用链路引用了实际代码（file:line）- ✅ Gate-R 全部勾选- ✅ 用户明确确认 research 完成
**Phase 1 状态追踪**（写入 `state/progress.md`）：
```##
Phase 1 — Research- 状态：✅ 已完成 / 🔄 迭代中（第 N 轮）- 迭代次数：[N]- 用户确认：[是/否]- 关键发现：[摘要]

```

#### Phase 2 — Plan（规划迭代循环）
**前置条件**：Phase 1 Research 已完成，用户已确认。
**首次规划 Prompt**（AI 执行）：
```首先读取并内化治理文
件
（按优先级：AGENTS.md → CLAUDE.md，取先存在的），其中规则作为本次所有操作的最高优先级宪法。基于已批准的 research.md，更新非常详细的 plan.md。先读真实代码再规划。必须包含：任务分解、验收标准（AC）、测试策略、回滚方案、影响范围与非范围。暂时不要实施。
首先读取并内化治理文件（按优先级：AGENTS.md → CLAUDE.md，取先存在的），其中规则作为本次所有操作的最高优先级宪法。基于已批准的 research.md，更新非常详细的 plan.md。先读真实代码再规划。必须包含：任务分解、验收标准（AC）、测试策略、回滚方案、影响范围与非范围。暂时不要实施。

```

**执行序列**：
```1
. readFile rpe/{feature_name}/research.md → 加载研究成果2. readFile AGENTS.md（若存在）或 readFile CLAUDE.md（若存在）→ 内化规则（AGENTS.md 优先）3. 读取真实代码（research 中标记的关键文件）4. 更新 rpe/{feature_name}/plan.md： - 任务分解（Task 列表，每个 Task 可独立验收） - 每个 Task 的验收标准（AC） - 测试策略（单元/接口/集成，映射到具体 Task） - 回滚方案（每个 Task 的回滚动作） - 影响范围（明确列出受影响文件） - 非范围（明确列出不做的事）5. 输出规划摘要，等待用户审阅
1. readFile rpe/{feature_name}/research.md → 加载研究成果2. readFile AGENTS.md（若存在）或 readFile CLAUDE.md（若存在）→ 内化规则（AGENTS.md 优先）3. 读取真实代码（research 中标记的关键文件）4. 更新 rpe/{feature_name}/plan.md： - 任务分解（Task 列表，每个 Task 可独立验收） - 每个 Task 的验收标准（AC） - 测试策略（单元/接口/集成，映射到具体 Task） - 回滚方案（每个 Task 的回滚动作） - 影响范围（明确列出受影响文件） - 非范围（明确列出不做的事）5. 输出规划摘要，等待用户审阅

```

**用户审阅迭代循环（AI 主动归纳并请确认）**：
```循
环
： 用户在 plan.md 中添加备注/修改 → 用户触发继续 → AI 逐条回应备注，更新 plan.md → AI 主动检查 Gate-P 自检：
 【有未完成项（AC 不清晰 / 回滚方案缺失 / 未解答问题）】 → 列出缺口，继续迭代
 【Gate-P 全部通过】→ AI 主动归纳并请确认： "plan.md 已完整，共 N 个 Task： · RPE-001 {描述}（{预估影响 N 文件}） · RPE-002 {描述} · RPE-003 {描述}
 确认启动执行？（回车开始 / 说说还有什么调整）"
 用户回车 → 进入 Phase 3 启动确认（已有一次，合并，直接执行） 用户有调整 → 继续迭代

```
> **不需要用户说"开始执行"**——AI 归纳完毕后主动请确认，用户回车即可。
**Gate-P 检查（Phase 2 退出门禁，强审批）**：- [ ] 任务分解完整- [ ] AC 可验证（三段式：步骤/成功/失败）- [ ] 测试可执行（工具和命令已指定）- [ ] 回滚可执行（步骤清晰，触发条件量化）- [ ] DOD 明确且可检查- [ ] 用户显式批准（yes）
**Gate-R 附加检查（Phase 2 方案自评，按项目类型路由）**：Plan 通过后、进入 Phase 3 前，**必须**自动调用代码审查评审方案文档：
**Go 项目**：
```→ 自动调用 lx-code-review 评审 plan.md→ 重点检查: 1. 是否列出 ≥2 个备选方案及优缺点 2. 是否引用现有类似模块路径（file:line） 3. 是否检查反模式（循环查询、大 struct 值传递、无超时保护等） 4. 是否与现有架构一致（Handler→Logic→Model 分层）→ P0/P1 必须修复后才能进入 Phase 3
→ 自动调用 lx-code-review 评审 plan.md→ 重点检查: 1. 是否列出 ≥2 个备选方案及优缺点 2. 是否引用现有类似模块路径（file:line） 3. 是否检查反模式（循环查询、大 struct 值传递、无超时保护等） 4. 是否与现有架构一致（Handler→Logic→Model 分层）→ P0/P1 必须修复后才能进入 Phase 3

```

**前端项目**：
```→ 自动调用 lx-react-review 评审 plan.md→ 重点检查: 1. 是否列出 ≥2 个备选方案及优缺点 2. 是否引用现有类似组件/Hook 路径（file:line） 3. 是否检查反模式（useEffect 无限循环、组件内定义组件、过深 prop drilling 等） 4. 是否与现有架构一致（Pages→Components→Hooks→Services 分层）→ P0/P1 必须修复后才能进入 Phase 3
→ 自动调用 lx-react-review 评审 plan.md→ 重点检查: 1. 是否列出 ≥2 个备选方案及优缺点 2. 是否引用现有类似组件/Hook 路径（file:line） 3. 是否检查反模式（useEffect 无限循环、组件内定义组件、过深 prop drilling 等） 4. 是否与现有架构一致（Pages→Components→Hooks→Services 分层）→ P0/P1 必须修复后才能进入 Phase 3

```

**上下文锚点（实现前强制）**：进入 Phase 3 每个 Task 编码前，**必须**显式声明：
```📌 上下文锚点：- 架构决策: [引用 ADR-NNN 或 CLAUDE.md 相关章节]- 类似模块: [existing_file:line] 的 [模式名]- 复用检查: [引用 lx-code-review 模式库匹配结果]
📌 上下文锚点：- 架构决策: [引用 ADR-NNN 或 CLAUDE.md 相关章节]- 类似模块: [existing_file:line] 的 [模式名]- 复用检查: [引用 lx-code-review 模式库匹配结果]

```
→ 未声明不得编码，宁 BLOCKED 不可跳过
**Gate-X 预检（进入执行前，强制）**：- [ ] 是否涉及 Schema/DB 变更- [ ] 是否涉及 API 契约变更- [ ] 是否涉及跨模块依赖变更- [ ] 是否涉及合规/安全敏感变更→ 任一为"是" → 回 Plan 二次批准，不进入 Phase 3
**Phase 2 完成标准**：- ✅ plan.md 已完整填充（无空白骨架段落）- ✅ 每个 Task 有明确的 AC + 测试策略 + 回滚方案- ✅ 所有用户备注已逐条回应- ✅ Gate-P 全部勾选 + 用户显式批准- ✅ Gate-X 预检全部为"否"（或二次批准已通过）- ✅ 用户明确确认 plan 完成
**Phase 2 状态追踪**（写入 `state/progress.md`）：
```##
Phase 2 — Plan- 状态：✅ 已完成 / 🔄 迭代中（第 N 轮）- 迭代次数：[N]- 用户确认：[是/否]- Task 数量：[N]- 预估影响文件：[N]

```

#### Phase 3 — Execute（执行 → 进入主循环）
**前置条件**：Phase 2 Plan 已完成，用户已确认。
**启动（Phase 2 确认已包含，直接进入）**：
> > Phase 2 迭代完成时 AI 已归纳 Task 列表并获得用户确认，此处直接进入执行。
> 无需再次确认，减少重复操作。
进入主循环后**全程自动推进**，以下情况才暂停通知用户：- ⛔ **Gate-X 触发**（发现 Schema/API/跨模块变更，需二次批准）- 🚫 **Blocker SLA**（3次不同策略仍失败，记录后询问）- 📤 **Step 6 验收**（自动验收结果 + 人工确认）- 🔴 **Step 8 git commit**（必须用户确认）
**执行 Prompt**（AI 执行）：
```首先读取并内化治理文
件
（按优先级：AGENTS.md → CLAUDE.md，取先存在的），其中规则作为本次所有操作的最高优先级宪法。按已批准 plan.md 单步实施并逐项勾选，只允许执行"当前可执行 Task"。不得跨步、不得偏离方案。持续运行 typecheck/lint/tests。严格执行 Gate-X：若出现 Schema/API/跨模块/合规变更，立即暂停并回到 Plan 二次批准。遵守 Blocker SLA（三态熔断）与 Change Budget；超时或超预算必须记录并暂停。不要添加不必要注释或 jsdoc，不要使用 any；unknown 仅允许在边界并必须做类型收敛。失败必须留痕（原因/证据/修正建议/是否回滚/回滚动作）。
首先读取并内化治理文件（按优先级：AGENTS.md → CLAUDE.md，取先存在的），其中规则作为本次所有操作的最高优先级宪法。按已批准 plan.md 单步实施并逐项勾选，只允许执行"当前可执行 Task"。不得跨步、不得偏离方案。持续运行 typecheck/lint/tests。严格执行 Gate-X：若出现 Schema/API/跨模块/合规变更，立即暂停并回到 Plan 二次批准。遵守 Blocker SLA（三态熔断）与 Change Budget；超时或超预算必须记录并暂停。不要添加不必要注释或 jsdoc，不要使用 any；unknown 仅允许在边界并必须做类型收敛。失败必须留痕（原因/证据/修正建议/是否回滚/回滚动作）。

```

**复杂 Task sub-step 追踪**（Task 涉及 ≥3 个独立子操作时启用）：在 Step 2 设计阶段输出 sub-step 列表，执行时逐步标记：
```- [ ] N.1 {子操作} → AC → Rollback: {git restore path / 删除新建文件 / 无}- [ ] N.2 {子操作} → AC → Rollback: {撤销动作}
- [ ] N.1 {子操作} → AC → Rollback: {git restore path / 删除新建文件 / 无}- [ ] N.2 {子操作} → AC → Rollback: {撤销动作}

```
完成一个立即标 `[x]`，禁止批量回标。
**每个 Task 完成后**（AI 执行）：
```更
新
executor.md，给出可复现 Evidence（typecheck/lint/tests/手工验证）。补充回滚演练记录。未通过 Gate-E 不得标记整体完成。

```

**Phase 3 与主循环的衔接**：
```Pha
s
e 3 将 plan.md 中的 Task 列表作为 RPE 任务项注入主循环。
1. 读取 plan.md → 提取 Task 列表2. 将 Task 映射为 RPE-001, RPE-002, ... 写入 state/progress.md3. → 进入主循环 Step 1（首个 Task）
主循环中每个 Task 完成 Step [3]\~[9] 后： → 更新 executor.md（Evidence + 回滚演练记录） → 更新 state/progress.md（Task 状态）
Gate-X 检查（每个 Task 执行前）： 若当前 Task 涉及 Schema/API/跨模块/合规变更 → 立即暂停主循环 → 回到 Phase 2 对该 Task 做二次 Plan 批准 → 批准后重新进入主循环

```
**Phase 3 完成标准**：- ✅ 所有 RPE 任务项已完成（state/progress.md 中无 `- [ ]` 项）- ✅ Gate-E 全部勾选- ✅ executor.md Evidence 完整- ✅ 所有 Blocker 已解决或已获接受
**Gate-E 检查（全部 Task 完成后，强制）**：- [ ] typecheck 通过- [ ] lint 通过- [ ] tests 通过（按计划范围）- [ ] Evidence 完整（可复现，state/evidence/）- [ ] Rollback Drill 完成（含演练证据）- [ ] Known Limitations 已记录并沟通- [ ] 上线后观察指标已定义并可执行- [ ] （Handover）接管遗留问题已闭环或获接受→ 未全部勾选前，不得标记整体完成
**Blocker SLA（三态熔断）**：
| 状态 | 触发条件 | 处理|
|------|---------|------|
|**Closed** | 正常执行中 | 继续|
|**Open** | 同一阻塞超 2 次修复尝试失败 | executor.md Blocker 报告 + 标 BLOCKED + 通知用户|
|**Half-Open** | 用户提供新约束/新信息后 | 单次试探：成功→Closed 继续，失败→维持 Open + 回 Plan 二次批准 |\|
> 「不同方案」≠「重试」：每次尝试必须改变策略方向，相同思路换参数不算新方案。
**Phase 3 状态追踪**（写入 `state/progress.md`）：
```##
Phase 3 — Execute- 状态：🔄 执行中 / ✅ 已完成- 当前 Task：RPE-xxx [描述]- 当前主循环步骤：[N]- 已完成 Task：[列表]- Gate-X 暂停次数：[N]- Blocker 数：[N]- 阻塞项：[列表]

```

#### 进度文件模板（`state/progress.md`）

```markdown

# RPE Progress: {feature_name}

## 特性信息- 特性名：{feature_name}- 创建时间：{date}- 状态：Phase [1/2/3] / 主循环执行中 / 已完成

## Phase 1 — Research- 状态：pending- 迭代次数：0

## Phase 2 — Plan- 状态：pending- 迭代次数：0

## Phase 3 — Execute- 状态：pending- 当前 Task：-

## RPE 任务项（Phase 3 进入主循环时从 plan.md 提取）

## 当前进度### {date} 会话- 当前阶段：[Phase N / 主循环 Step N]- 当前任务项：RPE-xxx- 完成项：[列表]- 阻塞项：[列表]- 下一步：[描述]

## Tech-Debt List（开发过程中发现但不立即处理的技术债务）

## 已完成任务项（从 RPE 任务项移入）

```

### 恢复流程（默认行为）

```1
. 搜索 RPE 实例目录： ls rpe/
2. 若多个特性 → 列出供用户选择 若指定名称 → 直接加载 rpe/{feature_name}/ 若仅一个 → 自动加载
3. readFile rpe/{feature_name}/state/progress.md → 提取： - 当前阶段（Phase 1/2/3 / 主循环） - 当前步骤编号（主循环时） - 当前任务项 ID - 上次会话的"下一步" - 阻塞项
4. 上下文完整性校验（防止 progress.md 与实际文件状态不一致）： ├─ Phase 2+ 但 research.md 仍为空骨架 → 警告，回退到 Phase 1 ├─ Phase 3 但 plan.md 仍为空骨架 → 警告，回退到 Phase 2 ├─ 主循环但 RPE 任务项区为空 → 警告，回退到 Phase 3 入口 └─ 文件缺失（research/plan/executor.md 被删除）→ 从模板重建 + 警告用户
5. 判断恢复入口： ├─ Phase 1 未完成 → 恢复 Research 迭代循环 ├─ Phase 2 未完成 → 恢复 Plan 迭代循环 ├─ Phase 3 / 主循环 → 恢复对应主循环步骤 └─ Gate-X 暂停中 → 恢复 Plan 二次批准
6. 输出恢复摘要： 📂 已恢复：{feature_name} 📍 当前阶段：[Phase N / 主循环 Step N] 📋 当前任务：RPE-xxx {描述}（主循环时） 📝 上次记录的下一步：{内容} ⚠️ 阻塞项：{列表或"无"}
7. → 进入对应阶段/步骤

```
**完成标准**：- ✅ 进度文件已加载（引用 readFile 输出）- ✅ 恢复摘要已输出- ✅ 上下文已重建（当前阶段 + 步骤 + 任务项 + 阻塞项）- ✅ 恢复入口正确（Phase 1/2/3 或主循环步骤）

---

## 主循环（9 步）

```[1] 读 RPE 任务项 │ ▼[2] 设计 │ ↓ 方案自评（自动调 lx-code-review 评审方案） ▼[3] 编码 + pre-commit 门禁 │ ├─ 编译通过（Go: go build / 前端: tsc --noEmit） │ ├─ 代码质量（Go: lx-code-review（专项规则） / 前端: lx-react-review（前端规则）） │ └─ lx-pre-commit 自动跑测试 + 检测测试缺口 + 自动补测 │ ├─ 全部通过 ──► [4] └─ 任何失败 ──► 修复（max 3 次）→ 重跑门禁 │ └─ 第 3 次仍失败 → 回到 [2] 重新设计 │ ▼[4] Security Review │ ├─ 通过 ──► [5] └─ 发现问题 ──► auto-fix → re-scan（max 2 次）
[5] 同步（输出实现摘要+测试方案+验收清单） │ ▼[6] 等待验收（用户执行） │ ▼[7] 判定验收结果 │ ├─ 通过 ──► [8] └─ 不通过 ──► 分级回退（功能缺失→[3] / 逻辑缺陷→[4] / 规范→[3] minor fix）
[8] Git Commit（需用户确认） │ ▼[9] 写进度摘要 │ ▼ 下一个 RPE 任务项 → 回到 [1]

```

### 关键变更说明（11 步 → 9 步）
| 旧步骤 | 新处理 | 原因|
|--------|--------|------|
|Step 3.5 Code Review | 合并到 [3] pre-commit 门禁 | lx-pre-commit 已自动调 lx-code-review|
|Step 4 TDD 查漏补缺 | 合并到 [3] pre-commit 门禁 | lx-pre-commit Step 3.5.4 已自动补测试缺口|
|Step 5 Security | 成为 [4] | 位置前移（原序号不变）|
|Step 6-10 | 成为 [5]-[9] | 序号整体减 1 |
---

### Step 1 — 读 RPE 任务项
加载 `@../../nodes/behavior_rules.md`，应用执行阶段行为约束。
**输入**：用户提供 或 从进度文件读取下一个未完成项。
**执行**：
```1
. readFile rpe/{feature_name}/state/progress.md2. 找到第一个未完成的 RPE 任务项（`- [ ] RPE-xxx`）3. 分析任务项范围： - grep 相关代码文件 - 预估影响范围4. 调用脚本提取该 Task 的 AC 列表： python3 .claude/skills/lx-rpe/scripts/extract_ac.py \ --feature {feature_name} \ --task {task_id} 读取 JSON → 获取 ac_list 用于 Step 6 验收清单5. 输出任务概要
1. readFile rpe/{feature_name}/state/progress.md2. 找到第一个未完成的 RPE 任务项（`- [ ] RPE-xxx`）3. 分析任务项范围： - grep 相关代码文件 - 预估影响范围4. 调用脚本提取该 Task 的 AC 列表： python3 .claude/skills/lx-rpe/scripts/extract_ac.py \ --feature {feature_name} \ --task {task_id} 读取 JSON → 获取 ac_list 用于 Step 6 验收清单5. 输出任务概要

```
**工具降级**：进度文件不存在 → 询问用户提供任务项。
**完成标准**：- ✅ 当前任务项 ID + 描述已明确- ✅ 影响范围已初步评估（引用 grep 输出）- ✅ 进度文件中该项已标记为当前项
**输出模板**：
```📋 RPE-xxx {描述} · 影响 [N] 文件 → Step 2 设计
📋 RPE-xxx {描述} · 影响 [N] 文件 → Step 2 设计

```

---

### Step 2 — 设计
加载 `@../../nodes/context_collector.md`，收集项目上下文。
**职责分工**：- Claude Code：详细技术设计（函数签名、数据结构、调用链）- OpenCode（如参与）：高层架构决策
**执行**：
**按项目类型加载编码规范**：- Go 项目：加载 `@scripts/../references/go-coding-rules.md`- 前端项目：加载 `@scripts/../references/frontend-coding-rules.md`

```1
. 分析任务需求 → 拆解为子任务2. grep / readFile 现有同类实现 → 提取可复用模式3. 设计方案： - 新增/修改的文件列表 - 每个文件的变更概要 - 接口设计（Go: go-style-guide §4.17 ISP / 前端: 组件 Props 接口 + Hook 契约） - 数据流路径4. 输出设计文档（executor 阶段：AI 自主完成，不停下等待用户审阅，直接进 Step 3）
1. 分析任务需求 → 拆解为子任务2. grep / readFile 现有同类实现 → 提取可复用模式3. 设计方案： - 新增/修改的文件列表 - 每个文件的变更概要 - 接口设计（Go: go-style-guide §4.17 ISP / 前端: 组件 Props 接口 + Hook 契约） - 数据流路径4. 输出设计文档（executor 阶段：AI 自主完成，不停下等待用户审阅，直接进 Step 3）

```

**惯性断路器**：> "我的设计是否过度工程化？是否有更简单的方案？"> 检查：新增抽象层是否必要？能否复用现有组件？
**完成标准**：- ✅ 子任务列表已明确- ✅ 影响文件列表已确定（引用 grep 输出）- ✅ 接口设计符合 ISP（方法 ≤5）- ✅ 可复用模式已识别
**输出模板**：
```## 设计方案：RPE-xxx

### 子任务1. [描述] → [文件]2. [描述] → [文件]

### 影响文件| 文件 | 变更类型 | 概要 ||------|---------|------|| [path] | 新增/修改 | [描述] |

### 接口设计[如涉及新接口，列出方法签名]

### 可复用模式参考：[existing_file:line] 的 [模式名]

### 风险点[如有，列出潜在风险]

```
---
### Step 3 — 编码 + pre-commit 门禁
加载 `@../../nodes/auto_fixer.md`，传入变更 + 修复策略。
> **核心变更**：lx-pre-commit 统一处理 Code Review + 测试执行 + 测试缺口检测 + 自动补测。不再单独调 lx-code-review 和 lx-golang-test。
**执行序列**（按项目类型路由）：
**Go 项目**：
```1
. 按设计方案逐文件实现 关键决策点主动说一句（只在以下情况，不逐行汇报）： · 复用了重要现有模块 → "复用 {file:line} 的 {模式名}" · 发现 plan.md 外的问题 → "发现 {问题}，记入 tech-debt，继续" · 换了实现策略 → "改用 {新策略}，原因：{为什么}" · 遇到模糊需求 → "plan.md 对 {X} 没说清楚，采用 {决策}"2. 遵循 go-style-guide §4.1-§4.20 全部规范3. 每个文件完成后 → go build ./... 增量编译检查4. 全部文件完成后 → 调用 lx-pre-commit（自动门禁）： a. 编译验证 b. 自动调 lx-code-review（专项规则 + auto-fix） c. 运行变更包测试（go test -race） d. 检测测试缺口 → 自动调 lx-golang-test 补测 e. 输出综合判定5. 发现技术债 → 记入进度文件 Tech-Debt List（不立即处理）6. **生成实现文档写入 executor.md**（门禁通过后立即执行）： - 变更概要（文件列表 + 行数 + 说明） - 关键设计决策（与 plan.md 对比，记录实际偏差） - 已知限制（如有）
1. 按设计方案逐文件实现 关键决策点主动说一句（只在以下情况，不逐行汇报）： · 复用了重要现有模块 → "复用 {file:line} 的 {模式名}" · 发现 plan.md 外的问题 → "发现 {问题}，记入 tech-debt，继续" · 换了实现策略 → "改用 {新策略}，原因：{为什么}" · 遇到模糊需求 → "plan.md 对 {X} 没说清楚，采用 {决策}"2. 遵循 go-style-guide §4.1-§4.20 全部规范3. 每个文件完成后 → go build ./... 增量编译检查4. 全部文件完成后 → 调用 lx-pre-commit（自动门禁）： a. 编译验证 b. 自动调 lx-code-review（专项规则 + auto-fix） c. 运行变更包测试（go test -race） d. 检测测试缺口 → 自动调 lx-golang-test 补测 e. 输出综合判定5. 发现技术债 → 记入进度文件 Tech-Debt List（不立即处理）6. **生成实现文档写入 executor.md**（门禁通过后立即执行）： - 变更概要（文件列表 + 行数 + 说明） - 关键设计决策（与 plan.md 对比，记录实际偏差） - 已知限制（如有）

```

**前端项目**：
```1
. 按设计方案逐文件实现 关键决策点主动说一句（只在以下情况，不逐行汇报）： · 复用了重要现有组件/Hook → "复用 {file:line} 的 {组件名}" · 发现 plan.md 外的问题 → "发现 {问题}，记入 tech-debt，继续" · 换了实现策略 → "改用 {新策略}，原因：{为什么}" · 遇到模糊需求 → "plan.md 对 {X} 没说清楚，采用 {决策}"2. 遵循项目 ESLint/Prettier 规范 + TypeScript strict mode3. 每个文件完成后 → npx tsc --noEmit 增量编译检查4. 全部文件完成后 → 调用 lx-pre-commit（自动门禁）： a. TypeScript 编译检查（tsc --noEmit） b. 自动调 lx-react-review（组件质量规则） c. 运行测试（npm test / vitest run） d. 检测测试缺口 → 自动调 lx-frontend-test 补测 e. 输出综合判定5. 发现技术债 → 记入进度文件 Tech-Debt List（不立即处理）6. **生成实现文档写入 executor.md**（门禁通过后立即执行）： - 变更概要（文件列表 + 行数 + 说明） - 关键设计决策（与 plan.md 对比，记录实际偏差） - 已知限制（如有）
1. 按设计方案逐文件实现 关键决策点主动说一句（只在以下情况，不逐行汇报）： · 复用了重要现有组件/Hook → "复用 {file:line} 的 {组件名}" · 发现 plan.md 外的问题 → "发现 {问题}，记入 tech-debt，继续" · 换了实现策略 → "改用 {新策略}，原因：{为什么}" · 遇到模糊需求 → "plan.md 对 {X} 没说清楚，采用 {决策}"2. 遵循项目 ESLint/Prettier 规范 + TypeScript strict mode3. 每个文件完成后 → npx tsc --noEmit 增量编译检查4. 全部文件完成后 → 调用 lx-pre-commit（自动门禁）： a. TypeScript 编译检查（tsc --noEmit） b. 自动调 lx-react-review（组件质量规则） c. 运行测试（npm test / vitest run） d. 检测测试缺口 → 自动调 lx-frontend-test 补测 e. 输出综合判定5. 发现技术债 → 记入进度文件 Tech-Debt List（不立即处理）6. **生成实现文档写入 executor.md**（门禁通过后立即执行）： - 变更概要（文件列表 + 行数 + 说明） - 关键设计决策（与 plan.md 对比，记录实际偏差） - 已知限制（如有）

```

**编译失败处理**：
| 失败次数 | 动作|
|---------|------|
|第 1 次 | 读取错误信息 → 修复 → 重新编译|
|第 2 次 | 分析是否设计问题 → 修复 → 重新编译|
|第 3 次 | **停止编码**，回到 Step 2 重新设计 |\|
**pre-commit 门禁规则**：
| lx-pre-commit 结果 | 动作|
|-------------------|------|
|格式 ✅ + 测试 ✅ + 代码质量 ✅ | → Step 4|
|测试缺口 → 自动补测通过 | → Step 4|
|P0 auto-fix 通过 | → Step 4|
|测试失败 / 编译失败 / P0 blocked | 修复 → 重跑门禁（max 3 次）|
|第 3 次仍失败 | 回到 Step 2 重新设计 |\|
**完成标准**（按项目类型）：
**Go 项目**：- ✅ `go build ./...` 编译通过（引用实际输出，exit code = 0）- ✅ lx-pre-commit 判定通过（引用实际输出）- ✅ P0 = 0（lx-code-review auto-fix 后）- ✅ 测试全部 PASS（含自动补测）- ✅ Change Budget 未超标（`git diff --name-only | wc -l` ≤ plan.md 允许上限）- ✅ 技术债已记录（如有）- ✅ 编译/门禁失败重试 ≤3 次- ✅ **实现文档已写入 executor.md**（变更概要+关键决策+已知限制，供 Step 5 引用）
**前端项目**：- ✅ `npx tsc --noEmit` 编译通过（引用实际输出，exit code = 0）- ✅ lx-pre-commit 判定通过（引用实际输出）- ✅ P0 = 0（lx-react-review 后）- ✅ 测试全部 PASS（含自动补测）- ✅ Change Budget 未超标（`git diff --name-only | wc -l` ≤ plan.md 允许上限）- ✅ 技术债已记录（如有）- ✅ 编译/门禁失败重试 ≤3 次- ✅ **实现文档已写入 executor.md**（变更概要+关键决策+已知限制，供 Step 5 引用）
---
### Step 4 — Security Review
加载 `@../../nodes/scanner.md`，传入变更 + 安全规则集。加载 `@scripts/../references/security-scan-rules.md` → 按规则执行扫描。
**按项目类型路由**：
**Go 项目**：
```使
用
Skill tool 调用 lx-security-review → Invoke the Skill tool with skill: "lx-security-review"传入：Step 3 变更的文件

```

**降级处理**（lx-security-review 不可用时，Go 项目）：1. 首选 → `lx-security-review`2. 替补 → `oh-my-claudecode:security-review`（传入变更文件列表 + "扫描 Go 安全漏洞"）3. 均不可用 → 内联执行 `govulncheck ./...` + 基础 hardcode 扫描（密钥/eval/SQL 注入模式），🔴 阻塞保留，🟡 降级为警告并注明"静态扫描，未运行完整规则集"
**前端项目**：
```安全检查三
层
：1. npm audit --production（依赖漏洞扫描）2. ESLint security 规则（代码模式扫描）3. 静态模式扫描（eval/innerHTML/硬编码密钥/不安全 URL）
安全检查三层：1. npm audit --production（依赖漏洞扫描）2. ESLint security 规则（代码模式扫描）3. 静态模式扫描（eval/innerHTML/硬编码密钥/不安全 URL）

```

**门禁规则**：
| 结果 | 动作|
|------|------|
|✅ Pass / Clean pass | → Step 5|
|🔴🟠🟡 auto-fix → re-scan 通过 | → Step 5|
|🚫 Blocked，第 1 次 | 修复 → 重新扫描|
|🚫 Blocked，第 2 次 | **暂停**，输出 blocked 报告，询问用户 |\|
**完成标准**（按项目类型）：
**Go 项目**：- ✅ lx-security-review 已执行（引用判定）- ✅ govulncheck 已执行（引用输出）- ✅ 🔴 = 0, 🟠 = 0, 🟡 = 0（修复后）- ✅ 重试 ≤2 次
**前端项目**：- ✅ npm audit --production 已执行（引用判定）- ✅ ESLint security + 静态模式扫描已执行- ✅ 高危/严重漏洞 = 0（修复后）- ✅ 重试 ≤2 次
---
### Step 5 — 实现文档 + 验收准备
> **Fix5**：实现文档（文档 A）在 Step 3 编码完成时已由 AI 生成并写入 executor.md，此处直接引用，不重复生成。
**执行**：
```1
. 引用 Step 3 已写入 executor.md 的实现文档（文档 A）2. 基于 plan.md 的 AC + 测试策略生成 文档 B（测试方案）3. 基于 AC + 文档 B 生成 文档 C（验收清单） → 文档 B、C 相互独立，可并行 Agent 生成
1. 引用 Step 3 已写入 executor.md 的实现文档（文档 A）2. 基于 plan.md 的 AC + 测试策略生成 文档 B（测试方案）3. 基于 AC + 文档 B 生成 文档 C（验收清单） → 文档 B、C 相互独立，可并行 Agent 生成

```

#### 文档 A — 实现摘要（Step 3 已生成，此处引用）
```## 实现摘要：RPE-xxx（Step 3 编码完成时写入）

### 变更概要| 文件 | 变更类型 | 行数 | 说明 ||------|---------|------|------|| [path] | 新增/修改 | [N] | [描述] |

### 关键设计决策1. [决策] — 原因：[why]

### 已知限制[如有]

```

#### 文档 B — 测试方案
```## 测试方案：RPE-xxx

### 已通过测试（引用 Step 3 门禁输出）| 测试名 | 类型 | 覆盖场景 ||--------|------|---------|| TestXxx | unit | [场景] |

### 人工验收测试建议1. [场景描述] — 预期结果：[expected]2. [场景描述] — 预期结果：[expected]

### 边界场景- [需要关注的边界条件]

```

#### 文档 C — 验收清单
```## 验收清单：RPE-xxx

### 自动验收（AI 在 Step 6 自动执行）- [x] 编译：{实际输出}- [x] 测试：{实际输出}- [x] Code Review：{判定结果}- [x] Security：{判定结果}

### 人工验收（需要用户确认）- [ ] [功能点 1]：[验证方法]- [ ] [功能点 2]：[验证方法]

```
**完成标准**：- ✅ 文档 A 已引用（executor.md 中 Step 3 写入的实现摘要）- ✅ 文档 B、C 已生成- ✅ 文档内容与实际变更一致（引用 git diff 验证）

---

### Step 6 — 验收（AI 自动 + 用户确认）
> >
> **Fix2**：AI 先自动执行验收清单中的可自动化部分，
> 再把结果 + 人工验收部分一起给用户确认，减少用户操作。
> **Fix4**：单 AI / 双 AI 两种模式，按实际情况选择。
#### 单 AI 模式（常用）
**AI 先输出可执行验收清单，用户选择执行方式**：

```📋 RPE-xxx 验收清单
自动验收（已完成）： ✅ 编译：go build ./... 通过（exit 0） ✅ 测试：go test -race ./... — 12 passed ✅ Code Review：专项规则通过（Step 3 门禁） ✅ Security：15条+govulncheck 通过（Step 4）
人工验收（需要你做）： 1. {功能点描述} 命令：{具体命令，可直接复制} 期望：{预期结果}
 2. {功能点描述} 命令：{具体命令} 期望：{预期结果}
你可以： · 自己跑上面的命令，把结果告诉我 · 说"帮我跑一下"，我来执行人工验收部分 · 直接说"通过"（如果你已经手动验证过了）

```

#### 双 AI 模式（OpenCode 作为第二终端）

```📤 已同步给 OpenCode： A. 实现摘要 B. 测试方案 C. 验收清单（含自动验收结果）
⏳ 等待 OpenCode 验收报告...请将验收报告粘贴到此处，或输入验收结果。

```
**完成标准**：- ✅ 自动验收项已执行（引用实际输出）- ✅ 用户已确认人工验收结果（通过/不通过）- ✅ 未收到确认前不得推进到 Step 7
**验收报告 Schema**（OpenCode 应返回的格式）：
```## 验收报告：RPE-xxx

### 判定：[通过 / 不通过]

### 功能验收- [x] / [ ] [功能点]：[实际结果]

### 发现的问题（如有）| # | 类型 | 描述 | 严重度 ||---|------|------|--------|| 1 | 功能缺失/逻辑缺陷/规范问题 | [描述] | [高/中/低] |

### 建议[如有]

```

---

### Step 7 — 判定验收结果
加载 `@../../nodes/verifier.md`，传入验收结果 + 原始 AC。
**解析验收报告** → 分级处理：
| 判定 | 问题类型 | 回退目标 | 动作|
|------|---------|---------|------|
|✅ 通过 | 无 | → Step 8 | 继续|
|❌ 功能缺失 | 缺少功能点 | → Step 3 | 补充实现|
|❌ 逻辑缺陷 | 实现有 bug | → Step 3 | 修复（门禁已含测试）|
|❌ 规范问题 | 风格/命名/结构 | → Step 3 | minor fix |
**回退限制**：
| 回退次数 | 动作|
|---------|------|
|第 1-2 次 | 正常回退修复|
|第 3 次 | **暂停**，输出完整问题列表，与用户讨论是否拆分任务 |
**完成标准**：- ✅ 验收报告已解析- ✅ 判定结果明确（通过 / 不通过 + 问题类型）- ✅ 回退次数已记录（≤3 次）

---

### Step 8 — Git Commit（需用户确认）
加载 `@scripts/../references/commit-convention.md` → 确认 commit 格式。
**执行**：
```1
. 调用脚本生成待确认信息： python3 .claude/skills/lx-rpe/scripts/git_commit.py \ --feature {feature_name} \ --task {task_id} \ --type {feat|fix|refactor} \ --scope {module} \ --msg "{描述}" \ --dry-run
2. 读取 JSON 输出 → 展示给用户确认： · commit message · 变更文件列表 · diff 统计
3. 等待用户明确确认（必须）
4. 确认后执行实际提交（去掉 --dry-run）： python3 .claude/skills/lx-rpe/scripts/git_commit.py \ --feature {feature_name} \ --task {task_id} \ --type {type} \ --scope {scope} \ --msg "{描述}"
5. 读取结果 JSON → 提取 commit_hash 用于 Step 9 记录

```
**铁律**：必须等待用户明确确认后才执行（--dry-run 步骤必须先跑）。
**完成标准**：- ✅ 用户已确认- ✅ 脚本返回 `{"status": "success", "commit_hash": "..."}` - ✅ commit message 包含 RPE 任务项 ID

---

### Step 9 — 写进度摘要
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。
**更新文件**：`rpe/{feature_name}/state/progress.md` + `rpe/{feature_name}/executor.md`

```1
. state/progress.md（调用脚本）： python3 .claude/skills/lx-rpe/scripts/update_progress.py \ --feature {feature_name} \ --task {task_id} \ --action complete \ --next {next_task_id} - 当前任务项标记为已完成：- [ ] → - [x] - 更新"当前进度"区： ### {date} 会话 - 完成步骤：[1]-[9] 全流程 - 任务项：RPE-xxx ✅ - 变更文件：[列表] - 测试：[N] 个通过 - 关键决策：[如有] - 发现的 tech-debt：[如有] - 下一步：RPE-yyy [描述] - Tech-Debt List 更新（如有新增）
2. executor.md： - 更新该 Task 的 Evidence 记录 - 补充回滚演练记录 - 标记 Gate-E 通过状态

```
**完成标准**：- ✅ state/progress.md 已更新（`readFile` 验证）- ✅ executor.md Evidence 已记录- ✅ 当前任务项已标记完成- ✅ 下一步已明确
**输出模板**：
```✅ RPE-xxx 完成 · [N]文件 [N]测试通过[回退N次]📋 下一个：RPE-yyy {描述} · 👉 /lx-rpe
✅ RPE-xxx 完成 · [N]文件 [N]测试通过[回退N次]📋 下一个：RPE-yyy {描述} · 👉 /lx-rpe

```

---
## 两端交互协议
| 交互内容 | 方向 | 触发时机 | Schema|
|---------|------|---------|--------|
|RPE 任务项 | OpenCode → Claude | Step 1 开始前 | `RPE-xxx [描述]`|
|设计方案 | Claude → OpenCode | Step 2 完成时 | 设计方案模板|
|实现摘要 | Claude → OpenCode | Step 5 | 文档 A 模板|
|测试方案 | Claude → OpenCode | Step 5 | 文档 B 模板|
|验收清单 | Claude → OpenCode | Step 5 | 文档 C 模板|
|验收报告 | OpenCode → Claude | Step 6 完成后 | 验收报告 Schema|
|buglist | OpenCode → Claude | 里程碑后 | `[#] [类型] [描述] [file:line]` |\|
## Skill 映射表
> > **调用方式**：所有 Skill 均通过 `Invoke the Skill tool with skill: "<name
> "` 调用，不使用斜杠命令。
| 步骤 | Skill（Skill tool name） | 项目类型 | 触发条件 | 模式|
|------|--------------------------|---------|---------|------|
|[2] | 无（直接设计） | 通用 | - | grep + readFile + LSP|
|[3] | `lx-pre-commit` | 通用 | 编译通过后必须执行 | 统一门禁（CR + 测试 + 补测）|
|[3] | ↳ `lx-code-review` | Go | lx-pre-commit 内部调用 | 专项规则 + auto-fix|
|[3] | ↳ `lx-golang-test` | Go | lx-pre-commit 内部检测缺口 | table-driven + mock|
|[3] | ↳ `lx-react-review` | 前端 | lx-pre-commit 内部调用 | 组件质量规则|
|[3] | ↳ `lx-frontend-test` | 前端 | lx-pre-commit 内部检测缺口 | Jest/Vitest + RTL|
|[4] | `lx-security-review` | Go | Step 3 通过后必须执行 | 15 条 + govulncheck|
|[4] | npm audit + ESLint security | 前端 | Step 3 通过后必须执行 | 依赖漏洞 + 代码模式扫描|
|[8] | git commit | 通用 | 验收通过后 | 需用户确认 |\|
## 阶段转换条件（严格门禁）
| 从 | 到 | 条件 | 门禁证据|
|----|-----|------|---------|
|[1] | [2] | 任务项已明确 + 影响范围已评估 | grep 输出|
|[2] | [3] | 设计方案已确定 + 文件列表已明确 | 设计文档|
|[3] | [4] | lx-pre-commit 全部通过（编译+CR+测试） | lx-pre-commit 判定|
|[4] | [5] | security 🔴=0, 🟠=0, 🟡=0 | Go: lx-security-review 判定 / 前端: npm audit + ESLint security 判定|
|[5] | [6] | 三份文档已生成 | 文档内容|
|[6] | [7] | 验收报告已收到 | 用户粘贴|
|[7] | [8] | 验收通过 | 报告判定|
|[7] | [3]/[7] | 验收不通过（按类型分级回退） | 问题列表|
|[8] | [9] | 用户确认 + commit 成功 | git 输出|
|[9] | [1] | 进度摘要已写入 + executor.md 已更新 + 有下一任务项 | readFile state/progress.md + executor.md 验证 |\|
## 里程碑节点（若干任务项完成后）
**触发条件**：累计完成 ≥3 个 RPE 任务项 或 用户主动要求。
**Claude Code 端**：
```1
. 清理 tech-debt list： readFile rpe/{feature_name}/state/progress.md Tech-Debt List ├─ 每项评估： │ · 简单小修 → 记入 tech-debt list（待特性完成后处理） │ · 中等复杂（>3文件或需 AC 驱动）→ /lx-task-spec 创建独立任务 │ （buglist 中的问题是修复/改进性质，不升级到 RPE） └─ 清理完成 → 更新 state/progress.md
2. 代码全局健康检查： /lx-pre-commit（全量文件，非增量）

```
**OpenCode 端**：
```1
. 全量 Auto-test-and-fix2. RPE 整体状态审视与演化3. → 产出 buglist 传递给 Claude Code
1. 全量 Auto-test-and-fix2. RPE 整体状态审视与演化3. → 产出 buglist 传递给 Claude Code

```

**Buglist 处理**：
```接
收 buglist → 逐项分拣：├─ 小修（≤3文件，简单） → 记入 tech-debt list└─ 中等复杂（>3文件 或需 AC 驱动）→ /lx-task-spec
buglist 中的问题本质是修复/改进。RPE 是从业务 PRD 出发的新特性，不是任务大小的升级目标。

```

## 根因三步协议
**任何 BLOCKED 情况必须执行，禁止直接重试相同方向**：
1. **症状**：`[工具输出的可观察表现，如 go build failed / test FAIL / security blocked]`2. **根因假设**：`[为什么会出现此症状，基于代码逻辑/设计缺陷/外部依赖]`3. **修复方向**：`[针对根因的具体动作；若上次已尝试此方向则必须换方向并标注原因]`
> 区分：编译失败（设计/语法问题）→ 回 Step 2；测试失败（逻辑问题）→ 修 Step 3；安全 blocked（漏洞/规范）→ 修 Step 4；验收不通过（功能缺失/逻辑缺陷）→ 按类型分级回退。误判根因类型 = 无效修复循环，达到 Blocker SLA 时必须升级。
**成功惯性检查**（选择方案时必须自问）：> 我选择此方案，是因为它**适合当前场景**，还是因为**上次用过它**？> 两者不同时，必须重新评估——成功案例不等于普适方案。

## 错误恢复与升级路径
| 场景 | 检测机制 | 回退协议 | 重入点 | 升级路径|
|------|---------|---------|--------|---------|
|[3] 编译 3 次失败 | exit code 计数 | 保留代码 | [2] 重新设计 | 询问用户|
|[3] pre-commit 2 次 blocked | blocked 计数 | 按报告修复 | [3] 修复代码 | 暂停，询问用户|
|[3] 测试 3 次失败 | FAIL 计数 | 修复实现 | [3] 重跑 | 深入 debug（max 2 次）|
|[4] security 2 次 blocked | blocked 计数 | auto-fix | [4] re-scan | 暂停，询问用户|
|[7] 验收 3 次不通过 | 回退计数 | 分级回退 | [3] | 暂停，讨论拆分任务|
|Phase 1/2 迭代超 5 轮 | 迭代计数 | 暂停迭代 | 当前 Phase | 询问用户是否继续或简化需求|
|Gate-X 触发 | 执行中检测到 Schema/API 变更 | 暂停执行 | Phase 2 Plan 二次批准 | 用户审批后继续|
|进度文件损坏 | readFile 异常 | git history 恢复 | 入口恢复流程 | 询问用户重建|
|会话中断 | 无（被动） | 下次 continue 恢复 | 上次阶段/步骤 | state/progress.md 保障 |\|

## 上下文保持
| 时间点 | 保存内容|
|--------|---------|
|Phase 1 完成后 | `<remember priority>RPE 特性 {name}，Phase 1 Research 完成，关键发现：[摘要]</remember>`|
|Phase 2 完成后 | `<remember priority>RPE 特性 {name}，Phase 2 Plan 完成，Task 数量：[N]，进入执行</remember>`|
|Step 2 完成后 | `<remember priority>RPE 特性 {name}，当前任务 RPE-xxx，设计方案：[关键决策]</remember>`|
|Step 3 门禁失败时 | `<remember>RPE-xxx 门禁第 [N] 次失败，blocked 项：[规则号列表]</remember>`|
|Step 7 回退时 | `<remember>RPE-xxx 验收回退第 [N] 次，问题：[类型] [描述]</remember>`|
|Step 9 完成后 | `<remember priority>RPE 特性 {name}，已完成 RPE-xxx，下一个 RPE-yyy</remember>` |\|

## 跨 Skill 联动
| 方向 | Skill | 项目类型 | 触发条件 | 数据契约|
|------|-------|---------|---------|---------|
|内部调用 | `lx-pre-commit` | 通用 | Step 3 编译通过后必须执行 | 传递：变更文件；接收：CR+测试+补测综合判定|
|↳ | `lx-code-review` | Go | lx-pre-commit 内部调用 | 专项规则判定 + auto-fix 结果|
|↳ | `lx-golang-test` | Go | lx-pre-commit 检测测试缺口 | 缺口函数名 + 测试类型|
|↳ | `lx-react-review` | 前端 | lx-pre-commit 内部调用 | 前端组件质量判定|
|↳ | `lx-frontend-test` | 前端 | lx-pre-commit 检测测试缺口 | 缺口组件/Hook + 测试类型|
|内部调用 | `lx-security-review` | Go | Step 4 必须执行 | 传递：变更文件；接收：15 条 + govulncheck 判定|
|内部调用 | npm audit + ESLint security | 前端 | Step 4 必须执行 | 传递：变更文件；接收：依赖漏洞+代码模式判定|
|内部调用 | `lx-pre-commit` | 通用 | 里程碑全量检查 | 传递：全部文件；接收：综合判定|
|关联 | `lx-task-spec` | 通用 | 里程碑 buglist 中中等复杂问题 | 传递：问题描述 + AC → task-spec|
|上游来自 | `lx-tdd-spec` | 通用 | 新特性需求规格 | 接收：AC 列表 + GWT 场景 |\|

## 中止条件
| 条件 | 输出|
|------|------|
|无 RPE 实例目录 + 未指定 `new` | 提示：`无 RPE 实例，请使用 /lx-rpe new 新建。`|
|Phase 1/2 用户说"好了"/"可以了" | 进入下一 Phase|
|Phase 3 Gate-X 触发 | 暂停执行，回到 Phase 2 二次批准|
|RPE 任务项全部完成 | `🎉 特性 {name} 全部任务完成！进入里程碑回顾。`|
|用户要求暂停 | 立即写 state/progress.md 进度摘要 → 停止|
|多次回退触发暂停 | 输出完整问题列表 → 等待用户决策|
|非 Go 且非前端项目 | `⏭️ 当前仅支持 Go 和前端（React/Next.js）项目` |\|

## 版本历史
| 版本 | 日期 | 变更摘要|
|------|------|---------|
|v1.0 | 2026-04-17 | 初始版本：Phase 1/2/3 + 9步主循环 + HARNESS 统一入口 + 批量验收 + Blocker SLA 三态熔断|
|v1.1 | 2026-04-17 | P0修复：`### Step 7 — 等待验收` 改为 `### Step 6`（步骤号与主循环对齐）；补 AI 角色声明（C2）；补根因三步协议（E5）；Step 4 补 lx-security-review 3级降级路径（C7）；补版本历史（C8） |\|

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|build_and_test.py 失败 | 脚本执行 | 直接运行 go build && go test，手动读取结果|
|git_commit.py 失败 | 脚本提交 | 直接执行 git add + git commit，需用户二次确认|
|lx-security-review 不可用 | 调用 skill | 执行 govulncheck ./...，标注"[降级扫描]"|
|Gate-X 频繁触发（>3次）| 暂停执行 | 回 Phase 2 全面重审影响范围|
|Phase 迭代超 5 轮 | 继续迭代 | 暂停，询问用户是否简化需求 |
