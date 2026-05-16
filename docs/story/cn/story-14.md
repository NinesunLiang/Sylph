# 圣器锻造所 — 工匠的工具箱

> 防御再强也只是盾。要创造东西，还需要剑——那些能产出代码、测试、审查、验证的技能。在 Carror OS 的前哨站和审计庭之外，有一批圣器锻造师，日夜打造着工坊的精良工具。
>
> **2026-05-16 更新**：本文描述的 8 个领域专用 skill（lx-browser-verify、lx-react-review、lx-golang-test、lx-web-perf、lx-prd、lx-debug-spec、lx-security-review、lx-tdd-spec）已于 v6.2.0 从 Carror OS 核心移除。它们属于用户项目层面，不属于 AI 治理框架范围。本文作为历史叙事保留，记录 Carror OS 曾经探索过的方向。

---

## 锻造所的布局

圣器锻造所按产出类型分为四大工坊：

| 工坊 | 圣器 | 产出 |
|------|------|------|
| **代码审查工坊** | lx-code-review, lx-security-review, lx-react-review, lx-web-perf, lx-browser-verify | 多维度代码质量报告 |
| **测试工坊** | lx-test-gen, lx-golang-test, lx-tdd-spec, lx-debug-spec | 测试代码 + 行为矩阵 |
| **任务工坊** | lx-todo, lx-task-spec, lx-rpe, lx-prd | 任务驱动，从简单到复杂的全谱系 |
| **运维工坊** | lx-pre-commit, lx-pre-push, lx-status, lx-varlock | 提交门禁 + 健康面板 + 隐私管理 |

---

## 代码审查工坊：双模审查系统

锻造所最独特的圣器是**双模代码审查系统**——传统审查（lx-code-review）+ 视觉审查（lx-browser-verify），两套完全不同方法论，交叉确认。代码审查告诉你"逻辑是否正确"，视觉审查告诉你"是否正确渲染给了用户"。

### lx-code-review — 多语言代码审查官

语言无关的通用审查：8 大类别 39 条规则，覆盖错误处理、并发安全、接口设计、性能。审查不只看"代码写得对不对"——更看"代码放在这个项目里对不对"（反模式 D3：项目业务盲区防御）。

他的工作流程：读取项目的代码规范（kernel.md / style-guide） → 比对代码与规范的一致性 → 输出结构化审查报告（严重度分级：P0 阻断 / P1 建议 / P2 风格）。

### lx-security-review — 安全扫描仪

独立于功能审查的安全维度：OWASP Top 10 漏洞检测、依赖审计（CVE 数据库对比）、密钥泄露扫描（硬编码 Token / Password / API Key）、注入攻击面分析。与 lx-code-review 并行运行——功能正确不意味着安全正确。

他的独立性是设计选择。同一个 AI 不应该同时审查功能和安全性——功能正确的代码可能不安全，安全的代码不一定功能正确。分离审查者 = 交叉视野。

### lx-react-review — 前端组件审计

针对 React/Next.js 的组件模式、hooks 用法、渲染性能、状态管理。审查的不是"JSX 语法对不对"，而是"这个组件的设计在 React 生态中合不合理"——不必要的 re-render、滥用 useEffect、状态提升过远导致的 prop drilling、应该拆分但混在一起的组件。

### lx-web-perf — Web 性能诊断师

6 大类别 24 条检查：bundle 分析（tree-shaking 效果、chunk 分割）、Web Vitals 核心指标（LCP / FID / CLS）、Next.js 优化（Image 组件使用、SSR/SSG 策略、动态 import）。他不是说"这个页面慢"——他定位到"这个 800KB 的第三方库没有 tree-shake，导致首屏加载增加了 1.2 秒"。

### lx-browser-verify — 视觉回归猎手

传统代码审查看不到的盲区，由视觉审查覆盖。

基于 Playwright 的多重武器：多分辨率截图（Desktop / Tablet / Mobile 三端）、视觉回归对比（baseline vs current 像素级差异热力图）、元素定位验证（CSS selector / data-testid / accessibility role 三重定位）、断点布局测试。

他不相信代码——他相信眼睛。正确的 CSS 不等于正确的渲染。Storybook 里完美的按钮可能在 Chrome 125 的一个渲染 bug 下偏移了 3px。lx-browser-verify 找到代码审查永远发现不了的问题。

---

## 测试工坊：从行为矩阵到运行验证

### lx-test-gen — 语言无关的测试生成器

自动检测项目语言（Go/TS/Python/Rust/Java），路由到对应的测试模式：

- Go → table-driven tests + testify mocks + race detector
- TypeScript → Jest/Vitest + Testing Library + MSW
- Python → pytest + parametrize + unittest.mock
- Rust → #[cfg(test)] + proptest

