---

name: lx-root-cause-analysis

version: v4.0.0

description: "Trace recurring Go bugs via Five Whys: evidence chains → confidence scoring → immunity defense."

when_to_use: "Use when bug recurs after fix, systematic debugging failed, or user says 'root cause', 'keeps happening', 'why again'."

model: sonnet

argument-hint: "<recurring bug symptom and history>"

disable-model-invocation: true

paths:

 - "*.go"

 - "go.mod"

harness_version: ">=1.1.0"

---

Skill: root-cause-analysis v3.1 | Go 项目系统性 bug 根因分析与免疫防护 | 变更日志见同目录 CHANGELOG.md

## 原子化声明

> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点

| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 定位 recurring bug 涉及代码|
|context_collector | `../../nodes/context_collector.md` | 收集 bug 历史和修复记录|
|report_generator | `../../nodes/report_generator.md` | 根因分析报告|
|behavior_rules | `../../nodes/behavior_rules.md` | 研究阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema

| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 分析目标定义|
|context_summary | `../../schemas/atomic/context_summary.yaml` | 历史上下文摘要|
|finding | `../../schemas/atomic/finding.yaml` | 发现的根因线索|
|verdict | `../../schemas/atomic/verdict.yaml` | 根因分析判定 |

### 引用的 task_sys 组件

| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Phase 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长分析会话的上下文总结 |

### 状态机

本 skill 使用**私有 5 阶段状态机**（症状收集 → 证据链构建 → 5-Why 根因 → 置信度评分 → 免疫防御），不引用 `orchestrator.md`。原因：根因分析是深度推理过程，非任务执行流程。
**核心状态映射**: need_clarification → executing → [症状收集 → 证据链构建 → 5-Why 根因 → 置信度评分 → 免疫防御] → done

### 私有节点

本 skill 无私有节点。

---

# 根因分析：五层 Why + 免疫防护

## 目标

将复现 bug 从"可能再次出现"转变为"免疫复现"，分两大阶段：
- **阶段 1-3：侦探** — 证据链根因发现
- **阶段 4-5：免疫设计师** — 测试/验证/监控三重防护
**不适用于**：一次性 bug（使用 `/lx-debug-spec`）、安全扫描（使用 `/lx-security-review`）、新功能规格。

## 最低输入要求

用户问题描述：$ARGUMENTS
继续前必须具备：
1. **症状**：什么失败了，在哪里
2. **复现证据**：至少一次历史发生记录
缺少任一项 → 向用户提问，使用以下模板：
- "请描述 bug 现象和出现位置"
- "这个问题之前出现过吗？第一次是什么时候？"

## 入口检查（自动执行）

```
bashls
go.mod # 缺失 → "不适用"，重定向到通用调试grep "go-zero" go.mod # 存在 → 激活 go-zero 模式（影响阶段 3 的模式匹配）
```

从 `go.mod` 获取 Go 版本 → 应用版本特定约束。

## 会话目标锚定（每个阶段前必须执行）

```
🎯 会话目标锚定原始问题：[$ARGUMENTS 中不超过 20 字]完成标准：[用户预期结果，一句话]
```
每个阶段门控检查："本阶段是否偏离了原始目标？" 是 → 停止，重新对齐。

## 执行步骤

### 1. 症状映射（阶段 1）

