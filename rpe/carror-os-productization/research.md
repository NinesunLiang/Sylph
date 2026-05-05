# Research — Carror OS Productization

> RPE Version: v2.3 | 最后更新: 2026-05-04
> 状态：✅ Research Completed / ⚠️ Implementation Pending
> 范围：16 original requirements + 17 RPE work items after decomposition
> 证据标准：AGENTS.md L1-L4 验证模型

---

## 需求分组与关键发现

### Group A：知识库 & 文档化（需求 1, 4）

**需求 1：整理超高质量 Carror OS 知识库**
- 现有 `docs/` 目录 36 文件（营销 13+、技术 6+、测试 4+、内部 4+）
- 核心文档完整：features.md（全特性参考）、editions.md（三阶段产品结构）、technical/architecture-review.md（架构评分 9.8/10+9.2/10，**仅限内部参考**）
- 但文档分布零散，缺少**结构化知识体系**（按主题目录组织）
- 营销文档质量高但内部语气过重（v6.1.8-dual-domain-scoring.md 以"自评分"口吻呈现）
- `error_log.md` 已暴露 6 处文档偏差，说明文档与实际代码存在不同步

**需求 4：基础特性文档化（lecture 系列）**
- 目前无 `lecture/` 目录，无逐特性的教学文档
- 现有技术文档侧重"架构概览"而非"特性教学"
- 需要新建 `lecture/` 体系：每个特性独立 `.md`，含功能/实现/哲学/收益/核心代码/可视化图标

---

### Group B：特性验证（需求 2, 5, 6, 7, 8, 10, 11, 12, 15）

**需求 2：每一份特性具备开关 + 强证据**
- 所有 hooks 通过 `harness_config.sh` 的 `hc_enabled()` 机制实现开关（gate on/off）
- 证据层级已定义（AGENTS.md L1-L4），completion-gate 强制要求 VERIFIED 证据
- 但特性开关集中在 hooks 层，skills 层缺少统一开关注册表

**需求 5：Race 模式**
- **证据：** `append-to-claude.md:75` — "Race（多路径编排）模式" 文档化
- **实现程度：** 75%。"race" 是 AI 流程提示，非确定性并发引擎。Race = 任意顺序执行
- **增强机会：** 缺少确定性调度及并行 Bash 任务编排

**需求 6：一人成军 (OMA)**
- **证据：** `oma_lock_manager.py:31-61` — acquire_lock() 原子 O_EXCL 文件锁，60 秒超时、指数退避
- **实现程度：** 核心锁原语已实现。已知问题：posttool-write-lock.sh 存在换行符 bug 导致 release_lock() 永不被调用，需修复锁生命周期后宣称生产级完备
- **增强机会：** 集成至 harness_config 使 OMA 在 lx-rpe 步骤中自动触发

**需求 7：Mirror 扫描（已删除）**
- Mirror 特性（lx-mirror skill）已从代码库删除，本需求不再适用。

**需求 8：渐进式披露 Token 节省 19,280（~75%）**
- **关键发现：** `error_log.md:55-67` 确认该数字**完全无证据支撑**，已从 README 删除
- `loading_matrix.md` 声称 "首次加载 ~394 转 ~120 行，减少 70%" — 同样未经基准测试验证
- **增强机会：** 构建 `scripts/loading_benchmark.py` 实测验证

**需求 10：50% 主动交接 + 80% 物理熔断**
- **证据：** `context-guard.sh:45-51` — 80% 硬阻断 Exit 2（Edit/Write/Bash）
- **证据：** `proactive-handoff.sh` — 50% 软警告（Enhanced 专属，step 完成 + 上下文 >50%）
- **证据：** `context_monitor.py:37-44` — 百分比计算（**注意：该文件磁盘不存在，依赖未闭环**）
- **实现程度：** 80% hard gate 已实现；50% proactive handoff 设计存在，但依赖 context_monitor.py（不存在）导致静默失效，需修复 token source 后再宣称有效

**需求 11：Error DNA + Build Validator**
- **build-validator.sh:57-76/91-253** — 功能完备。多语言错误分类器（Go/npm/pytest/cargo/tsc 等），12 种错误类型 + 修复建议
- **error-dna.sh:5-10** — **严重损坏！** `$DNA_FILE` 未定义，`mkdir-p .omc/state echo` 会创建名为 "echo" 的目录，`$TOOL_NAME` 检查含换行符 bug
- 磁盘上不存在 `error-dna.json`，但 `inject-project-knowledge.sh:166-189` 和 `auto-snapshot.sh:212-227` 都期望读取它
- **关键修复：** 完全重写 error-dna.sh

**需求 12：AI 审计追踪（做了什么/犯过什么错/消耗 Token）**
- **read-tracker.sh** — 将 Read 工具调用去重记录至 `.omc/state/read-files.log`
- **turn-counter.sh** — 会话轮次持久化至 `session-turns.json`，每 N 轮铁律提醒 + 模糊指令检测
- **auto-snapshot.sh:99-311** — Stop hook 写入 JSON 快照 + 会话交接备忘录（活跃步骤/ADR/TODO/踩坑/错误/修改文件）
- **context_monitor.py** — Token 用量追踪
- **实现程度：** 多源审计追踪已具备基础，缺统一视图、token 写入者、防篡改链与轮转
- **增强机会：** read-files.log 缺少轮转机制（无限增长）；Token 可视化可提升

**需求 15：Flywheel 30 天高频阻断报表**
- **证据：** `flywheel-report.sh:13-42` — 从 `~/.claude/flywheel.log` 读 CSV，按 30 天过滤，P0 事件 >5 次时输出 Markdown 表格
- **实现程度：** 基础报表能力存在。需补空日志防护、持久化报表、趋势对比后宣称成熟
- **增强机会：** 首次运行（空日志）时缺少早期守卫

