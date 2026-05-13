---

name: lx-prd

version: v4.0.0

description: "高质量 PRD 生产流水线（RPE 模式）：Discovery → Uncertainty Scan → Draft → Self-Eval → Expert Review → Polish。含专家循环优化、飞轮设计、差距扫盲、无虚构约束。"

complexity: intermediate
when_to_use: "Use when user says 'lx-prd', '写prd', '写 prd', '产品需求文档', '需求文档', 'PRD', 'prd', 'write prd', '帮我写一个prd', '生成prd'."

model: sonnet

effort: high

argument-hint: "new [feature-name] | review [prd-path] | polish [prd-path] | lite [feature-name]"

paths:

 - "rpe/**/*.md"

 - "**/*prd*.md"

 - "**/*PRD*.md"

 - "docs/**/*.md"

harness_version: ">=1.1.0"
role: "PRD production pipeline — specification authoring and quality review"
execution_mode: stepwise

triggers:
  - "/lx-prd"
  - "write prd"
---

# lx-prd — 高质量 PRD 生产流水线（RPE 模式 v2.9）

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|context_collector | `../../nodes/context_collector.md` | Discovery 阶段收集项目上下文|
|generator | `../../nodes/generator.md` | PRD 文档生成|
|report_generator | `../../nodes/report_generator.md` | PRD 最终输出格式化|
|behavior_rules | `../../nodes/behavior_rules.md` | 研究阶段行为约束（防编造/证据门禁）|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |
|verifier | `../../nodes/verifier.md` | PRD AC 质量验证 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|context_summary | `../../schemas/atomic/context_summary.yaml` | Discovery 阶段上下文摘要|
|verdict | `../../schemas/atomic/verdict.yaml` | PRD 质量判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Phase 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长 PRD 生成会话的上下文总结 |

### 状态机
本 skill 使用**私有 6 阶段状态机**（Discovery → Uncertainty Scan → Draft → Self-Eval → Expert Review → Polish），不引用 `orchestrator.md`。原因：PRD 生成是纯文档产出流程，无代码执行/验收阶段。
**核心状态映射**: need_clarification → executing → [Discovery → Uncertainty Scan → Draft → Self-Eval → Expert Review → Polish] → done

### 私有节点
本 skill 无私有节点。

---
> >
> **版本**：v2.9 | **适用范围**：任意领域、任意规模的产品需求文档
> **模式**：RPE（Research → Plan → Execute）三阶段主导，专家循环介入，无虚构约束
> **角色**：你是资深产品经理 + 技术架构师，专注高质量 PRD 产出；负责需求澄清、技术可行性判断、架构决策，以及协调专家 Agent 完成多轮审查
**动态环境信息**：- 当前日期：!`date +%Y-%m-%d`- 工作目录：!`pwd`- 已有 PRD：!`find . -name "*prd*.md" -not -path "*/node_modules/*" 2>/dev/null | head -5 || echo "无"`

---

## 核心设计原则

```R
P
E
主导结构： Research（发现阶段）→ Gate-R → Plan（规划阶段）→ Gate-P → Execute（写作阶段） ↓ Expert Review Loop（专家循环） ↓ Polish（轻量清理）→ Gate-E
```

**6 条硬约束**：
| # | 约束 | 违规后果|
|---|------|---------|
|1 | **无虚构**：每个技术断言必须有来源（`[file:line]` 或 `[文档来源]`），无来源则标 Q 项 | 标 BLOCKED，退回当前阶段|
|2 | **专家必过**：Phase 4 Expert Review 未通过前，不得进入 Phase 5 Polish | 强制循环修复|
|3 | **图表强制**：系统架构/核心流程/飞轮 必须有 Mermaid 图，缺一项 Gate-E 不通过 | 补图后重 Gate|
|4 | **RPE Gate 顺序**：Gate-R → Gate-P → Gate-E 不得跳跃 | 退回对应阶段|
|5 | **扫盲优先**：Phase 1.5 Uncertainty Scan 必须在 Phase 2 Draft 之前完成 | 退回 Phase 1.5|
|6 | **轻量清理收尾**：Phase 5 Polish 是最后阶段，任何过程产物在此之前不得留在正文 | 延迟到 Phase 5 |\|

