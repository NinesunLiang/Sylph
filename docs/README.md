# Carror OS 文档索引

> **版本**：v6.1.8 | **更新日期**：2026-05-02

---

## 目录结构

```
docs/
├── marketing/          ← 宣发材料（预热 + 发布日使用）
│   ├── manifesto.md              产品宣言（博客长文 / Medium / 知乎专栏）
│   ├── README-draft.md           精简版（GitHub README 直接来源 / Product Hunt）
│   ├── industry-benchmark.md     8 维度行业横评白皮书（vs 9 款竞品）
│   ├── harness-landscape-2026.md Agent Harness 行业全景与定位分析
│   └── launch-plan.md            5 周预热排期 + 发布日计划
│
├── technical/          ← 技术文档（用户阅读 / 贡献者参考）
│   ├── product-guide.md          产品指南（三阶段产品结构 + 全特性 + 安装验收）
│   ├── migration.md              数据迁移与无损升级指南
│   ├── one-man-army.md           OMA 多终端并发架构深度解析
│
├── evaluation/         ← 评测与评分
│   └── architecture-review.md    内核/用户态极限评分 + 竞品对比
│
├── internal/           ← 内部模板与参考（不对外发布）
│   ├── ac-template.md            AC 验收条件模板
│   ├── behavior-matrix.md        行为矩阵模板（TDD 用）
│   ├── execution-modes.md        执行模式说明（stepwise/race）
│   ├── execution-types.md        Bug/Feature/Refactor 路径定义
│   └── audit-v6.1.8.md           v6.1.8 质量审计报告
│
└── README.md           ← 本文件

tests/                  ← 测试文档（独立于 docs）
├── auto-feature-test.md          自动化特性验收手册（4 战区）
├── auto-feature-test-log.md      自动化验收战报模板
├── manual-acceptance-test.md     49 项全人工验收清单
├── manual-acceptance-test-log.md 人工验收战报（含已填写记录）
└── final-exam.md                 终极人工审判清单（Dogfooding 前置）
```

---

## 文档分类说明

| 分类 | 用途 | 受众 |
|------|------|------|
| **marketing** | 预热宣发、社区投稿、发布日使用 | 外部用户、社区、媒体 |
| **technical** | 产品使用、架构理解、贡献者参考 | 用户、开发者、贡献者 |
| **evaluation** | 能力评分、竞品对比 | 内部评估、投资者、技术决策者 |
| **internal** | Skill 内部模板、审计记录 | 仅内部使用 |
| **tests** | 验收测试手册与战报 | QA、Dogfooding |

---

## 重复文档处理记录

| 原文件 | 处理 | 原因 |
|--------|------|------|
| `source/auto-feature-test.md` | 已删除 | 与根目录版本完全相同 |
| `source/auto-feature-test-log.md` | 已删除 | 同上 |
| `source/final-exam.md` | 已删除 | 同上 |
| `source/manual-acceptance-test.md` | 已删除 | 同上 |
| `source/manual-acceptance-test-log.md` | 已删除 | 同上 |
| `packages/final-exam.md` | 已删除 | 同上 |
| `editions.md` + `features-reference.md` | 合并为 `product-guide.md` | 内容 80% 重叠 |
| `PRESS-KIT.md` | 重命名为 `README-draft.md` | 明确其 GitHub README 来源定位 |
| `architecture-review.md` | 已整合 | 两个版本评分拼接 → 统一为一份连贯文档 |

---

## 宣发材料与技术文档的关系

```
manifesto.md ──────────── 完整版产品宣言（博客长文，深度叙事）
    ↓ 精简
README-draft.md ────────── 精简版（GitHub README / Product Hunt / Show HN）
    ↓ 数据支撑
industry-benchmark.md ─── 量化评分（8 维度 × 9 款竞品）
    ↓ 行业视角
harness-landscape-2026.md 行业趋势分析（Agent Harness 全景）
    ↓ 执行计划
launch-plan.md ─────────── 5 周预热排期 + 发布日计划
```
