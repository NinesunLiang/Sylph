# 技能目录

> **所属层级**: 3-机制(血肉层) — 26 个 Skill 能力目录

> 基于源码 `.claude/skills/` 实测提取。共 26 个技能，按功能域分类。

## 分类速查

| 分类 | 技能数 | 用途 |
|------|--------|------|
| [执行模式](#执行模式) | 2 | 无人值守自主执行 |
| [OMA 管线](#oma-管线) | 4 | PRD→拆解→编排→治理 |
| [质量门禁](#质量门禁) | 2 | 提交前/推送前检查 |
| [任务管理](#任务管理) | 4 | todo→task-spec→RPE→stepwise |
| [代码审查](#代码审查) | 1 | 通用代码审查 |
| [测试](#测试) | 2 | 测试生成/根因分析 |
| [基础设施](#基础设施) | 6 | 状态面板/隐私代理/蜂群/一致性/验证 |
| [审计与审判](#审计与审判) | 3 | Oracle 门禁/增强审查/自食狗粮 |
| [系统运维](#系统运维) | 1 | 自更新 |
| [技能创建](#技能创建) | 2 | skillify/learner |

---

## 执行模式

自主执行模式，安全网降级，不暂停问人。

| 技能 | 一句话 | 触发词 |
|------|--------|--------|
| `/lx-ghost` | 方向驱动的增量探索。给方向，AI 自主一步步探索修复 | `ghost mode`、`幽灵模式` |
| `/lx-goal` | 目标驱动的自主执行。给目标，AI 执行到完，完成后报告 | `goal mode`、`目标模式`、`无人值守` |

**选择指南**：
- 方向模糊、需要迭代探索 → `/lx-ghost`
- 目标明确、知道要什么结果 → `/lx-goal`

---

## OMA 管线

One-Man Army — 一人成军开发管线，从 PRD 到 feature 的全流程。

| 技能 | 一句话 | 触发词 |
|------|--------|--------|
| `/lx-oma-hier` | 超大型 PRD 按功能域 MECE 拆分为 Sub PRD | `分层 PRD`、`hier` |
| `/lx-oma-split` | Sub PRD 拆解为正交 feature 分支 | `一人成军`、`split` |
| `/lx-oma-orch` | 4-skill 管线编排（状态/推进/Oracle 门禁/并行管理） | `管线编排`、`orchestrator` |
| `/lx-oma-gov` | PRD 变更时增量同步，冲突裁决，漂移检测 | `PRD 治理`、`reconcile` |

**典型流程**：`hier` 拆大 PRD → `split` 拆 feature → `orch` 编排执行 → `gov` 治理变更。

---

## 质量门禁

提交和推送前的自动化检查。

| 技能 | 一句话 | 触发词 |
|------|--------|--------|
| `/lx-pre-commit` | 项目类型检测 → 编译 → 测试 → 代码审查 | `pre-commit`、`提交前检查` |
| `/lx-pre-push` | commit message 校验 → 测试覆盖 → 安全扫描 → 判定 | `pre-push`、`推送前检查` |

**说明**：编译/测试等检测由 AI 直接执行，`lx-pre-commit` 和 `lx-pre-push` 负责结果解读和路由决策。

---

## 任务管理

从轻量 bug 修复到完整 PRD 驱动的分级任务系统。

| 技能 | 复杂度 | 适用场景 |
|------|--------|----------|
| `/lx-todo` | L1 | 轻量 5 步循环：捕获→分诊→修复→验证→关闭。≤3 文件 |
| `/lx-task-spec` | L2 | 中等复杂度。3 问引导 → AC 驱动 → 澄清→规划→执行→验收 |
| `/lx-rpe` | L3 | 完整 RPE 驱动 feature 开发循环：TDD→审查→安全→验收 |

**选择指南**：
- 修个 typo / 单行 bug → `/lx-todo`
- 需要精确 AC 但不需完整 PRD → `/lx-task-spec`
- 新 feature / 架构变更 → `/lx-rpe`
- 需要 PRD（被 `/lx-oma-split` 替代） → `/lx-oma-split`

---

## 代码审查

| 技能 | 审查对象 | 规则数 |
|------|----------|--------|
| `/lx-code-review` | 通用代码 | 8 类 39 条（错误处理/并发/接口/性能/可观测性） |

---

## 测试

| 技能 | 一句话 |
|------|--------|
| `/lx-test-gen` | 语言无关测试生成。自动检测语言（Go/TS/Python），路由到对应模式 |
| `/lx-root-cause-analysis` | 5-Why 根因追踪，证据链+置信度评分+免疫防御 |

---

## 基础设施

| 技能 | 一句话 |
|------|--------|
| `/lx-status` | 健康面板 v3.0：Token 节省/任务通过率/拦截错误/知识点 4 面板 + audit 摘要 |
| `/lx-varlock` | 隐私脱敏代理。敏感信息（密码/API Key/Token）绝不泄露到 AI 上下文 |
| `/lx-race` | 蜂群协调层：注册子任务→派发→收集→报告。复用 team 调度+OMA Lock |
| `/lx-stepwise` | 逐步攻坚模式：高难度 bug 单步推进，每步需验证，不可跳过 |
| `/lx-sync` | 变更后一致性检查：frontmatter↔registry 漂移、source mirror 同步等 6 项 |
| `/lx-validate-skill` | 验收新 skill 是否遵循原子化架构规则（11 项检查） |

## 审计与审判

| 技能 | 一句话 |
|------|--------|
| `/lx-oracle` | Oracle 常规守门员 — 每阶段门禁独立审查，裁决 ACCEPT/REVISE/REJECT |
| `/lx-oracle-v2` | Oracle v2 — 增强版审查，对抗性审查 + 设计盲区扫描 |
| `/lx-dogfood` | 自食狗粮 — 用 Carror OS 验证自身，收集 token/hook 拦截率报告 |

## 系统运维

| 技能 | 一句话 |
|------|--------|
| `/update-carror-os` | 自更新圣器 — 跨版本升级时确保 hooks/skills/scripts 版本一致 |

---

## 技能创建

| 技能 | 一句话 | 触发词 |
|------|--------|--------|
| `/skillify` | 将自然语言描述转化为生产级 lx-* skill（6 阶段管道） | `skillify`、`创建 skill`、`生成 skill` |
| `/learner` | 从对话中检测重复模式并提取为可重用 lx-* skill，附带来源文档 | `learner`、`extract skill`、`从对话中学习` |

---

## 技能关系图谱

```
任务复杂度递增 →
  /lx-todo (L1, 轻量)
    → /lx-task-spec (L2, 中等)
      → /lx-rpe (L3, 完整 feature)

OMA 管线流 →
  /lx-oma-hier (拆大 PRD)
    → /lx-oma-split (拆 feature)
      → /lx-oma-orch (编排执行)
        → /lx-oma-gov (治理变更)

门禁链 →
  /lx-pre-commit (提交前)
    → /lx-pre-push (推送前)

质量保障四件套 →

自主执行 →
  /lx-ghost (方向驱动探索)
  /lx-goal (目标驱动执行)
```

---

## 已废弃 / 不在本目录的技能

以下技能通过 `omc-reference` skill 管理，非 `lx-` 前缀，属于 OMC 基础设施层：

`autopilot` `ultrawork` `ralph` `team` `ccg` `ralplan` `deep-interview` `ai-slop-cleaner` `omc-setup` `omc-doctor` `omc-plan` 等

完整列表见 `/omc-reference`。

## lx-purify — 思想纯度审计
三 Pass 审计（哲学→铁律→现状）+ 双法官审核。runtime hook: pretool-purify-gate.sh。
