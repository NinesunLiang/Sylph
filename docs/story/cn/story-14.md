# 圣器锻造所 — 工匠的工具箱

> 防御再强也只是盾。要创造东西，还需要剑——那些能产出代码、测试、审查、验证的技能。在 Carror OS 的前哨站和审计庭之外，有一批圣器锻造师，日夜打造着工坊的精良工具。
>
> **2026-05-16 更新**：本文描述的 8 个领域专用 skill（lx-browser-verify、lx-react-review、lx-golang-test、lx-web-perf、lx-prd、lx-debug-spec、lx-security-review、lx-tdd-spec）已于 v6.2.0 从 Carror OS 核心移除。它们属于用户项目层面，不属于 AI 治理框架范围。本文作为历史叙事保留，记录 Carror OS 曾经探索过的方向。

---

## 锻造所的布局

圣器锻造所按产出类型分为四大工坊：

| 工坊 | 圣器（活跃） | 产出 | 历史（已移除） |
|------|------|------|------|
| **代码审查工坊** | lx-code-review | 8大类别39条规则代码质量报告 | lx-security-review, lx-react-review, lx-web-perf, lx-browser-verify |
| **测试工坊** | lx-test-gen | 多语言测试代码生成 | lx-golang-test, lx-tdd-spec, lx-debug-spec |
| **任务工坊** | lx-todo, lx-task-spec, lx-rpe, lx-stepwise | 从轻到重的全谱系任务驱动 | lx-prd |
| **运维工坊** | lx-pre-commit, lx-pre-push, lx-status, lx-varlock | 提交门禁 + 健康面板 + 隐私管理 | — |

---

## 代码审查工坊

### lx-code-review — 多语言代码审查官

语言无关的通用审查：8 大类别 39 条规则，覆盖错误处理、并发安全、接口设计、性能。审查不只看"代码写得对不对"——更看"代码放在这个项目里对不对"（反模式 D3：项目业务盲区防御）。

他的工作流程：读取项目的代码规范（kernel.md / style-guide） → 比对代码与规范的一致性 → 输出结构化审查报告（严重度分级：P0 阻断 / P1 建议 / P2 风格）。

> **历史备忘录**：lx-security-review（独立安全审查）、lx-react-review（React 组件审计）、lx-web-perf（Web 性能诊断）、lx-browser-verify（视觉回归测试）已于 v6.2.0 移除。安全审查现已融入 lx-code-review 的安全类别规则，视觉和性能审查属于项目层面而非 AI 治理框架。

---

## 测试工坊

### lx-test-gen — 语言无关的测试生成器

自动检测项目语言（Go/TS/Python/Rust/Java），路由到对应的测试模式。他不生成"能通过的测试"——他生成"能发现 bug 的测试"。边界值、nil/None 输入、并发竞态、timeout——测试的价值在失败的时刻，不在通过的时刻。

> **历史备忘录**：lx-golang-test（Go 专项）、lx-tdd-spec（行为矩阵）、lx-debug-spec（结构调试）已于 v6.2.0 移除。Go 测试已融入 lx-test-gen 的路由系统，调试逻辑已融入 lx-root-cause-analysis。

---

## 任务工坊：从随手修复到完整 PRD

任务工坊按复杂度分级，避免"高射炮打蚊子"和"水果刀砍大树"。四级升级链：

```
lx-todo (轻量: 1-3个文件, 5步闭环)
  → 失败超过 2 次自动升级 → lx-task-spec
lx-task-spec (中等: 3-10个文件, 引导式3问 → 结构化任务)
  → 复杂度超过阈值自动升级 → lx-rpe
lx-rpe (重量: 完整 feature, 9步闭环)
  → 需要上游 PRD → lx-prd
lx-prd (重量: 产品级, Discovery → 6阶段 → Polish)
```

升级不是惩罚——是承认当前工具的复杂度天花板。用小刀削苹果，用大斧砍树。工具没有高低之分，只有匹配与否。

### lx-stepwise — 步步为营的原子执行者

任务工坊最新的成员。他强制将任何任务拆分为不可再分的原子步骤——每一步是单一、可验证的简单操作。每步完成后必须有 VERIFIED 证据才能进入下一步。

他不是在拆分任务——他在贯彻因果基座的教训：复杂任务中的错误，99% 是因为一步跨太大了。

### lx-todo — 随手抓住的小问题

