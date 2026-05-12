# Carror OS 文档索引

> **版本**：v6.1.9 | **更新日期**：2026-05-13

---

## 目录结构

```
docs/
├── overview/            ← 产品概述
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── marketing/           ← 宣发材料
│   ├── cn/                         中文版
│   ├── us/                         英文版
│   └── archive/                    原始 Youdao 笔记归档
│
├── guides/              ← 用户引导
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── concepts/            ← 核心概念
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── governance/          ← 版本与治理
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── technical/           ← 技术文档
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── internal/            ← 内部记录（不对外发布）
│   ├── cn/                         中文版
│   ├── us/                         英文版
│   └── benchmark/                  安全基准扫描结果
│
├── test/                ← 交叉验证计划
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── tests/               ← 验收测试手册
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── reference/           ← 参考文档
│   ├── cn/                         中文版
│   └── us/                         英文版
│
├── pipeline-orchestration.md    ← PRD 管线编排（跨 skill 全生命周期）
└── README.md            ← 本文件
```

---

## 文档分类

| 分类 | 用途 | 受众 | 语言 |
|------|------|------|------|
| **overview** | 产品概述 | 首次接触用户 | cn + us |
| **marketing** | 宣发、社区投稿、发布日 | 外部用户、社区、媒体 | cn + us |
| **guides** | 用户引导、快速上手 | 新手用户 | cn + us |
| **concepts** | 核心概念解释 | 想深入理解的用户 | cn + us |
| **governance** | 版本说明、特性参考 | 用户、贡献者 | cn + us |
| **technical** | 架构分析、技术评估 | 开发者、技术决策者 | cn + us |
| **internal** | 审计记录、模板 | 仅内部使用 | cn + us |
| **test** | 交叉验证计划 | QA、Dogfooding | cn + us |
| **tests** | 验收测试手册 | QA、Dogfooding | cn + us |
| **reference** | 已知限制、反馈模板 | 所有用户 | cn + us |

---

## 文档关系

```
manifesto.md ──────────── 完整版产品宣言
    ↓ 精简
README-draft.md ────────── 精简版（GitHub README / Product Hunt）
    ↓ 数据支撑
industry-benchmark.md ─── 量化评分
    ↓ 引导
onboarding-guide.md ───── 首次使用引导（起点）
    ↓ 深度
first-10-minutes.md ───── 快速体验
quickstart.md ─────────── 极速启动
    ↓ 进阶
for-experts.md ────────── Enhanced 版激活
concepts/ ─────────────── 理解各机制原理
```

> 每个文档维度均提供 **cn/**（中文）和 **us/**（英文）双语版本。
> 无对应语种的文件将由 AI 优化翻译后补全。