加载 `@../../nodes/behavior_rules.md`，应用研究阶段行为约束。加载 `@../../nodes/context_collector.md`，收集 bug 历史和修复记录。
收集症状数据。使用 Task 工具在**单条消息中并行启动**以下 agent：
**Agent A — 历史记录与已知模式**：
- `readFile .claude/claude-next.md` → 提取根因相关条目（标题含 "反哺" / "根因" / "竞态" / "泄漏"），检查当前症状是否匹配已知模式（若匹配 → 标注"疑似已知模式: [条目标题]"，加速定位）
- `git log --grep="[symptom keyword]"` → 历史修复记录
- `git log --oneline -20` → 近期变更
- 受影响区域的现有测试覆盖情况
**Agent B — 故障链**：
- 读取错误日志/堆栈跟踪
- 追踪数据流：触发点 → 中间环节 → 失败点
- 若怀疑并发问题：`go test -race -count=20 ./...`
Go 特定症状检查：加载 `readFile("${CLAUDE_SKILL_DIR}/docs/go-root-cause-patterns.md")` 获取症状特定搜索命令（goroutine 泄漏、nil 指针、竞争条件、连接池、interface panic、go-zero 模式）。
**完成标准**：
- ✅ 症状用一句话描述清楚
- ✅ 影响范围已识别（package/module/service）
- ✅ 时间线：[首次出现] → [修复1] → [复现1] → ... → [当前]
- ✅ ≥1 条历史修复记录，含 commit hash 和结果
- ✅ 故障链：[触发点] → [A] → [B] → ... → [失败点]
- ✅ 复现已通过证据确认
- ✅ 历史根因分析记录：是否存在对同一问题/同类问题的前序分析？ - 检查方式：`git log --grep="ROOT CAUSE" --oneline` + `rg "ROOT_CAUSE_TRIGGER" --include="*.go"` 搜索已有免疫痕迹 - [是 → 前序结论：[引用前序 Phase 3 根因一句话]，本次分析是否与其一致？[一致/矛盾（矛盾点：）/新角度（说明：）]] - [否 → 首次分析]
- ❌ 无复现证据 → 输出"不适用"模板，重定向到 `/lx-debug-spec`

### 2. 断点隔离（阶段 2）

缩小到预期行为与实际行为之间的精确分叉点。
工具（按场景选择）：
1. LSP hover/references → 类型不匹配、interface 违规
2. `ast-grep` → 跨模块模式搜索
3. `go test -v -run TestName` → 隔离失败
4. `go test -race -count=20 ./...` → 并发场景的完整竞争报告
5. `go test -bench=. -benchmem` + `go tool pprof` → 性能问题
**完成标准**：
- ✅ 断点：[packageA] → [packageB]（具体函数名）
- ✅ 工具输出已引用：原始输出（≤3 行）+ 解读
- ✅ 直接原因用一句话陈述
- ✅ 并发评估：是（含竞争报告摘要）/ 否
- ✅ 是否需要深入调查：是/否（原因：复现 / 跨包）
- ✅ 初始置信度：[1-5]/5
**跨 Phase 检查点 CP-2**（Phase 2 完成后必填，传递给 Phase 3）：

```
📌 CP-2 检查点摘要Phase 1 故障链：[触发点] → [...] → [失败点]（一句话）Phase 2 断点：[packageA.FuncX] → [packageB.FuncY]Phase 2 直接原因：[一句话]Phase 2 并发评估：[是/否]Phase 2 初始置信度：[N]/5→ Phase 3 调查起点：[从断点处的哪个 Why 开始]

```

### 3. 五层 Why + 证据链（阶段 3 — 核心）