最简单的 5 步闭环：**capture → triage → fix → verify → close。** 不需要 spec，不需要拆分。但它的硬上限是 2 次失败——超过自动升级到 lx-task-spec。这是防止反模式 C1（编译错误盲修）的保险丝。

### lx-task-spec — 结构化任务引擎

引导式 3 问（目标是什么？范围是哪些文件？验收条件是什么？）→ 结构化任务输入 → 澄清 → 规划 → 执行 → 验收。它是 lx-todo 和 lx-rpe 之间的桥梁——不需要完整 PRD 的 formal 程度，但又超出了随手修的简单度。

### lx-rpe — 完整的 Feature 开发闭环

9 步闭环：TDD → Code Review → Security Review → Acceptance → Graded Rollback。每一步有独立的验证节点，不可跳过。RPE 输出四份文件——design.md（设计理由）/ spec.md（验收条件）/ executor.md（执行记录）/ qa.md（证据汇总）——形成完整的可审计开发记录 `[已验证: AGENTS.md §RPE 文档体系]`。

> **历史备忘录**：lx-prd（产品需求生产工艺）已于 v6.2.0 移除。PRD 编写属于项目层面，不属于 AI 治理框架。

---

## 运维工坊：门禁大厅与监控塔

### lx-pre-commit — 提交前质量门禁

四步质量门：**项目类型检测 → 编译 → 测试 → 代码审查。** AI 负责解读每一步的结果并做出路由决策（通过 / 修复 / 升级），scripts/ 目录中的检测脚本做实际的编译和测试执行 `[已验证: .claude/skills/lx-pre-commit/SKILL.md]`。

他不是 style formatter。不是 lint checker。他是**一口 gate**——在代码进入 git 历史之前拦住有问题的一切。

具体流程：detect_project.py 检测项目语言 → run_checks.py 运行对应语言的编译+测试 → AI 解读结果并通过/失败判定 → 通过则放行 git commit，失败则回开发阶段。

### lx-pre-push — 推送前深度门禁

比 lx-pre-commit 更深、更慢、更彻底。四阶段：**commit message 规范校验（骨架驱动，通用不锁语言）→ 测试覆盖分析（新增代码是否有对应测试？）→ 安全扫描（依赖漏洞、密钥泄露）→ 最终判定（允许推送 / 阻止推送 / 警告推送）。**

commit message 校验通过 `commit_convention.py` 实现——不绑定特定的 Angular/Conventional 格式，而是从项目历史中学习 commit 风格，检测新 commit 是否显著偏离。

### lx-status — 健康面板

4 面板可视化：Token 节省（上下文消耗趋势）、任务通过率（lx-todo/lx-task-spec/lx-rpe 的成功/失败/升级统计）、拦截的错误（permission-gate/context-guard/privacy-gate/fuzzy-block 的触发频率）、升华的知识点（claude-next.md 的 hits 排行，即将升级到 kernel.md 的候选）。

底部追加 audit dashboard 摘要——聚合了 completion-gate 通过率、Oracle 裁决记录、error-dna 错误趋势。他不是"看看状态好不好的面板"——他是飞轮（story-12）的数据可视化端。

### lx-varlock — 隐私脱敏代理

物理隔离的隐私守卫。当 AI 需要接触涉及敏感信息的文件（`.env`、credentials、证书），他不是警告 AI "小心"——他**替代** AI 直接接触文件。AI 告诉 varlock 需要什么操作，varlock 代理执行，AI 永远看不到明文 `[已验证: .claude/skills/lx-varlock/SKILL.md]`。

这是对铁律 #6（隐私防线）的最高级物化——不是"请你不要看"，而是"你根本看不到"。

---

## 新生代工坊：进化中的新工具

除了四大传统工坊，一批新生代圣器正在淬火成型：

### lx-dogfood — 吃自己的狗粮

`lx-dogfood` 是飞轮哲学（story-12）的物化。它不是开发工具——它是测试工具，但测试的不是代码，是 **Carror OS 自身**。它启动独立的 Claude Code 进程，让 AI 以"第一人称操作者"的身份使用 Carror OS，收集 token 消耗、hook 触发率、completion-gate 拦截率。狗粮报告直接喂入飞轮。

它是最"因果"的 skill —— 用系统自己验证自己，把验证结果变成新的因果。

### lx-root-cause-analysis — 根因猎人