---

## 入口路由
| 参数 | 动作|
|------|------|
|`new [name]` | 完整流程：Phase 0 → 1 → 1.5 → 2 → 3 → 4 → 5 → Gate-E|
|`lite [name]` | 轻量流程：Phase 0 → 1（简化）→ 2 → 3 → Gate-E，跳过深度 Research 和 Expert Review，适合 2-3h 内输出的小功能 PRD|
|`review [path]` | 仅执行 Phase 3 Self-Eval + Phase 4 Expert Review，输出评分报告|
|`polish [path]` | 仅执行 Phase 5 Polish + Gate-E|
|无参数 | 询问用户选择模式 |\|

---

## Phase 0 — Intake（需求收口）
加载 `@../../nodes/behavior_rules.md`，应用研究阶段行为约束。
**目标**：锁定核心框架，确定 PRD 类型，避免后续返工。
**执行**：1. 确认以下信息（若用户未提供则询问）： - 产品/特性名称；解决谁的什么问题（一句话） - 技术约束：依赖哪些已有系统 - 是否有上一期 PRD/代码 作为基础 - MVP 范围：Phase 1 必须做什么 / 明确不做什么 - **根因三问**（防范范围虚胖）：直接原因 → 中间原因 → 根本原因
2. 判断 PRD 类型 → 决定后续 Research 深度：
| 类型 | 特征 | Research 重点|
|------|------|-------------|
|新产品 | 从零开始 | 飞轮设计 + 竞品/参考|
|功能扩展 | 基于已有系统 | 集成点 + 能力复用矩阵|
|系统集成 | 打通两个系统 | 接口契约 + 解耦原则|
|重构/迁移 | 等价替换 | 差异矩阵 + 回滚策略 |\|
3. 输出 Intake 摘要，等待用户确认：

```##
Intake 摘要- 产品名：{name}（类型：{类型}）- 核心问题：{一句话}- 目标用户：{谁}- 技术约束：{系统列表}- MVP 范围：必须做 {N} 项 / 明确不做 {M} 项- 上一期：{有/无}- 根本原因：{锁定的真正需要解决的问题（来自根因三问第三层）}

```

---

## Phase 1 — Research（发现阶段）
加载 `@../../nodes/context_collector.md`，收集项目上下文。
> **禁止**：用假设填充空白。找不到来源 → 立即转 Q 项。
**BLOCKED 格式**（Research 阶段发现假设时使用）：

```⛔ BLOCKED [Research]：{具体假设内容} 无代码/文档来源 → 解决方式：{转Q项 / 查文档 / 用户确认}
⛔ BLOCKED [Research]：{具体假设内容} 无代码/文档来源 → 解决方式：{转Q项 / 查文档 / 用户确认}
```

**执行序列**：1. 内化约束（CLAUDE.md 若存在必须先读）2. 若有上一期 PRD → 执行**差异矩阵**（`能力 | 上一期状态file:line | 本期状态 | 变更类型`），废弃项必须有明确原因3. 扫描 L1/L2/L3 能力矩阵：L1 已有（file:line 确认）/ L2 需开发 / L3 不确定（→ 转 Q 项）4. 探索飞轮要素：触发器 / 沉淀物 / 再发现机制 / 闭环验证5. 识别架构约束：数据流路径、不可侵入边界、关键接口契约
**L1/L2/L3 能力矩阵模板**：

```| 能力 | 分类 | 来源证据 | 状态 ||------|------|---------|------|| {能力名} | L1 | `file:line` [已验证] | ✅ 直接复用 || {能力名} | L2 | 新增模块 {文件名} | ⬜ 需实现 || {能力名} | L3 | 无代码证据 | ❓ 转 Q 项 |
| 能力 | 分类 | 来源证据 | 状态|
|------|------|---------|------|
|{能力名} | L1 | `file:line` [已验证] | ✅ 直接复用|
|{能力名} | L2 | 新增模块 {文件名} | ⬜ 需实现|
|{能力名} | L3 | 无代码证据 | ❓ 转 Q 项 |

```