---

### Group C：产品化 & 宣发（需求 3, 16）

**需求 3：产品化宣发准备**
- `docs/marketing/` — 13 文件完整：
  - `manifesto.md` — 双语中英文宣言
  - `launch-plan.md` — 5 周发布计划（截至 June 1）
  - `FAQ.md` — 25 问答覆盖 6 大类别
  - `PRESS-KIT.md` — 中文新闻资料包
  - `README-draft.md` — 英文 GitHub README 草稿
  - `industry-benchmark.md` — 8 维度 x 10 分 vs 9 竞品（Carror OS 72.5/80）
  - `v6.1.8-dual-domain-scoring.md` — 12 维度评分（109.5/120）
  - `cross-platform-hooks.md` — 跨平台 Hook 系统规格
  - `harness-landscape-2026.md` — Agent Harness 行业全景分析
- `drafts/` — 社交媒体内容草稿 + 空白 dogfooding 日志
- **就绪状态：** 文档资产就绪度约 70%-80%；证据化与外部可信度就绪度约 40%-60%。文档完整但缺外部审查、dogfooding 数据、实际用户案例

**需求 16：对外化改造**
- 当前问题：
  1. 定位为"自评分"而非"基于公开方法论"
  2. industry-benchmark.md 缺评分依据说明
  3. 内部推演式评论语气普遍
- 需要重写：dual-domain-scoring.md、industry-benchmark.md、features.md 相关章节

---

### Group D：增强优化（需求 9, 13, 14）

**需求 9/14：追踪能力 + 可视化深度**
- 追踪基础设施完备（Turn counter / Read tracker / Snapshot / Flywheel / Progress tracking）
- 但可视化工具仅 `lx-status`（SKILL.md 1,564 字节，纯文本面板）
- 缺少图形化仪表盘、趋势图表、Token 消耗曲线

**需求 13：Agentic UI 覆盖率**
- 当前 UI：lx-status（纯文本健康面板）、各 skill 的文本输出
- 无图形化界面、无 Web Dashboard、无 CLI TUI（如 bubbletea）
- 按交互式 numbered-choice 菜单定义，当前覆盖率接近 0%；按文本提示/状态输出定义，则已有基础 UI primitives

---

## 风险识别（含 Round 2-3 新增发现）

| # | 风险 | 影响 | 缓解 | 发现轮次 |
|---|------|------|------|---------|
| 1 | error-dna.sh 严重损坏（4 bug） | 跨会话错误记忆功能归零 | RPE-001 完全重写 | Round 1 |
| 2 | 19,280/75% Token 数字无证据 | 营销可信度崩塌 | RPE-002 benchmark 实测 | Round 1 |
| 3 | AI 审计追踪可视化深度不足 | 用户信任建立慢 | RPE-012 lx-status 升级 | Round 1 |
| 4 | docs 与实际代码不同步（6 处） | 文档可信度问题 | RPE-007 lecture 化逐项验证 | Round 1 |
| 5 | error_log.md 记录偏差未纳入正式追踪 | 偏差可能复发 | RPE-006 纳入 lecture 体系 | Round 1 |
| 6 | **posttool-write-lock.sh 嵌入式换行符 Bug** | OMA 锁永不过期 → 孤儿锁 | RPE-014 mkdir 锁自动解决 | **Round 3** |
| 7 | **context_monitor.py 僵尸代码** | token-tracking-index.json 无写入者 | RPE-003 创建写入者或移除 | **Round 3** |
| 8 | **Agentic UI 菜单覆盖率 ~0%** | tests 期望但 hooks 未实现 | RPE-005 扩展 AC (5.4/5.5/5.6) | **Round 3** |
| 9 | **Marketing 12% 验收覆盖 + 12 "分析"框残留** | 对外发布信用不足 | RPE-010 Phase 2 后执行 | **Round 3** |
| 10 | **RPE-016 错误依赖 RPE-014** | 阻塞解耦，Race 可独立执行 | 已删除依赖 | **Round 3** |

---

## GPT5.5 Report Advice Evaluation

> 2026-05-04 | 来源: `state/evidence/gpt5.5-report-advice.md`
> 独立评估 Carror OS 产品定位并提供 10 条优先级建议 + 替代评分框架

### 核心定位差异

GPT5.5 给出的综合评分框架（能力 8.7/10 + 治理 9.0/10 = **综合 8.4/10**）与 Carror OS 自评体系（14 维度 136.7/140 → 折算 126.9/130）口径不同：
- GPT5.5 采用"能力域 + 治理域"双域模型，适合**对外横向比较**
- 自评体系采用 14 维度深度剖析，适合**内部迭代决策**
- 两者互补不冲突：自评用于指导产品开发方向，GPT5.5 评分可用于对外参照框架

### 10 条建议覆盖分析