他不是生成"能通过的测试"——他生成"能发现 bug 的测试"。边界值、nil/None 输入、并发竞态、timeout——测试的价值在失败的时刻，不在通过的时刻。

### lx-golang-test — Go 专项测试工匠

语言专用测试：table-driven 模式（标准的 Go 测试哲学）、mockgen/testify 双轨 mock 策略、HTTP handler 测试（httptest.NewServer + recorder）、benchmark（-benchmem + -cpuprofile 联合分析）、fuzz test（Go 1.18+ 原生 fuzzing）、race detector（-race flag 全量覆盖）。

`[已验证: .claude/skills/lx-golang-test/SKILL.md 描述为 "Go test generator"]`

### lx-tdd-spec — 行为矩阵工匠

不写代码——他写**行为矩阵**。Given-When-Then 验收条件，每一条都是可证伪的断言的集合。行为矩阵是三重门（story-11）中 A 端预言者的燃料——预言需要可以被证明为错的断言，而这些断言来自 TDD spec。

### lx-debug-spec — 根因猎人

结构化调试：**假设 → 验证 → 修复 → 回归**。每一步记录假设内容和验证结果。同一假设不能被使用两次——防止反模式 C1（编译错误盲修）的死循环。

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

### lx-todo — 随手抓住的小问题

最简单的 5 步闭环：**capture → triage → fix → verify → close。** 不需要 spec，不需要拆分。但它的硬上限是 2 次失败——超过自动升级到 lx-task-spec。这是防止反模式 C1（编译错误盲修）的保险丝。

### lx-task-spec — 结构化任务引擎

引导式 3 问（目标是什么？范围是哪些文件？验收条件是什么？）→ 结构化任务输入 → 澄清 → 规划 → 执行 → 验收。它是 lx-todo 和 lx-rpe 之间的桥梁——不需要完整 PRD 的 formal 程度，但又超出了随手修的简单度。

### lx-rpe — 完整的 Feature 开发闭环

9 步闭环：TDD → Code Review → Security Review → Acceptance → Graded Rollback。每一步有独立的验证节点，不可跳过。RPE 输出四份文件——design.md（设计理由）/ spec.md（验收条件）/ executor.md（执行记录）/ qa.md（证据汇总）——形成完整的可审计开发记录 `[已验证: AGENTS.md §RPE 文档体系]`。

### lx-prd — 产品需求生产工艺

6 阶段：Discovery → Uncertainty Scan → Draft → Self-Eval → Expert Review → Polish。不是写出一份"看起来像 PRD"的文档——是通过六层过滤，确保每一行需求都有来源、每一个假设都被标记。

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

底部追加 audit dashboard 摘要——5 源聚合（audit-hooks.sh / harness-smoke-test.sh / hook-production-verify.sh / pre-commit-self-review.sh / doc-sync-check.sh 的最新运行结果）。他不是"看看状态好不好的面板"——他是飞轮（story-12）的数据可视化端。

### lx-varlock — 隐私脱敏代理

物理隔离的隐私守卫。当 AI 需要接触涉及敏感信息的文件（`.env`、credentials、证书），他不是警告 AI "小心"——他**替代** AI 直接接触文件。AI 告诉 varlock 需要什么操作，varlock 代理执行，AI 永远看不到明文 `[已验证: .claude/skills/lx-varlock/SKILL.md]`。

这是对铁律 #6（隐私防线）的最高级物化——不是"请你不要看"，而是"你根本看不到"。

---

## 圣器之间的锁链

锻造所的工具不是孤立的——它们按 L3 流水线编排：

```
lx-prd (产出 PRD)
  → lx-oma-hier (拆解) → lx-oma-split (Feature 拆分)
    → lx-rpe (Feature 开发)
      → lx-tdd-spec (行为矩阵) → lx-test-gen/lx-golang-test (生成测试)
      → lx-code-review (功能审查) + lx-security-review (安全审查)
      → lx-browser-verify (视觉验证)
    → lx-pre-commit (提交门禁)
  → lx-pre-push (推送门禁)
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
  ├─ 完整 feature，需要四文件闭环 → lx-rpe
  │   └─ 上游需求尚未明确 → lx-prd
  │
  ├─ 需要代码审查 → lx-code-review + lx-security-review (并行)
  │
  ├─ 需要测试 → lx-tdd-spec (行为矩阵) → lx-test-gen (代码生成)
  │
  ├─ 需要检查前端视觉 → lx-browser-verify
  │
  ├─ 准备提交 → lx-pre-commit
  │
  ├─ 准备推送 → lx-pre-push
  │
  └─ 看看整体状态 → lx-status
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