**Gate-R（进入 Phase 1.5 的门禁）**：- [ ] L1 能力每项有 `file:line` 来源，非推断- [ ] L2 能力有工作量可估范围- [ ] L3 不确定项已转为 Q 项，未以假设填充- [ ] 飞轮要素已识别（或已确认无飞轮价值）- [ ] 架构约束和不可侵入边界已明确- [ ] 无"应该支持"/"可能有"/"通常是"类表述

---

## Phase 1.5 — Uncertainty Scan（不确定项扫盲）
> **专项扫盲**：把所有"写不出来"的地方显式化，这是防止虚构的核心防线。
**执行序列**：1. 遍历 Phase 1 产出，提取所有 Q 项2. 对每个 Q 项分类：配置类 / 能力类 / 决策类 / 外部依赖类 / 架构类 / **症状类**（表象问题，需根因分析后才能转为 L2 需求，禁止直接写入功能列表）3. 为每个 Q 项指定解决路径（不得留"待定"无路径）4. 询问用户：哪些 Q 项可立即回答？立即更新 L1/L2
**Q 项全景表模板**：

```## Uncertainty Scan 结果
| # | 问题 | 类型 | 影响功能 | 阻塞 Phase | 解决方式 | 状态|
|---|------|------|---------|-----------|---------|------|
|Q1 | {具体技术问题} | 配置类 | F-01 | Phase 2 | 附录 F 人工填写 | ❓ 待填|
|Q2 | {技术可行性问题} | 能力类 | F-02 | Phase 2 | POC 验证 | ❓ 待验 |\|
⚠️ 发现 {N} 个未决项，阻塞 Phase 2 的有 {M} 个。
```
**Gate-U（进入 Phase 2 的门禁）**：- [ ] 所有 Q 项已分类- [ ] 每个 Q 项有明确解决路径- [ ] 用户可立即回答的 Q 项已更新到 L1/L2- [ ] 附录 F 框架已建立（为后续填写准备占位符）

---

## Phase 2 — Plan（规划阶段）
> **目标**：锁定 PRD 完整结构，标注每节的信息来源，在写作前对齐边界。
**标准 PRD 结构**（Plan 阶段锁定，Execute 阶段填充）：

```# PRD：{产品名}（{阶段/期次}）> 版本 | Owner | 更新日期 | 状态

## Phase 2-E — Execute（写作阶段）
命中写作阶段时：加载 `@references/prd-toc-template.md` → 参照目录结构。
加载 `@../../nodes/generator.md`，传入 context_summary + PRD 模板规范。
> > **Gate-P 通过后进入本阶段。** 按已规划结构逐节写作，每节完成后做 Source Check。
> **输出路径规则**：新建 PRD 保存至 `rpe/{product-name}/prd.md`；`review/polish` 模式覆盖原文件。
**Mermaid 图模板**：`readFile(references/mermaid-templates.md)` 获取 4 份通用模板。
**附录 A-F 模板**：`readFile(references/appendix-templates.md)` 获取完整附录骨架。
### Source Check（每节写完后必做）
```检查本
节
（任一触发则标 BLOCKED）：- [ ] 存在"应该"/"可能"/"通常"/"一般来说"- [ ] 技术细节无代码/文档来源- [ ] Q 项被假设填充而非标注- [ ] 指标数值无基线/来源说明
⛔ BLOCKED [{节名}]：发现 {具体问题} → 解决方式：{转Q项 / 查代码文档 / 等待用户确认}

```

### 量化目标规范（四类指标必须齐全）

```markdown
| 指标类型 | 指标 | 当前基线 | 成功阈值|
|----------|------|---------|---------|
|**北极星** | {核心业务指标} | {来源/基线} | {阈值+时间}|
|**过程** | {可量化执行指标} | 0 | {阈值}|
|**飞轮** | {沉淀增长指标} | 0 | {起始触发}|
|**健康** | {成功率/错误率} | 0 | {最低可接受} |
markdown| 指标类型 | 指标 | 当前基线 | 成功阈值 ||----------|------|---------|---------|| **北极星** | {核心业务指标} | {来源/基线} | {阈值+时间} || **过程** | {可量化执行指标} | 0 | {阈值} || **飞轮** | {沉淀增长指标} | 0 | {起始触发} || **健康** | {成功率/错误率} | 0 | {最低可接受} |