| # | 建议 | 覆盖状态 | 对应 RPE | 说明 |
|---|------|---------|---------|------|
| 1 | 强 claim 降级为可证据化 | ✅ 已覆盖 | RPE-002、RPE-010 | benchmark + claim-registry.yaml + claim-lint.sh 三层机制 |
| 2 | 先做 repo reality check | ✅ 已覆盖 | RPE-000 | 已在 v1.2 新增为 Phase 0 前置任务 |
| 3 | 建立 claim registry | ✅ 已覆盖 | RPE-010 AC-10.6 | claim-registry.yaml + 四态标注(retracted/downgraded/implemented/partial) |
| 4 | feature registry 机器可读 | ✅ 已覆盖 | RPE-004 | feature-registry.yaml + harness.yaml skills_enabled 块 |
| 5 | 先补 benchmark | ✅ 已覆盖 | RPE-002 | loading_benchmark.py tiktoken 实测，标注 estimate 级别 |
| 6 | 先补治理证据链再谈宣传 | ✅ 已覆盖(结构) | Phase 排序 | Phase 1(修复) → 1.5(可观测) → 2(文档) → 3(宣传)，天然保障 |
| 7 | 提升易用性降低专家门槛 | ⚠️ **缺口** | 待定 | 当前 plan 未覆盖。RPE-007 AC-7.2 (persona 入口) 部分触及但不完整。推荐列为独立交叉关注点，Phase 2 执行时纳入考量 |
| 8 | 对外文档改方法论审查 | ✅ 已覆盖 | RPE-010 AC-10.1/10.2 | 删除"分析"框、自评分语气，改为可复现测试引用 |
| 9 | 补强可视化 + Agentic UI | ✅ 已覆盖 | RPE-005/012/013 | 4 个 numbered-choice 菜单 + lx-status 趋势面板 + audit dashboard |
| 10 | 商业路径分层 | ⚠️ **缺口** | 待定 | 当前 plan 未覆盖。涉及社区/商业策略决策，超出 RPE 产品化范围，建议由项目管理团队单独讨论 |

### 采纳决定

| 建议 | 裁决 | 动作 |
|------|------|------|
| #1-#6, #8-#9 | ✅ **采纳**(已覆盖) | 无需额外变更，计划中已体现 |
| #7 易用性 | ⚠️ **记录待纳入** | RPE-007 AC-7.2 (persona-based 入口) 已部分覆盖；建议 Phase 2 执行时在 docs 重构中加强「首屏入门」引导，减少术语密度 |
| #10 商业路径 | ⚠️ **记录待讨论** | 超出当前 RPE 范围，建议产品治理会议单独讨论 |

---

## GPT5.5 Report Advice 2 Evaluation

> 2026-05-04 | 来源: `state/evidence/gpt5.5-report-advice2.md`
> 提供两份可直接纳入知识库的文档：产品对比评分表 + 本地模型可执行任务清单

### 文档一：Product Comparison Scorecard

**评估**：合理的 10 维评分框架，方法论清晰（1-10 分级定义），带有显式证据级别和外部发布限制声明。Carror OS 综合得分 8.16/10，治理域 9.1 为最高分，开发者体验 6.5 为最低分。诚实且可用于内部战略参考。

**裁决**：✅ **采纳** — 已创建 `docs/internal/product-comparison-scorecard.md`

**与现有评分的互补关系**：

| 评分体系 | 类型 | 用途 |
|---------|------|------|
| Carror OS 14 维自评 (126.9/130) | 内部深度剖析 | 产品迭代方向决策 |
| GPT5.5 10 维评分 (8.16/10) | 外部参照框架 | 竞品横向对比，市场定位参考 |
| industry-benchmark.md 8 维度 | 对外发布版 | RPE-010 中将改为方法论审计 |

### 文档二：Product Optimization Tasks

**评估**：10 个可执行任务（Task 1-10）与现有 plan.md 的 17 个 RPE 任务覆盖高度重叠：

| GPT5.5 Task | 对应 RPE | 状态 |
|------------|---------|------|
| Task 1 Claim Governance | RPE-010 AC-10.6/10.7 | ✅ 已覆盖 |
| Task 2 Repository Reality Check | RPE-000 | ✅ 已覆盖 |
| Task 3 Audit/Token Repair | RPE-003 | ✅ 已覆盖 |
| Task 4 Feature Registry | RPE-004 | ✅ 已覆盖 |
| Task 5 Token-Saving Claims → Benchmark | RPE-002 | ✅ 已覆盖 |
| Task 6 Simplify Developer Experience | ⚠️ 同 #7 缺口 | 记录待纳入 |
| Task 7 Restructure Knowledge Base | RPE-007 | ✅ 已覆盖 |
| Task 8 Marketing Rewrite | RPE-010 | ✅ 已覆盖 |
| Task 9 Observability + Agentic UI | RPE-005/012/013 | ✅ 已覆盖 |
| Task 10 Evidence/Launch Assets | RPE-011 | ✅ 已覆盖 |

**裁决**：⚠️ **不创建多余副本** — 现有 plan.md 已包含更细粒度的 17 个 RPE 任务，GPT5.5 的 10 任务版本作为参考保留，不创建 `product-optimization-tasks.md` 以避免任务清单分裂。

---

## GPT5.5 Release Plan Evaluation

> 2026-05-04 | 来源: `state/evidence/gpt5.5-report-release.md`
> 提供 5 月完整发布作战计划（Week 1-5 + 发布日 + 72h 响应）

### 核心论点

**"5 月最重要的目标不是继续堆功能，而是把 Carror OS 从强概念系统打磨成真实生产环境跑过、有证据、有案例、有传播资产、有商业承接的产品。"**

该论断与现有 RPE Phase 排序完全一致（Phase 1 修复 → Phase 1.5 可观测 → Phase 2 文档 → Phase 3 对外化），是产品策略层面的强化验证而非冲突。

### 评估与采纳

| 章节 | 内容 | 裁决 | 理由 |
|------|------|------|------|
| 定位核心句 | "Carror OS turns AI coding from vibe-driven into evidence-driven" | ✅ **采纳** | 极佳的品牌定位语，已加入 README/manifesto/FAQ |
| 产品叙事 | "半年 vibe coding + 不懂 Go 开发 Go 云平台" | ✅ **采纳** | 用户推荐叙事，已加入 README Origin Story |
| 产品目标 A-E | 发布前质量门槛清单 | 📝 **参考** | 战略指引，无代码变更 |
| Week 1-5 周计划 | 逐周发布日历 | 📝 **参考** | 产品所有者的执行日历，非 RPE 代码工作 |
| 商业设计（三层） | 免费/支持/咨询 | 📝 **参考** | 策略建议，超出当前 RPE 范围 |
| Go/No-Go 条件 | 发布决策清单 | 📝 **参考** | 可用于 Phase 3 执行时的质检清单 |
| Dogfooding Log 模板 | 每次 dogfooding 结构化记录 | ✅ **采纳** | 已创建 `docs/internal/DOGFOODING-LOG.md` |
| Evidence Bank 模板 | 证据资产仓库 | ✅ **采纳** | 已创建 `docs/internal/EVIDENCE-BANK.md` |
| Risk Register 模板 | 风险登记表 | 📝 **参考** | 现有 RPE 风险清单已覆盖 |

