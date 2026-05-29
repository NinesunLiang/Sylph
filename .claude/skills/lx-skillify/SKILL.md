---
name: lx-skillify
version: v1.0.0
description: "将自然语言描述转化为生产级 lx-* skill。6 阶段管道。"
when_to_use: "Use when user says 'skillify', '创建 skill', '生成 skill', /skillify"
argument-hint: "[描述，例如：'创建一个审查 Dockerfile 的 skill']"
harness_version: ">=6.3.0"
status: draft
role: "Skill 自动生成器 — 6 阶段管道：澄清→分析→生成→创建→验证→注册"
execution_mode: stepwise
triggers:
  - "/skillify"
  - "skillify"
  - "创建 skill"
---

# lx-skillify — 技能自动生成器

> **一次澄清 → 全自动生成 → 验证 → 注册。**

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| interactive_prompt | `../../nodes/interactive_prompt.md` | 澄清窗口 |
| target_resolver | `../../nodes/target_resolver.md` | 解析目标域 |
| context_collector | `../../nodes/context_collector.md` | 收集模式+注册表 |
| explore | `../../nodes/explore.md` | 找参考技能 |
| generator | `../../nodes/generator.md` | 生成 SKILL.md |
| report_generator | `../../nodes/report_generator.md` | 报告 |
| behavior_rules | `../../nodes/behavior_rules.md` | 行为约束 |

Schema: verdict / finding / scan_report / severity / context_summary → `../../schemas/atomic/`

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/phases-clarify-analyze-generate.md` | phases clarify analyze generate 阶段 |
| `references/phases-create-validate-register-report.md` | phases create validate register report 阶段 |
| `references/reference_skill_selector.md` | reference_skill_selector 阶段 |
| `references/skill_generation_prompts.md` | skill_generation_prompts 阶段 |

> 降级升级: @../reference/oma/degradation-escalation.md
> 裁决链: @../reference/oma/decision-chain.md
> 执行工作流: @../reference/oma/execution-workflow.md

## 状态机

```
CLARIFY → ANALYZE → GENERATE → CREATE_FILES → VALIDATE → REGISTER → REPORT
  ↑         ↑                        ↓ fail<3         ↓
  └─ reprompt(max2)                  └→ back GENERATE ─┘
```

降级：VALIDATE fail≥3 → blocked | CLARIFY 不足 → reprompt max2

## 边界声明

| 不做 | 原因 |
|------|------|
| git commit/push | 硬边界 |
| 修改已有技能 | 仅创建 |
| 删除/重命名 | 破坏性操作 |
| 虚构节点/Schema | Phase 4 阻断 |

## 执行流程

### Phase 0-2: 澄清→分析→生成 → `@references/phases-clarify-analyze-generate.md`

4 问澄清 → 探索参考技能 + 节点/Schema 选择 → 按 TEMPLATE.md 生成 SKILL.md（≤300行）。

### Phase 3-6: 创建→验证→注册→报告 → `@references/phases-create-validate-register-report.md`

scripts/references 条件创建 → validate-skill.sh + validate_skill_refs.py → feature-registry + skills-catalog 注册 → 完成报告。

## 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| 描述模糊 | 重新提问 max2 | 部分信息生成 |
| 无参考技能 | TEMPLATE.md 默认 | 手动指定参考 |
| 验证失败 1-2轮 | 自动修复 | 标记需人工 |
| 验证失败 3轮 | 停止 | 输出违规详情 |
| 技能名占用 | 提示冲突 | 建议替代名 |
| validate 不可用 | 自动验证 | 手动 11 条检查 |

## lx-goal 集成

Phase 0 人类窗口期 → Phase 1-6 lx-goal 全自动 → git commit 硬边界。