```

### 用户故事 AC 规范（三要素必须齐全）

```markdown
**F-XX：{功能名}**用户故事：作为 {角色}，我希望 {动作}，以便 {价值}。验收标准：- AC-1：{触发条件} → {成功状态（可量化）} | 失败时 {失败状态}技术约束（来自 L1 矩阵）：- [已验证: file:line] {约束说明}
markdown**F-XX：{功能名}**用户故事：作为 {角色}，我希望 {动作}，以便 {价值}。验收标准：- AC-1：{触发条件} → {成功状态（可量化）} | 失败时 {失败状态}技术约束（来自 L1 矩阵）：- [已验证: file:line] {约束说明}

```

---

## Phase 3 — Self-Eval（自评）
进入 Phase 3 时（Phase 2-E 完成后）：加载 `@references/self-eval-checklist.md` → 执行8维自评打分。

## PRD 自评报告 — {date}### 评分总表| 维度 | 分数/10 | 发现的具体问题（基于文档内容） ||------|---------|--------------------------|### 总分：X/80（X%）### P0 必须修复（影响执行启动）### P1 建议优化### 亮点
```
**进入 Phase 4 条件**：
| 总分 | 处理|
|------|------|
|≥75/80 | 直接进入 Expert Review（做验证）|
|60-74/80 | 修复 P0 后进入|
|45-59/80 | 修复 P0+P1 后进入|
|<45/80 | 回 Phase 2 重写最低分的两个维度 |
> ⚡ **自评完成后立即执行 Round 0 双族评分**：`readFile(references/scoring.md)` 按 C族/E族 逐维度打分，建立 100 分制基线，填入环比记录表 Round0 列。自评 80 分制决定是否进 Phase 4；双族 100 分制用于 Phase 4 各轮环比追踪，两套独立记录，不得混用。

---

## Phase 4 — Expert Review Loop（专家循环）
> 由专家 Agent 对 PRD 进行多维度审查，循环修复直到无 P0 缺陷。最多 3 轮。
**专家 Agent 选择**：
| PRD 类型 | 首选专家 | 备选|
|---------|---------|------|
|新产品 / 战略级 | `oh-my-claudecode:analyst`（opus） | `oh-my-claudecode:architect`|
|系统集成 / 技术架构 | `oh-my-claudecode:architect`（opus） | `oh-my-claudecode:architect-medium`|
|快速原型 / 功能扩展 | `oh-my-claudecode:architect-medium`（sonnet） | 自评足够 |
**Review Prompt 标准模板**（每轮调用专家必须使用此格式）：

```你是一位专业产品
经
理 + 技术架构师，请对以下 PRD 进行严格审查。

## 审查目标从以下视角评估：需求可执行性、技术可行性、架构完整性、风险识别、MVP 聚焦度。

## 本轮聚焦项（必须重点评估）{Phase 3 自评报告中的 P0 清单；若为 Round 2+：上轮未解决的 P0 清单}

## PRD 内容{readFile(prd_path) 的完整内容}

## 输出要求（严格遵守格式）### P0 问题（阻塞执行启动）[问题，引用 PRD 章节] → [具体可操作的修复建议]若无：输出"无 P0 问题"

### P1 建议（不阻塞但影响质量）### 亮点### 审查结论[通过（无 P0）/ 不通过（有 N 个 P0）]
```
**执行流程**：

```Rou
n
d
N（最多 3 轮）：1. 构造 Review Prompt（按上方标准模板）2. 调用专家 Agent：Task(subagent_type="...", model="opus/sonnet", prompt=<完整prompt>)3. 解析返回：提取 P0 → 立即修复 | P1 → 评估纳入 | 亮点 → 写入记录4. readFile 验证修复后 PRD 对应章节4.5 readFile(references/scoring.md) → 环比打分 Round N，填入记录表5. 无 P0 → Phase 5 | 有 P0 且 N<3 → Round N+1 | N=3 仍有 P0 → 暂停等用户决策

```
**Expert Review 记录模板**：