### 采用的位置语言

| 语言 | 原文 | 加入位置 |
|------|------|---------|
| 英文定位 | "AI coding governance and workflow layer for Claude Code" | README / FAQ |
| 英文 tagline | "Carror OS turns AI coding from vibe-driven into evidence-driven" | README / manifesto |
| 中文 tagline | "Carror OS 把 AI 编程从凭感觉变成有纪律、有证据、有验收" | README / FAQ |
| 传播核心句 | "AI coding 最大的问题不是 AI 不够聪明，而是它不受控" | manifesto / FAQ |
| 产品叙事 | "半年 vibe coding 真实项目 → 不懂 Go 开发 Go 云平台 → 血的教训催生 Carror OS" | README Origin Story / manifesto |

---

## GPT5.5 better-info Evaluation

> 2026-05-04 | 来源: `state/evidence/better-info.md`
> 独立评估 Carror OS 产品价值并提供 8 条产品化优化建议 + 4 层商业化估值模型

### 核心论点

better-info 的核心论点：**如果 Carror OS 全部核心特性的证据链可复现，它将从一个"高势能专家产品"升级为 AI coding governance / harness 基础设施产品，综合产品力从 8.4 → 8.9-9.1 / 10。** 该论断与现有 RPE Phase 排序的精神完全一致（先修复 → 再证据化 → 再对外），是产品策略层面的外部验证而非冲突。

### 层级估值模型参考

| 情况 | 条件 | 估值区间 | 当前对应状态 |
|------|------|---------|------------|
| 1: 作者自用 | 全部特性证明有效，无外部用户 | ¥50万-¥200万 | 大致符合 current |
| 2: 早期验证 | 3-10 个外部重度用户 | ¥200万-¥800万 | 目标（发布后 1-3 月） |
| 3: 团队试跑 | 2-5 团队 pilot + ¥10万-¥50万 收入 | ¥800万-¥3000万 | 目标（发布后 3-6 月） |
| 4: 赛道代表 | GitHub 2k-10k stars + 付费客户 | 数千万+ | 目标（6-12 月路线） |

**裁决**：📝 **参考** — 超出当前 RPE 代码工作范围，作为商业策略参考保留。

### 8 条优化建议覆盖分析

| # | 建议 | 覆盖状态 | 对应 RPE / 动作 | 说明 |
|---|------|---------|-----------------|------|
| 1 | 简化为 4 核心词 (Gate/Context/Audit/Workflow) | ⚠️ **已记录，RPE-010 执行** | RPE-010 | 极佳的信息架构简化建议。不宜现在零散修改，统一在 RPE-010 marketing 重写时应用：首页/README/features 只提 4 核心词，深层文档保留全概念 |
| 2 | 防御价值包装为"爽点"（5 个 30-60s demo） | 📝 **参考** | RPE-011 | 5 个 demo 场景（假完成被拦/越界编辑被拦/上下文过载被拦/敏感信息操作被拦/错误 DNA 提醒）应纳入 RPE-011 发布资产清单 |
| 3 | 证据分层展示（3-tier） | ✅ **已覆盖** | RPE-010 AC-10.6, docs/internal/EVIDENCE-BANK.md | Layer 1 (普通用户: 截图+demo+case) → Layer 2 (试用者: benchmark+test) → Layer 3 (企业: audit+dogfooding) 天然符合 claim-registry + evidence bank 设计 |
| 4 | 安装体验极简（10 分钟 aha moment） | ⚠️ **新资产** | **本评估创建** | 之前未覆盖。需新建 `docs/guides/first-10-minutes.md` |
| 5 | 最小成功路径 | ✅ **已覆盖** | RPE-007 AC-7.2 | Persona-based 入口自然覆盖 |
| 6 | 作者型→团队型产品（mode selector） | ✅ **已覆盖** | editions.md | 已存在 Harness Only / Base / Enhanced 三层模式选择 |
| 7 | ROI 计算器 | ⚠️ **记录待创建** | 本评估后创建 | ROI Calculator 文档。超出 RPE 代码范围但可快速创建 |
| 8 | 卖治理方案而非产品 | 📝 **参考** | 商业策略 | 超出 RPE 范围，保留作为商业策略参考 |

### 证据层级互补

better-info 提出 C1-C5 证据层级（C1=文档设计存在, C2=代码存在, C3=本地测试通过, C4=真实任务验证, C5=外部用户验证），与现有 AGENTS.md L1-L4 层级互补：

| 层级 | AGENTS.md L1-L4 | better-info C1-C5 |
|------|----------------|-------------------|
| 最弱 | L4: 语法合法 | C1: 文档设计存在 |
| | L3: 脚本执行成功 | C2: 代码存在 |
| | L2: 测试通过+输出匹配 | C3: 本地测试通过 |
| 最强 | L1: 端到端功能验证 | C4: 真实任务验证 |
| | — | C5: 外部用户验证 |

**裁决**：✅ **采纳互补标注** — 在 EVIDENCE-BANK.md 中以双层级标注。C1-C5 更适合对外展示（阶梯清晰），L1-L4 更适合内部门禁（强调端到端 vs 语法级）。

### 6 产品化资产覆盖

