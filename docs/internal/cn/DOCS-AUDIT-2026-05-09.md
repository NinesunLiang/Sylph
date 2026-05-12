# Carror OS 文档审计 — 2026-05-09

## 参考状态
- `.claude/skills/` — **25 个文件**，全部有内容 ✓
- `.claude/hooks/` — **32 个文件**，全部有内容 ✓
- `source/lx-skills-v5/` — 旧/存根目录（**不应视为当前版本**）
- `source/harness-kit/` — 旧/存根目录（**不应视为当前版本**）
- Rev2 审计：`docs/internal/audit-v6.1.8-rev2.md` = 72/100
- 旧审计：`docs/internal/audit-v6.1.8.md` = 40/100（有缺陷）

---

## 待修改文件（含具体变更说明）

### 1. docs/internal/audit-v6.1.8.md（旧版 — 40/100）
**状态：** 已被 rev2 取代。应归档或重写。
- ❌ 引用 `source/lx-skills-v5/` 作为当前技能目录 — **事实错误**。实际技能在 `.claude/skills/`（25 个文件，全部有内容）。
- ❌ 引用 `source/harness-kit/` 作为当前钩子目录 — **事实错误**。实际钩子在 `.claude/hooks/`（32 个文件，全部有内容）。
- ❌ 基于错误目录评估给出 40/100 分。rev2 审计修正目录混淆后正确评分为 72/100。
- ❌ 声称"技能为空"（低分的核心原因）。技能并非空 — `.claude/skills/` 有 25 个包含真实内容的文件。
- **变更：** 添加醒目头部：`[已取代] 请使用 docs/internal/audit-v6.1.8-rev2.md`。或归档为 `audit-v6.1.8-superseded.md`。

### 2. docs/internal/scoring-defense-amplify-governance.md
**状态：** 框架文档存在问题。
- ❌ 在摘要中声称"治理：9.0/10"和"能力：7.5/10" — 与 rev2 审计的 C1-C9 和 E1-E8 评分方法不一致。
- ❌ 该框架使用与 rev2 审计实际应用的评分标准（C1-C9、E1-E8）不同的规则。
- ❌ "总分"75/100 与 rev2 审计得分 72/100 不一致。
- **变更：** 更新以对齐 rev2 审计的评分方法和数字，或重构为与具体得分无关的独立框架文档。

### 3. docs/technical/architecture-review.md
**状态：** 需要针对当前结构更新。
- ❌ 部分地方引用 `source/lx-skills-v5/` — 应引用 `.claude/skills/`。
- ❌ 部分地方引用 `source/harness-kit/` — 应引用 `.claude/hooks/`。
- ❌ 包含与当前三级火箭模型（仅 Harness / Base 版 / Enhanced 版）不匹配的过时架构描述。
- **变更：** 将所有 `source/lx-skills-v5/` 替换为 `.claude/skills/`。将所有 `source/harness-kit/` 替换为 `.claude/hooks/`。更新架构描述以匹配当前的版本模型。

### 4. docs/internal/better-info.md 和 docs/internal/better-info2.md
**状态：** 这些似乎是来自 AI 审查过程的草稿/分析文件。
- ❌ `better-info.md` 引用 `source/lx-skills-v5/` 并暗示这是当前目录。
- ❌ `better-info2.md` 引用 `source/lx-skills-v5/` 并建议重命名 `.claude/skills/`。
- **变更：** 两个文档均基于有缺陷的评估。要么用正确事实重写，要么合并为 `docs/internal/` 下的单一更新分析。

### 5. docs/marketing/industry-benchmark.md
**状态：** 引用不存在的文件。
- ❌ 第 33 行：`[自动化特性验收测试](../tests/auto-feature-test.md)` — 文件存在 ✓（位于 `docs/tests/auto-feature-test.md`）
- ❌ 第 34 行：`[全人工逐项验收测试](../tests/manual-acceptance-test.md)` — 文件存在 ✓（位于 `docs/tests/manual-acceptance-test.md`）
- ✅ 这些路径实际正确，因为它们使用相对于 marketing 文件夹的 `../tests/`。
- **裁决：** 次要问题 — 保持现状，路径能正确解析。