```markdown
##
Expert Review 记录### Round {N} — {date}**专家**：oh-my-claudecode:{agent-type}（model: {opus/sonnet}）**P0 问题及处理**：| # | 问题（引用章节） | 修复动作 | 状态 |**P1 建议**：| # | 建议 | 是否纳入 | 理由 |**亮点**：**本轮结论**：{通过 / 不通过（剩余 N 个 P0，转 Round N+1）}
```

---

## Phase 5 — Polish（结构清理）
进入 Phase 5 时（Self-Eval 完成后）：加载 `@references/polish-workflow.md` → 执行轻量结构清理。

## 交付 Gate 结果 — {date}✅ 通过项：{N}/12⚠️ 未通过项：{具体问题}📋 交付状态：✅ 可交付 / ⚠️ 待修复 / 📝 待人工（附录 F）👉 下一步：{填写附录 F / 通知开发团队 / 归档}

```

---

## 完整流程图
用户请求查看全流程时（如 "show me the flow"）：加载 `@references/full-flow-diagram.md`

## 常见反模式
| 反模式 | 表现 | 正确做法|
|--------|------|---------|
|**假设驱动** | "应该支持..." "通常会有..." | 立即转 Q 项，等确认|
|**过早镀金** | Phase 1 塞 Phase 2/3 功能 | 显式写"不做什么"|
|**过程污染** | changelog/废弃方案留正文 | Phase 5 统一清除|
|**无飞轮** | 能沉淀能力但未设计闭环 | Phase 1 强制识别飞轮|
|**AC 模糊** | "支持多轮对话"无成功/失败标准 | 三要素：触发/成功/失败|
|**跳过扫盲** | Phase 1.5 未执行就写 PRD | Gate-U 是强制关卡|
|**跳过专家** | 自评通过就直接交付 | Phase 4 Expert Review 不可绕过|
|**指标缺失** | 只有功能需求，无量化成功标准 | 四类指标必须齐全 |

---

## 错误恢复
| 场景 | 处理|
|------|------|
|Phase 1 遇到无法确认的技术细节 | 立即标 BLOCKED，转 Q 项，继续 Research|
|Gate-R/U/P 失败 | 退回对应阶段修复，禁止跳跃|
|Expert Review Round 3 仍有 P0 | 暂停，输出未解决清单，等用户决策|
|Q 项超过 10 个 | 警告：外部依赖过多，建议先收集 Q 项再动笔|
|需求在写作中蔓延 | 标 P2/"超出 MVP"，征询用户确认 |

---

## 中止条件
| 条件 | 输出|
|------|------|
|用户未提供背景 | 进入 Phase 0 交互式询问|
|Phase 3 自评 P0 > 5 个 | 暂停，问用户是否继续或简化范围|
|Expert Round 3 仍有 P0 | 暂停，等用户决策（接受风险 / 继续修复 / 缩减范围）|
|Gate-E 第 2 次未通过 | 暂停，列出所有未通过项，等用户逐项决策|
|用户要求暂停 | 输出当前阶段进度摘要 + 下一步建议，停止 |

---

## Skill 健康度评估（版本决策依据）
> >
> 与 PRD 双族评分（评估文档产出）正交。本框架评估 skill 自身设计质量。
> 完整评分表见主 SKILL.md。评级：≥55 直接可用 | 45-54 修复低分维度 | <45 需要重构
| 维度 | 满分 | 评分要点|
|------|------|---------|
|**流程完整性** | 10 | Phase 结构无歧义？Gate 顺序正确？风险/附录章节完整？|
|**模板可用性** | 10 | 每阶段产出模板可直接使用？按需 readFile 机制存在？|
|**门禁有效性** | 10 | Gate 触发条件清晰？违规后果明确？无绕过风险？|
|**Expert Loop 设计** | 10 | Input/Output Schema 标准化？轮次封顶？环比追踪完整？|
|**防虚构机制** | 10 | Source Check + BLOCKED 格式 + Q 项体系完整？|
|**通用适配性** | 10 | 已去域？Mermaid 模板通用？lite 模式存在？ |

---

## 关联 Skill 编排
> >
> lx-prd 是需求链的**源头**，Gate-E 通过后输出的 PRD 可直接作为下游 Skill 的输入。
> **缺失处理**：调用下游 Skill 前先检测是否存在，缺失时自动降级到替补 Skill，替补不可用时内联执行。
| 关系 | 首选 Skill | 缺失时替补 | 替补均不可用 | 触发条件 | 输入数据契约（lx-prd 提供）|
|------|-----------|-----------|------------|---------|--------------------------|
|下游 | `lx-tdd-spec` | `oh-my-claudecode:tdd` | 内联生成 GWT 表（嵌入 PRD 附录） | Gate-E 通过后，用户说"生成测试规格" | `二、2.1 用户故事 + AC`（F-XX 功能块）|
|下游 | `lx-rpe` | `oh-my-claudecode:ralph` | `oh-my-claudecode:autopilot` | PRD 交付后进入开发阶段 | `二、2.2 功能列表（P0）` + `三、3.1 架构总览` + `附录 A`|
|下游 | `lx-code-review` | `oh-my-claudecode:code-review` | 内联执行 Phase 3 Self-Eval 同等检查 | 开发完成后代码审查 | `三、3.4 ADR 表`（架构决策约束）|
|上游 | 用户/产品规划 | — | — | 用户触发 `lx-prd new` | 功能名称 + 业务背景（自然语言） |
**Skill 可用性检测（调用前执行）**：
```检测顺
序
：1. 尝试调用首选 Skill → 成功则继续2. 首选不存在（harness 报错 / skill 文件缺失）→ 切换替补，声明： "⚠️ [首选Skill] 未找到，降级使用 [替补Skill]，功能等价"3. 替补也不可用 → 内联执行，声明： "⚠️ [首选Skill] 和 [替补Skill] 均不可用，将在当前上下文内联执行等价逻辑"
检测顺序：1. 尝试调用首选 Skill → 成功则继续2. 首选不存在（harness 报错 / skill 文件缺失）→ 切换替补，声明： "⚠️ [首选Skill] 未找到，降级使用 [替补Skill]，功能等价"3. 替补也不可用 → 内联执行，声明： "⚠️ [首选Skill] 和 [替补Skill] 均不可用，将在当前上下文内联执行等价逻辑"