| 资产 | 状态 | 说明 |
|------|------|------|
| First 10 Minutes 指南 | ⚠️ **缺失 → 本评估创建** | `docs/guides/first-10-minutes.md` |
| Demo Gallery | ⚠️ **已记录** | RPE-011 launch assets |
| Evidence Bank | ✅ **已创建** | `docs/internal/EVIDENCE-BANK.md` |
| Public Case Studies | ⚠️ **已记录** | RPE-011 launch assets |
| ROI Calculator | ⚠️ **记录待创建** | `docs/commercial/roi-calculator.md` |
| Work With Me | 📝 **参考** | 商业策略，超出 RPE 范围 |

### 采纳决定

| 区域 | 裁决 | 动作 |
|------|------|------|
| 4 核心词简化 | 📝 **记录，RPE-010 执行** | 待 marketing 重写时统一应用 |
| 防御价值 → 爽点 | 📝 **记录** | 纳入 RPE-011 demo 清单 |
| 证据 3-tier 分层 | ✅ **已覆盖** | EVIDENCE-BANK.md + claim-registry 已具备 |
| First 10 Minutes 指南 | ✅ **立即创建** | `docs/guides/first-10-minutes.md` |
| C1-C5 证据层级互补 | ✅ **采纳** | EVIDENCE-BANK.md 双层级标注 |
| ROI Calculator | ⚠️ **记录** | 超出 RPE 范围，单独创建 |
| 4 层估值模型 | 📝 **参考** | 商业策略参考 |

---

## GPT5.5 better-info2 Evaluation

> 2026-05-04 | 来源: `state/evidence/better-info2.md`
> 29 章深入分析：5 月战略、风险识别、首发核心包、证据体系、商业化、发布检查清单

### 核心论点

better-info2 的核心论点：**5 月不是功能扩张月，而是产品定型、证据沉淀、叙事压缩、发布资产和商业入口同步成型的月份。** 该论断与现有 RPE 路线完全一致，是更强有力的策略验证。

### 29 章覆盖分析

| # | 章节 | 覆盖状态 | 对应动作 |
|---|------|---------|---------|
| 1 | 最终战略判断 (harness/governance) | ✅ 已覆盖 | README/FAQ/AGENTS.md 定位已确立 |
| 2 | 最大机会 (dogfooding → 可信证据) | ✅ 已覆盖 | DOGFOODING-LOG.md + EVIDENCE-BANK.md 已创建 |
| 3 | 最大风险 — 首屏太复杂 | ✅ 已覆盖 | 4 核心词简化记录于 RPE-010 |
| 4 | 最大风险 — 防御不够"爽" | ✅ 已覆盖 | Demo Gallery 记录于 RPE-011 |
| 5 | 最大风险 — OS 定位抬高期待 | ✅ 已覆盖 | First 10 Minutes 已创建 |
| 6 | 北极星指标 (每周 ≥2 证据事件) | ⚠️ **新采纳** | 注入内部指标追踪 |
| 7 | 首发核心包 (5 能力) | ✅ 已覆盖 | 映射到 Phase 0/1/1.5 范围 |
| 8 | 首页写法 (READE 首屏压缩) | ⚠️ **已记录** | RPE-010 执行 |
| 9 | First 10 Minutes 文档 | ✅ **已创建** | `docs/guides/first-10-minutes.md` |
| 10 | Demo Gallery | ✅ 已记录 | RPE-011 launch assets |
| 11 | Evidence Bank | ✅ 已创建 | `docs/internal/EVIDENCE-BANK.md` |
| 12 | 证据级别 C0-C5 | ⚠️ **已采纳** | 已在 better-info 评估中采纳，EVIDENCE-BANK.md 标注 |
| 13 | Known Limitations | ⚠️ **新资产 → 立即创建** | `docs/reference/known-limitations.md` |
| 14 | 三种用户路径 | ⚠️ **已记录** | RPE-007 AC-7.2 persona-based 入口 |
| 15 | 商业化入口 | 📝 参考 | 超出 RPE 范围 |
| 16 | ROI Calculator | ⚠️ 记录 | 超出 RPE 范围 |
| 17 | Dogfooding 公开叙事 | ✅ 已覆盖 | DOGFOODING-LOG.md 已创建 |
| 18 | 内容策略比例 | 📝 参考 | 发布策略参考 |
| 19 | 10 个质疑标准回答 | ⚠️ **新采纳** | 注入 FAQ.md 或创建 reference doc |
| 20 | Go/No-Go 检查清单 | ⚠️ **新采纳** | RPE-011 发布资产检查 |
| 21 | 删减/下沉清单 | ✅ 已覆盖 | claim-lint (RPE-010) + claim-registry 覆盖 |
| 22 | 新增文件清单 | ⚠️ **部分覆盖** | known-limitations.md 立即创建；其余多数已存在 |
| 23 | 每日工作模式 | 📝 参考 | 个人工作习惯建议 |
| 24 | 每周产出目标 | 📝 参考 | 发布策略参考 |
| 25 | 量化指标 | ⚠️ **新采纳** | 可作为内部 Go/No-Go 检查表 |
| 26 | 外部测试者 10 问题 | ⚠️ **新采纳** | 注入 `docs/reference/feedback-questions.md` |
| 27 | 7 个致命错误 | ✅ 已覆盖 | claim-lint + evidence 门禁已覆盖 |
| 28 | 今天做 12 件事 | ⚠️ **部分覆盖** | DOGFOODING-LOG、EVIDENCE-BANK、First 10 Minutes 已创建 |
| 29 | 一句话作战纲领 | ✅ 已覆盖 | 与现有策略一致 |

### 新采纳的 4 项（已有明确动作）