### 6. docs/governance/features.md
**状态：** 引用 internal/ 文件夹中不存在的文件。
- ❌ 第 84 行：`auto-feature-test.md` — 此路径下**不存在**（它在 `docs/tests/`，引用方式不正确）。
- ❌ 第 85 行：`auto-feature-test-log.md` — 此路径下**不存在**（它在 `docs/tests/`）。
- ❌ 第 95 行：`manual-acceptance-test.md` — 此路径下**不存在**（它在 `docs/tests/`）。
- ❌ 第 96 行：`manual-acceptance-test-log.md` — 此路径下**不存在**（它在 `docs/tests/`）。
- **变更：** 更新所有引用为正确相对路径：`../tests/auto-feature-test.md` 等。

### 7. docs/governance/editions.md
**状态：** 数字不一致。
- ❌ 声称"32 个底层 Hook 脚本" — 实际 **32 个钩子** ✓（正确）
- ❌ 声称 Base 版中"10 款自动化审查门禁 Skills" — 对照实际 `.claude/skills/` 验证
- ❌ 声称 Enhanced 版中"14 款主动式工作流 Skills" — 验证数量
- ❌ 多次声称总数"24 款流水线 Skill"，但实际 `.claude/skills/` 有 **25 个文件**
- ❌ 引用 `bash install.sh harness/base/enhanced` — 验证这些命令在当前设置下是否有效
- **变更：** 对照实际目录内容验证技能数量并更新数字。

### 8. docs/marketing/FAQ.md
**状态：** 包含路径引用问题。
- ❌ 第 49 行：`[已验证: /Users/lucas.liang/Desktop/Sylph/Carror_OS/.claude/hooks/context-guard.sh:50-70]` — 这个面向公开的 FAQ 中的绝对路径引用很奇怪。
- **变更：** 移除或概括 `[已验证: ...]` 注释，因为它将内部路径泄露到公开文档中。

### 9. docs/internal/behavior-matrix.md
**状态：** 引用不存在的目录。
- ❌ 将 `harness-kit` 作为组件提及 — 这个旧存根路径不能反映实际情况。
- **变更：** 更新为引用 `.claude/hooks/`。

### 10. docs/internal/execution-types.md 和 execution-types-structure.md
**状态：** 引用旧目录结构。
- ❌ 两者均将 `source/lx-skills-v5/` 引用为技能位置。
- **变更：** 替换为 `.claude/skills/`。

### 11. docs/internal/carror-os-assessment-20260505.md
**状态：** 与基准测试文件的得分不一致。
- ❌ 声称"基准测试得分：69.5/80"但 `docs/internal/benchmark/pass-rate-summary-20260505.md` 显示 Carror OS 为 **72/80**。
- ❌ 引用早于 v6.1.8 的"v4"版本。
- **变更：** 更新得分以匹配基准测试文件（72/80），或注明不一致。

### 12. docs/internal/benchmark/*.md（全部 6 个文件）
**状态：** 准确度参差不齐。
- `pass-rate-summary-20260505.md` — 声称 Carror OS 为 72/80。对照实际 `.claude/skills/` 状态（25 个技能，32 个钩子）验证。
- `shellcheck-20260505.md` — 声称 0 个真实缺陷。对照当前钩子质量验证。
- `bandit-20260505.md` — Python 安全扫描结果。应为最新。
- **变更：** 更新任何引用 `source/lx-skills-v5/` 或技能计数不正确的基准测试分数。

### 13. docs/marketing/PRESS-KIT.md
**状态：** 与实际状态的数字不一致。
- ❌ 声称"30 个应用层 Hook" — 实际 `.claude/hooks/` 中有 **32 个钩子**。
- ❌ 声称"24 个工作流 Skill" — 实际 `.claude/skills/` 中有 **25 个技能**。
- ❌ 引用 `lx-skills` 命名（而非实际路径 `.claude/skills/`）。
- **变更：** 将钩子数量更新为 32，技能数量更新为 25。将 `lx-skills` 引用替换为 `.claude/skills/`。