**入口一致性检查**：Phase 3 调查对象必须 = Phase 1 故障链失败点。若不一致 → 暂停，与用户确认后再继续。
5 层 Why，每层必须提供证据。
加载置信度评分标准：`readFile("${CLAUDE_SKILL_DIR}/docs/confidence-scoring.md")`加载 Go 模式：`readFile("${CLAUDE_SKILL_DIR}/docs/go-root-cause-patterns.md")`
**执行纪律**：
- Why 1-5 按顺序执行，不可跳过
- 每层 Why 格式： ``` Why [N]: [答案] Tool: [命令] 原始输出（≤3 行）: [粘贴实际输出] 证据类型: [LSP/Grep/race/pprof/git/AST] 解读: [从输出得出的结论] 反事实验证: 若此工具输出为空或结果相反，本层结论是否仍成立？[否=证据有效 / 是=⚠️ 证据不足，需：[补充什么]] 一致性: [✅ / ⚠️ 与 Why X 矛盾]
Why [N]: [答案] Tool: [命令] 原始输出（≤3 行）: [粘贴实际输出] 证据类型: [LSP/Grep/race/pprof/git/AST] 解读: [从输出得出的结论] 反事实验证: 若此工具输出为空或结果相反，本层结论是否仍成立？[否=证据有效 / 是=⚠️ 证据不足，需：[补充什么]] 一致性: [✅ / ⚠️ 与 Why X 矛盾]

```
- **提前终止条件**（量化规则，替代模糊的"可操作根因"判断）： - 置信度 ≥ 18/25 **且** 满足以下全部条件时可提前终止： 1. 根因指向可定位的代码位置（有 file:line） 2. 修复方案不需要跨 package 变更 3. 至少 2 个独立证据源支持当前结论 - 不满足上述任一条件 → 必须继续下一层 Why - 提前终止时必须填写：`提前终止理由：[置信度 N/25] + [条件 1/2/3 满足证据]`
- 不确定时 → 以 "Speculative: ..." 为前缀 — 绝不将未验证内容陈述为事实
- 无法提供工具输出 → 标注"需补充：[缺失证据]"，不进入下一层
- 加载工具输出引用规则：`readFile("${CLAUDE_SKILL_DIR}/docs/tool-output-rules.md")`
**反事实检验**（已集成到每层 Why 格式的"反事实验证"字段中）：
**此检查的落地方式**：在上述每层 Why 格式中作为必填字段执行，不可省略。
**置信度评分**（每层 Why 后填写，最终必填）：
按评分标准逐项打分（5 个维度 × 5 分 = 最高 25 分）：
- 证据强度
- 可复现性
- 跨系统一致性
- 设计可追溯性
- 防护可操作性
**完成标准**：
- ✅ Why 1-5 已完成（或已说明提前终止理由）
- ✅ 每层 Why 均有工具 + 原始输出 + 证据类型 + 解读
- ✅ 根因用一句话陈述
- ✅ 置信度 ≥ 18/25 → 进入阶段 4
- ⚠️ 置信度 13-17 → 升级至 Oracle（升级前先用 `<remember priority>` 保存当前调查摘要防止上下文丢失）：`readFile("${CLAUDE_SKILL_DIR}/docs/oracle-escalation.md")`
- ❌ 置信度 < 13 → 调查中止，输出阻塞模板
- ✅ 18-20 边界区间：需 2 个独立证据来源交叉验证
- ✅ 修复层级：根因级或系统级（必须 ≥ 根因级）
- ✅ 已识别复现脚本概念
**跨 Phase 检查点 CP-3**（Phase 3 完成后必填，传递给 Phase 4）：
```
📌 CP-3 检查点摘要Phase 1 故障链：[触发点] → [...] → [失败点]（一句话）Phase 2 断点：[packageA.FuncX] → [packageB.FuncY]Phase 3 根因（一句话）：[Why N 得出的根因]Phase 3 置信度：[N]/25Phase 3 关键证据：[最强证据的工具命令 + 一行输出摘要]→ Phase 4 修复目标：[根因对应的修复位置 file:line]
📌 CP-3 检查点摘要Phase 1 故障链：[触发点] → [...] → [失败点]（一句话）Phase 2 断点：[packageA.FuncX] → [packageB.FuncY]Phase 3 根因（一句话）：[Why N 得出的根因]Phase 3 置信度：[N]/25Phase 3 关键证据：[最强证据的工具命令 + 一行输出摘要]→ Phase 4 修复目标：[根因对应的修复位置 file:line]

```

### 4. 根因消除（阶段 4）
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略。
**入口：读取 CP-3 检查点**，确认 Phase 3 根因 = Phase 4 修复目标。若不一致 → 暂停，与用户确认。
在根因级或系统级修复，绝不修复症状。
加载反模式：`readFile("${CLAUDE_SKILL_DIR}/docs/anti-patterns.md")`加载修复循环规则：`readFile("${CLAUDE_SKILL_DIR}/docs/repair-loop-rules.md")`
编写任何修复前，对照危险信号自检：`readFile("${CLAUDE_SKILL_DIR}/docs/checklists/danger-signals.md")`
**反模式拦截**（自动拒绝以下做法）：
- `time.Sleep()` → 必须使用 `sync.WaitGroup`/channel/context
- 增大 `MaxOpenConns`/retries → 必须修复资源泄漏
- 静默 `recover()` → 必须正确处理并记录日志
- 仅在调用处检查 nil → 必须修复 nil 来源
- 以症状级修复作为最终方案 → 中止，返回 `/lx-debug-spec`
**完成标准**：
- ✅ 修复轮次：[N]/3（超过 3 次 → 强制升级 Oracle）
- ✅ 修复层级：根因级或系统级
- ✅ 修复内容：具体变更，含 file:line 引用
- ✅ 验证命令已执行，原始输出含退出码已引用
- ✅ 原始问题：✅ | 类似问题：✅ | 回归：✅ | -race：✅/N/A
- ✅ 跨阶段一致性：阶段 3 根因 = 阶段 4 修复目标
- ✅ Why 链覆盖：修复指向被识别为根因的 Why 层
- ❌ 任何反模式触发 → 拒绝修复，提供正确方案