| 新采纳项 | 裁决 | 立即动作 | 后续归属 |
|---------|------|---------|---------|
| Known Limitations 页面 | ✅ **立即创建** | `docs/reference/known-limitations.md` | RPE-011 发布资产 |
| 10 个质疑标准回答 | ✅ **记录** | 注入 FAQ.md 已有 QA 体系 | RPE-010 FAQ 扩展 |
| Go/No-Go 检查清单 | ✅ **记录** | 注入 RPE-011 AC 检查表 | RPE-011 launch asset |
| 外部测试者 10 问题 | ✅ **记录** | 创建 `docs/reference/feedback-questions.md` | RPE-011 外部测试 |

### 已覆盖确认（无需额外动作）

| 已覆盖项 | 覆盖位置 |
|---------|---------|
| 战略定位 (harness/governance) | README/FAQ/AGENTS.md |
| Dogfooding Log | docs/internal/DOGFOODING-LOG.md |
| Evidence Bank | docs/internal/EVIDENCE-BANK.md |
| Evidence Level C0-C5 | EVIDENCE-BANK.md 双层级标注 |
| First 10 Minutes | docs/guides/first-10-minutes.md 已创建 |
| 4 核心词简化 | 记录于 RPE-010 |
| 三种用户路径 | 记录于 RPE-007 AC-7.2 |
| 每日 4 时段 | 个人工作习惯，不归属 RPE |

### 与 better-info 的关系

better-info2 与 better-info 是同一个 GPT5.5 的两轮输出，核心建议高度一致：
- better-info：侧重产品价值评估 + 8 优化建议 + 证据层级 C1-C5
- better-info2：侧重 5 月执行策略 + 29 章全面检查清单 + 风险识别 + 发布准备

两者互补，无冲突。此评估是 better-info 评估的补充，而非替代。

---

| # | 问题 | 结论 | 来源 |
|---|------|------|------|
| 1 | lecture/ 目录结构？ | 按构造顺序编号（01.progressive-disclosure → 07.oma-lock），非目录分组 | Oracle Round 1 Ch.2 |
| 2 | 产品化优先级？ | Phase 1 (修复) → Phase 1.5 (可观测性) → Phase 2 (文档化) → Phase 3 (对外化) → Phase 5 (增强) | Oracle Round 3 合成 |
| 3 | 对外化范围？ | 8 维度评分对外发布，12 维度保留内部；删除所有"分析"框内部语气 | Oracle Round 1 Ch.12 |
| 4 | Race "真并发"？ | 否 — Race 是"任意顺序编排"而非真并发，使用目录隔离而非 OMA 锁 | Oracle Round 3 §6 |
| 5 | benchmark 精度？ | n=10 足够，tiktoken cl100k_base 基线，calibrated chars/4 回退，不要求统计显著 | Oracle Round 2 Ch.7 |

---

---

## Oracle Expert Findings (Round 1)

> 以下为 13 项特性分别经独立 Oracle 专家咨询后的原始建议摘要（2026-05-04）。
> ⚠️ **注意**：Round 1 部分 Oracle 使用了"100% 功能完备"等强表述，这些是 Oracle 基于当前代码分析得出的结论。Round 3 最终验证发现其中部分存在依赖缺失、僵尸代码等问题，实际状态已在 Group A-D 主章节和 Round 3 章节中修正。**以主章节结论为准**。

### Chapter 1: Knowledge Base (需求 1)
**Oracle 建议：** 采用 BIMODAL 分类法 — reference spine（存在什么）+ learning paths（如何学习）。重构 `docs/` 为 overview/concepts/reference/guides/governance 目录结构，增加基于角色的入口点。创建 frontmatter-based `doc-sync-check.sh` 自动化验证文档与代码一致。6 优先级实施顺序。

### Chapter 2: Lecture Series (需求 4)
**Oracle 建议：** 8 篇 lecture 按构造顺序编号（而非目录分组）：
```
01.progressive-disclosure → 02.privacy-gate → 03.context-guard →
04.completion-gate → 05.flywheel → 06.race-mode →
07.oma-lock
```
每篇 7 部分模板（Function/Philosophy/Benefits/Implementation/Core Code/Logic Flow/Visual Diagram）。Mermaid 图表。创建 `lecture_sync_check.py` 自动验证代码引用。

### Chapter 3: Feature Verification (需求 2)
**Oracle 建议：** 创建统一 `.claude/feature-registry.yaml` 注册所有可切换特性（hooks + skills）。在 harness.yaml 增加 `skills_enabled:` 块。创建 `feature-probe.sh` 桥接 completion-gate 证据机制。目前缺口：skills 层零开关注册表，无自动探针基础设施。

### Chapter 4: Race Mode (需求 5)
**Oracle 建议：** Race 当前仅为 AI 流程提示（文档化），无真并发引擎。推荐 4 层实现：isolation（.omc/race/{id}/）、dispatch（run_in_background）、coordination（OMA lock）、collection（result.json polling）。Priority: 低（增强项）。

### Chapter 5: OMA Lock (需求 6)
**Oracle 建议：** 100% 功能完备。关键发现：TOCTOU 竞争条件（oma_lock_manager.py:50-52 锁撤销函数），60s 超时对复杂任务过短。推荐 heartbeat 机制检测过期锁、harness_config 集成自动触发、locks.json 锁可观测性。

### Chapter 7: Loading Benchmark (需求 8)
**Oracle 建议：** 19,280/75% 数字完全无证据。实测 L1 = 251 行（非声称的 ~120），加上 session-init 文件后实际首加载 = 432 行。推荐构建 `scripts/loading_benchmark.py` 使用 tiktoken 进行真实 token 测量。对比条件：渐进式 vs 全量加载。

### Chapter 8: Context Guard (需求 10)
**Oracle 建议：** 50% 主动交接和 80% 熔断均 100% 功能完备。三个关键风险：token-tracking-index.json 缺失时静默失败、step 完成检测使用模糊 grep（proactive-handoff.sh:84）、Python 重复调用开销（每次 PostToolUse 调用 3 次 Python）。推荐改用 completion-gate evidence 作为主交接信号，同时支持两种触发源。