`lx-root-cause-analysis` 是调试工坊的新成员。它不修 bug——它找根因。5 Why 追溯法 + 错误分类器 + 交叉验证：每一次 bug 分析输出根因报告（Root Cause / Contributing Factors / Prevention Strategy），确保同一个错误不会出现两次。它贯彻因果基座的逻辑——每一个 bug 都是未来防御机制的种子。

### lx-skillify — 经验结晶师

`lx-skillify` 是把教训变成工具的匠人。当用户反复手动执行某个操作、或 AI 反复遇到同一个模式的问题时，它介入：扫描操作记录 → 提取可复用模式 → 生成 SKILL.md。它不是自动创建 skill——它输出候选草案，通过机制采纳门禁的三问后才可激活。

### lx-validate-skill — 圣器质检师

`lx-validate-skill` 是 skill 目录的看门人。它检查每个 SKILL.md 的结构完整性、hook 规则的误用、与行为模式的一致性和冗余检测。它确保新加入的 skill 是"精品"而非"臃肿"。

### lx-learner — 自适应学习引擎

`lx-learner` 从会话历史中提取知识——当 AI 多次遇到同一类问题并反复纠正时，它检测模式，提出将知识点固化到 claude-next.md 或 kernel.md 的建议。它不是自动写——它输出候选知识点，等 Oracle 审核后才可以执行写入。

### lx-sync — 同步使者

`lx-sync` 负责跨环境同步：当 Carror OS 在多个项目中被使用时，它通过 Source Mirror 协议（story-15）将治理规则的一致性变化同步到各个目标。它是元环（蛇吞己尾）的具体执行者。

### update-carror-os — 自我更新圣器

`update-carror-os` 是唯一操作 Carror OS 自身的 skill。它不是外部工具——它是系统自噬的执行者，在每次跨版本更新时，确保所有 hooks、skills、scripts 的版本一致、注册完整、没有漂移。

---

## 圣器之间的锁链

锻造所的工具不是孤立的——它们按 L3 流水线编排：

```
lx-rpe (Feature 开发)
  → lx-test-gen (生成测试)
  → lx-code-review (功能审查)
  → lx-root-cause-analysis (问题根因追溯)
  → lx-validate-skill (如产出新 skill)
→ lx-pre-commit (提交门禁)
→ lx-pre-push (推送门禁)
→ lx-dogfood (狗粮飞轮)
```

每个工具的产出，是下一个工具的输入。锻造所是一座工厂——不是工具市场。

---

## 工具选择决策树

当面对一个问题时，选择什么工具？

```
问题出现了
  │
  ├─ 1-3 个文件，无 spec 需求 → lx-todo
  │
  ├─ 3-10 个文件，有验收条件但无 PRD → lx-task-spec
  │
  ├─ 需要原子级步步验收 → lx-stepwise
  │
  ├─ 完整 feature，需要四文件闭环 → lx-rpe
  │
  ├─ 需要代码审查 → lx-code-review
  │
  ├─ 需要根因分析 → lx-root-cause-analysis
  │
  ├─ 需要测试 → lx-test-gen
  │
  ├─ 准备提交 → lx-pre-commit
  │
  ├─ 准备推送 → lx-pre-push
  │
  ├─ 产出可复用 skill → lx-skillify → lx-validate-skill
  │
  ├─ 看看整体状态 → lx-status
  │
  └─ 验证 Carror OS 自身 → lx-dogfood
```

关键是：**不要一上来就开完整的 RPE 流程。也不要对完整 feature 用 lx-todo。** 匹配工具体积与问题体积——这是哲学 #2（少量正确大增益）在工具选择中的投影。

---

## 匠人精神

锻造所的哲学根基是哲学 #2（少量正确大增益）——工具不是越多越好。每一件圣器都必须解决一个明确的问题，输出可验证的结果。建造一件新圣器前，必须通过机制采纳门禁的三问（故事-12）。

锻造所在增长，但永不为增长而增长。每件圣器的诞生背后，都有一道具体且重复的伤口——用户反复手动做某件事，直到有人打造出工具来填那个坑。

---

## 相关故事

- [OMA 铸造厂](story-07.md) — lx-rpe/lx-prd 产物的上游消费者（OMA 四站流水线）
- [证据裁判庭](story-04.md) — lx-code-review/lx-security-review 的双模审查与证据链
- [审计军团](story-10.md) — lx-pre-commit/lx-pre-push 在提交/推送时与审计师的协作
- [三重门神谕](story-11.md) — lx-tdd-spec 的行为矩阵是 A 端预言者的燃料