### 5. 免疫防护 + 验证（阶段 5）
通过三重防护使复现成为不可能。
**三重强制防护**：
1. **测试防护**：根因攻击测试（模拟根因输入） - 调用 `/lx-golang-test`，传入目标 package、测试类型（race/unit/benchmark）、根因场景 - 并发根因：`go test -race -count=50`
2. **验证防护**：编译期 + 运行时约束 - Interface 约束：`var _ InterfaceName = (*ConcreteType)(nil)` - 运行时：`context.WithTimeout`、输入校验
3. **监控防护**：在关键路径添加告警日志 - goroutine 泄漏：`runtime.NumGoroutine()` 定期检查 - 性能根因：`go test -bench=BenchmarkTarget -benchmem` 基准回归对比（修复前 vs 修复后）
**自动化验证**（强制执行顺序）：
1. IDENTIFY: what command proves immunity works
2. RUN: execute full command including attack injection
3. READ: read complete output, check exit code + failure count + race report
4. VERIFY: does output confirm defense intercepted root cause trigger?
5. CLAIM: only claim immunity after evidence confirms
**完成标准**：
- ✅ 修复轮次：[N]/3
- ✅ 测试防护：[路径] 覆盖根因场景，适用时含 -race
- ✅ 验证防护：[编译期约束] + [运行时守卫]
- ✅ 监控防护：[日志模式] 位于 [关键路径]
- ✅ 验证命令已执行，原始输出已引用
- ✅ 攻击测试通过：模拟根因触发器已被拦截
- ✅ -race 干净（如涉及并发）：未检测到新竞争
- ❌ 任何防护缺失 → 不输出完成模板

### 5.7 经验沉淀（自动反哺）
当全部 5 个阶段通过（根因已消除 + 免疫防护已建立）时，自动追加到 `.claude/claude-next.md`。
**执行规则**：
1. 读取 claude-next.md，按根因模式 + 影响包去重
2. 同类根因模式已有 ≥3 条 → 跳过（噪声控制）
3. 仅记录复现性 bug 的根因模式，一次性 bug 不记录
4. 写入格式：
```
mark
d
o
w
n

## RCA 反哺模板

加载 `@references/rca-feedback-template.md`

## 跨 Skill 联动

| 方向 | Skill | 触发条件 | 数据契约|
|------|-------|---------|---------|
|上游来自 | `/lx-debug-spec` | 调查中止 / 架构挑战 / bug 复现 | 接收：症状摘要 + 复现步骤 + 已排除假说 + 已收集证据 + 修复尝试次数|
|下游传至 | `/lx-golang-test` | Phase 5 免疫防护：生成根因攻击测试 | 调用：`/lx-golang-test <target-function> <test-type>`，根因场景作为上下文传入|
|下游传至 | `/lx-debug-spec` | Phase 4 修复后需回传结果 | 返回：根因（一句话）、修复层级、建议修复文件、免疫验证要求 |

## 中止条件

- 无复现证据 → "不适用"，重定向 `/lx-debug-spec`
- 无 `go.mod` → "不适用"，非 Go 项目
- 阶段 3 后置信度 < 13 → 输出阻塞模板
- 修复循环 3/3 耗尽且 Oracle 失败 → 输出阻塞模板
- 用户说"这不是根因"/"别猜了" → 返回阶段 1

## 用户纠正信号

| 用户说 | 含义 | 处理动作|
|--------|------|---------|
|"这不是根源" | Why 分析偏离方向 | 返回阶段 1|
|"别猜了" | 使用推测代替了证据 | 停止，收集证据|
|"这个之前修过" | 遗漏了历史修复记录 | 重新检查 git 历史|
|"其他包也有这个问题" | 修复范围过窄 | 扩展至跨 package 范围 |

## 降级策略

| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|go test -race 不稳定 | 并发根因 | 增加 -count=50，超时则降为 -count=10 + 人工分析|
|git log 历史不完整 | 历史追溯 | 用 readFile 扫描代码注释中的 FIXME/TODO|
|5-Why 到第3层无进展 | 根因分析 | 标注"[根因待定]"，记录已排除假设，升级 |