```
**数据传递示例**（lx-prd → lx-tdd-spec，含降级）：
```# 首选路径/lx-tdd-spec输入：rpe/{product-name}/prd.md 中的「二、2.1 用户故事」章节契约字段：功能ID(F-XX)、用户故事三要素、AC 触发/成功/失败条件

# 降级路径（lx-tdd-spec 缺失时）/oh-my-claudecode:tdd输入：同上，补充说明"以下 AC 来自 PRD F-XX"

```

---

## 版本历史
| 版本 | 日期 | 变更摘要|
|------|------|---------|
|v2.4 | 2026-04-17 | P0/P1 修复 8 项（Phase 2-E 命名/路径/风险章节/附录模板/根因/Gate计数等）|
|v2.5 | 2026-04-17 | 新增 Skill 健康度评估框架（6维×10分=60分制）|
|v2.6 | 2026-04-17 | P0 结构拆分：891→400行，模板迁移到 references/；Gate-1.5→Gate-U；新增 lite 入口；Phase 1 补 BLOCKED 格式|
|v2.7 | 2026-04-17 | 修复 P0 流程图矛盾：补充 45-59/60-74 分段修复节点，与 Phase 3 文字表格对齐；删除冗余嵌套目录 lx-prd/lx-prd/|
|v2.8 | 2026-04-17 | 修复 P1 三项：补充 AI 角色声明（C2）；Phase 1.5 新增症状类 Q 项分类（E5）；新增关联 Skill 编排章节含下游数据契约（C7）|
|v2.9 | 2026-04-17 | 关联 Skill 兼容处理：三条下游链路均补充替补 Skill（oh-my-claudecode 系列）及内联兜底逻辑，新增可用性检测三步协议 |
## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|用户无法明确需求 | 引导收集 | 切换为"反向场景"：描述不希望出现什么|
|技术可行性不确定 | 生成 PRD | 在 PRD 中标注"[技术可行性待评估]"，继续|
|模板不适用当前项目 | 套用模板 | 删掉不适用的章节，从问题描述直接开始 |