### 14. docs/marketing/harness-landscape-2026.md
**状态：** 基本准确但有陈旧引用。
- ❌ 引用"30 个注册 Hook" — 应为 **32**。
- ❌ 第 96 行："30 个注册 Hook" — 应为 **32**。
- **变更：** 将钩子数量更新为 32。

### 15. docs/marketing/FAQ.md（续）
**状态：** 数字不一致。
- ❌ 第 60 行："32 个 Hook" — 正确 ✓
- ✅ FAQ 中的总体数字基本准确。

### 16. docs/governance/MIGRATION.md
**状态：** 基本准确。
- ✅ 正确引用 `.claude/hooks/` 和 `.claude/skills/`。
- **裁决：** 质量良好，只需做次要审核。

### 17. docs/governance/TESTING.md
**状态：** 需要做少量验证。
- ✅ 正确引用 `.claude/hooks/`。
- **裁决：** 良好，只需做次要审核。

---

## 保持原样的文件（质量良好）

### 内部文档
- **docs/internal/audit-v6.1.8-rev2.md** — 72/100，方法正确且评分准确 ✓
- **docs/internal/EVIDENCE-BANK.md** — 维护良好的证据收集 ✓
- **docs/internal/DOGFOODING-LOG.md** — 当前的狗粮记录 ✓
- **docs/internal/ac-template.md** — 验收标准模板，有用的参考 ✓

### 治理
- **docs/governance/MIGRATION.md** — 清晰准确的迁移指南 ✓
- **docs/governance/TESTING.md** — 准确的测试文档 ✓

### 营销
- **docs/marketing/v6.1.8-dual-domain-scoring.md** — 更新后的评分（2026 年 5 月 7 日），包含新能力 ✓
- **docs/marketing/FAQ.md** — 基本准确，需要做少量路径清理（见上文 #8）

### 技术
- **docs/technical/benchmark-report.md** — 验证是否为最新版本，否则标记需要更新
- **docs/technical/product-guide.md** — 检查是否引用正确路径

### 测试（位置正确）
- **docs/tests/auto-feature-test.md** — 存在且从 `industry-benchmark.md` 正确引用 ✓
- **docs/tests/manual-acceptance-test.md** — 存在且从 `industry-benchmark.md` 正确引用 ✓
- **docs/tests/final-exam.md** — "期末考试"测试套件，结构良好 ✓
- **docs/tests/auto-feature-test-log.md** — 测试日志模板 ✓
- **docs/tests/manual-acceptance-test-log.md** — 测试日志模板 ✓

### 其他
- **docs/README.md** — 主文档入口点
- **docs/concepts/**（审计追踪、上下文控制、门禁、工作流）— 概念文档
- **docs/guides/**（快速入门、前 10 分钟、面向初学者、面向专家）— 指南文档
- **docs/overview/what-is-carror-os.md** — 产品概览

### 营销归档（保留但标记为历史版本）
- `docs/marketing/archive/` 中的所有文件 — 这些是草稿/历史版本。应明确标记为已归档/已取代，但可保留供参考。

---

## 跨领域问题总结

1. **错误目录引用（严重）：** 多个文件引用 `source/lx-skills-v5/` 和 `source/harness-kit/` 而不是 `.claude/skills/` 和 `.claude/hooks/`。这是第一大问题 — 是损害可信度的事实性错误。

2. **数字不一致：** 钩子数量应为 32（不是 30），技能数量应为 25（不是 24）。影响 PRESS-KIT、editions.md、harness-landscape-2026.md 和其他可能文件。

3. **缺失文件：** `docs/internal/auto-feature-test.md`、`manual-acceptance-test.md`、`launch-plan.md`、`manifesto.md` 不存在但被引用。实际文件位于 `docs/tests/`。

4. **已取代的审计：** 旧的 40/100 审计（audit-v6.1.8.md）应明确标记为已取代，以防止与当前 72/100 rev2 审计混淆。

5. **得分不一致：** 多个文档显示不同的基准测试分数（69.5/80 vs 72/80）。应统一到最新的基准测试编号。

6. **评分框架不匹配：** scoring-defense-amplify-governance.md 框架与实际的 rev2 审计方法不一致。