### Chapter 9: Error DNA (需求 11)
**Oracle 建议：** error-dna.sh 4 处 bug（换行符/缺少命令分隔符/$DNA_FILE 未定义/JSON 换行损坏）导致完全不可用。根源在 source 模板。推荐完全重写：.jsonl 追加日志 + .json 合并状态双格式。从 build-validator.sh 提取共享 error_classifier.py。增加轮转（7 天过期 / 1MB 轮转）、凭据脱敏（cmd 中 --password/--token 等参数）。

### Chapter 10: AI Audit Trail (需求 12)
**Oracle 建议：** 100% 功能完备但 5 个关键缺陷：文件名不匹配（read-files.log vs read-tracker.txt）、read-files.log 无轮转、token-tracking-index.json 无写入者（context_monitor.py 始终读默认值 0/200000）、无跨源聚合、无防篡改链。推荐统一仪表盘、日志轮转、添加 token 写入者。

### Chapter 11: Flywheel (需求 15)
**Oracle 建议：** 100% 功能完备，隐式静默安全路径正确。推荐改进：显式空日志防护（[ -s "$FLYWHEEL" ]）、flywheel-reports/ 持久化报告、历史趋势对比、持续性 P0 事件桌面通知、P1-P3 终端摘要（不注入 AI 上下文）。

### Chapter 12: Productization (需求 3, 16)
**Oracle 建议：** 文档结构扎实但战略上 naive。改定位：从"自评分"到"方法论审计"——删除所有"分析"框内部推演语气，改为可复现测试引用。评分矛盾（72.5/80 vs 109.5/120）：对外仅发布 8 维度评分。缺少截图/演示视频/外部审查。FAQ 状态良好保持。

### Chapter 13: Agentic UI (需求 9, 13, 14)
**Oracle 建议：** 严格定义的交互式菜单覆盖率 ~0% —— tests 期望 numbered-choice 菜单但 hooks 仅打印纯阻断消息。最高优先级：为 completion-gate.sh 和 context-guard.sh 增加 numbered-choice 菜单。可视化：升级 lx-status 面板展示趋势（无需 TUI/Web）。read-files.log 添加轮转。

### Chapter 14: Error Log 偏差修复（error_log.md）
**Oracle 建议：** 6 项偏差均已内联修复，但修复质量参差：
- ✅ 4/6 修复正确（版本号、hooks 计数、skills 计数、19,280 删除）
- ⚠️ 1/6 修复无效（proactive-handoff.sh 依赖不存在的 context_monitor.py → 静默失效）
- ⚠️ 1/6 不完整（harness-kit/CLAUDE.md 未同步更新）
- **核心根因：** 文档更新与代码修改完全解耦。无自动化机制确保文档-代码一致性。
- **Oracle 裁定：** 现有 RPE 方案（RPE-003 AC-3.3 创建写入者、RPE-007 doc-sync-check.sh）已覆盖修复路径，无需创建独立 Task。**合并到 RPE-003 作为 AC-3.4**。

---

## Oracle Round 2 联网调研（3 不成熟特性）

> 2026-05-04 | 3 项不成熟特性经联网调研，每个出 3 候选方案，Oracle 裁定推荐方案

### 1. Error DNA 重写

| 方案 | 方法 | Oracle 推荐 |
|------|------|:-----------:|
| A: JSONL-only 纯日志 | 仅追加 .jsonl，每次启动重计算合并状态 | — |
| B: **Sentinel File + JSONL 双格式** | .jsonl 追加日志 + .json 合并状态，零依赖 | ✅ **推荐** |
| C: SQLite 结构化存储 | sqlite3 存储，支持复杂查询 | — |

**推荐方案 B 理由**：零外部依赖、兼容 Claude Code CLI 无 Python 运行时约束、双格式同时满足审计需求（JSONL）和状态读取需求（JSON）。

### 2. Loading Benchmark

| 方案 | 方法 | Oracle 推荐 |
|------|------|:-----------:|
| A: 行数统计 (wc -l) | 最轻量，统计文件行数 | — |
| B: **tiktoken cl100k_base 估算** | 近似 token 估算，非 Claude 官方 tokenizer | ✅ **推荐** |
| C: tiktoken + 结构化对比报告 | 条件 A vs B 对比，含完整报告 | — |

**推荐方案 B 理由**：tiktoken cl100k_base 可作为近似估算工具；严谨统计应优先使用 Anthropic 官方 token counting API 或实际运行数据，无法使用时才回退到 chars/4 或 tiktoken estimate。已在 benchmark 报告中标注 estimate 级别。

### 4. OMA Lock 增强

| 方案 | 方法 | Oracle 推荐 |
|------|------|:-----------:|
| A: 增强文件锁 (flock) | 在现有文件锁上增加超时/心跳 | ❌ 违反 pretool/posttool 分离约束 |
| B: **mkdir 原子锁** | `mkdir .lock` 原子操作 + heartbeat | ✅ **推荐** |
| C: 外部锁服务 | 独立锁进程/Redis | ❌ 过度工程 |

**推荐方案 B 理由**：pretool/posttool 分离链约束禁止 flock（posttool 无法释放 pretool 获得的锁）；mkdir 是 POSIX 原子操作，不存在 TOCTOU；.stealing 协议处理锁竞争（双检查模式）。

### 5. Error Log 偏差根因预防

| 方案 | 方法 | Oracle 推荐 |
|------|------|:-----------:|
| A: 人工审核流程 | 每次代码变更后手动更新文档，靠纪律约束 | — |
| B: **自动化 doc-sync-check** | frontmatter-based 验证脚本，每次 commit 前检查 file:line 引用 | ✅ **推荐** |
| C: CI/CD 管道门禁 | 在 CI 中运行 doc-sync-check 作为门禁，阻拦未同步提交 | — |

**推荐方案 B 理由**：
- RPE-007 已计划创建 `doc-sync-check.sh`（AC-7.4），直接复用无需新 Task
- 方案 A 依赖人为纪律，已证明不可靠（6 项偏差全部可追溯到人为疏漏）
- 方案 C 在当前无 CI 的环境下无法实施
- **路径**：RPE-003 AC-3.3 创建 token-tracking-index.json 写入者（修复 proactive-handoff.sh）→ RPE-007 AC-7.4 doc-sync-check.sh 做系统性预防

---

## Oracle Round 3 关键发现（最终验证）

> 2026-05-04 | 13/13 全部裁决 | 详见 `state/oracle-round3-synthesis.md`

### 裁决总览

| 裁决 | 数量 | 特性 |
|------|------|------|
| ✅ GO | 7 | RPE-003/004/006/007/012/013/015/016/017 |
| ✅ GO (条件) | 4 | RPE-003/004/007/016 |
| ❌ NO-GO | 2 | RPE-005 (AC 扩展后重审), RPE-010/011 (Phase 2 后重审) |
| ⏳ 部分 | 2 | RPE-001/002 (Round 2 方案已够，直接沿用) |

### 实锤 Bug 发现

1. **posttool-write-lock.sh 嵌入式换行符**（OMA Lock Round 3 代理 `cat -e` 发现）
   - TOOL_NAME 比较字符串含字面 `\n` + `edit` → `[[ "$TOOL_NAME" != "edit" ]]` 永不为真
   - 后果：posttool 永不调用 `release_lock()`，产生孤儿锁
   - 修复：RPE-014 mkdir 锁替代方案自动解决

2. **context_monitor.py 僵尸代码**
   - `plan.md` 和 `context_guard.md` 引用但**磁盘不存在**
   - `token-tracking-index.json` **无写入者**（无任何代码写入此文件）
   - 修复：RPE-003 AC-3.3 创建写入者或移除引用

### Error Log 偏差修复 Round 3 验证（最终裁决）

**验证方法**：全量复核 error_log.md 6 项偏差修复状态，逐项实际读文件确认。

| # | 偏差 | 声称状态 | 验证结果 | 证据 |
|---|------|---------|---------|------|
| 1 | 版本号不一致 | ✅ 已修复 | ✅ **确认** VERSION=6.1.8, install.sh=v6.1.8-stable, README badge=v6.1.8 | [已验证: VERSION:1, install.sh:4, README.md:3] |
| 2 | 24→26 hooks | ✅ 已修复 | ✅ **确认** README.md:71 "26 个底层物理拦截器", features.md:13 "26 个底层 Hooks" | [已验证: README.md:71, features.md:13] |
| 3 | 19→23 skills | ✅ 已修复 | ✅ **确认** README.md:79 "23 款主动工作流流水线" | [已验证: README.md:79] |
| 4 | 19,280 Tokens 删除 | ✅ 已修复 | ✅ **确认** README.md 无此数字残留 | [已验证: README.md grep 0 匹配] |
| 5 | 50% proactive handoff | ✅ 已实现 | ⚠️ **部分失效** proactive-handoff.sh:28-29 依赖不存在的 context_monitor.py，静默 exit 0，永不被触发 | [已验证: proactive-handoff.sh:28] |
| 6 | 26 hooks 限定语 | ✅ 已修复 | ⚠️ **不完整** CLAUDE.md ✅ + source/CLAUDE.md ✅，但 source/harness-kit/CLAUDE.md:9 仍为旧版 "26个 hooks 自动运行" | [已验证: source/harness-kit/CLAUDE.md:9] |

**裁决**：❌ NO-GO — 2/6 修复未达标

| 发现问题 | 根因 | 修复路径 |
|---------|------|---------|
| proactive-handoff.sh 依赖 context_monitor.py（不存在） | 创建脚本时未验证依赖存在性 | **RPE-003 AC-3.3** 创建 context_monitor.py 或重写 token 采集逻辑 |
| harness-kit/CLAUDE.md 未同步 | 批量修复遗漏源模板 | **RPE-003 新增 AC-3.4** 同步更新 source/harness-kit/CLAUDE.md |
| 系统性根因：无文档-代码一致性自动验证 | 无自动化机制 | **RPE-007 AC-7.4** doc-sync-check.sh 做系统性预防 |

### 结构性修正

| 修正项 | 旧 | 新 | 理由 |
|--------|---|-----|------|
| Phase 结构 | 4 Phase | **6 Phase (新增 Phase 0 + Phase 1.5)** | RPE-012/013 提前 + RPE-000 仓库校验 |
| RPE-009 | 独立 Task，3 AC | **已删除**，AC 分配至 RPE-004/005/012 | 功能归属更精确 |
| RPE-016 依赖 | 依赖 RPE-014 | **无依赖** | Race 用目录隔离，与 OMA 锁正交 |
| RPE-005 AC | 2 个菜单 (completion/context-guard) | **4 个菜单** (+ permission-gate/pretool-edit-scope) | 覆盖全部 4 个交互式钩子 |

### 执行建议（GPT5.5 Plan 评审修正）

```
Phase 0:  RPE-000 (Repository Reality Check) — 必须先执行
Phase 1:  RPE-001 → RPE-002 → RPE-003 → RPE-004 → RPE-005
Phase 1.5: RPE-012 → RPE-013 (依赖 Phase 1 数据源就绪)
Phase 2:  RPE-006 → RPE-007 → RPE-008 (依赖 RPE-001)
Phase 3:  RPE-010 → RPE-011 (依赖 Phase 2 完成)
Phase 5:  RPE-014 → RPE-015 → RPE-016 → RPE-017
```
