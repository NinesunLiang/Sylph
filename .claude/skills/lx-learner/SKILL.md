---
name: lx-learner
version: v1.0.0
description: "从对话中提取可重复工作流并生成 lx-* skill。检测模式 → 提议提取 → 生成技能 → 附带来源文档。"
when_to_use: "Use when user says 'learner', 'extract skill', '从对话中学习', /learner, or AI detects repeated workflow patterns"
argument-hint: "[可选：指定要提取的重复任务描述。留空则自动检测对话模式]"
harness_version: ">=6.3.0"
status: draft
role: "技能学习者 — 从对话模式中检测、提议并提取可重用 lx-* skill，附带来源文档"
execution_mode: stepwise
triggers:
  - "/learner"
  - "learner"
  - "extract skill"
  - "从对话中学习"
---
# lx-learner — 对话技能提取器

> **从真实使用中生长技能。** AI 观察重复模式 → 提议提取 → 用户确认 → 全自动生成 → 附带来源证明。

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| scanner | `../../nodes/scanner.md` | 扫描对话日志检测重复模式 |
| interactive_prompt | `../../nodes/interactive_prompt.md` | 展示证据 + 确认提取 |
| explore | `../../nodes/explore.md` | 查重 |
| generator | `../../nodes/generator.md` | 生成 SKILL.md |
| report_generator | `../../nodes/report_generator.md` | 提取报告 |

| Schema | 路径 |
|--------|------|
| verdict / finding / scan_report / severity / context_summary | `../../schemas/atomic/` |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/pattern_detection_guide.md` | pattern_detection_guide 阶段 |
| `references/phase-detect.md` | phase detect 阶段 |
| `references/phase-document.md` | phase document 阶段 |
| `references/phase-propose.md` | phase propose 阶段 |
| `references/phase-report.md` | phase report 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
DETECT → PROPOSE → GENERATE → VALIDATE → DOCUMENT → REPORT
  ↑       ↓ reject     ↑ fail<3     ↓
  └───────┴─────────────┴────────────┘
```

## 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| 未检测到重复模式 | 退出 | 提示用 /skillify 手动创建 |
| 置信度低（<5） | 标记附带发现 | 建议手动 /skillify |
| 用户拒绝提取 | 退出 | 记录模式供未来参考 |
| 生成失败 | 复用 skillify 降级 | 同 skillify Phase 2-4 |
| 已有同名技能 | 警告冲突 | 建议替代名称 |

## 边界声明

| 不做的操作 | 原因 |
|-----------|------|
| 未经确认自动提取 | 用户必须批准 |
| 修改已有技能 | 仅创建新技能 |
| 从对话推断凭据/密钥 | DLP 安全边界 |
| git commit/push | 硬边界 |
| 提取单次出现的操作 | 至少需要 3 次证据 |

## 执行流程

### Phase 0: DETECT → `@references/phase-detect.md`

扫描对话上下文 → 模式评分（0-10）→ ≥5 可提取。

### Phase 1: PROPOSE → `@references/phase-propose.md`

查重 → 展示证据 → 用户确认（是/修改方案/忽略）。

### Phase 2: GENERATE

复用 lx-skillify Phase 1-3 生成管道。Learner 专用规则：description/when_to_use/triggers 从对话实际使用痕迹中提取，所有步骤可追溯到对话上下文。

### Phase 3: VALIDATE

```bash
bash .claude/scripts/validate-skill.sh lx-{name}
python3 .claude/scripts/validate_skill_refs.py
```

通过 → Phase 4。失败 → 回 Phase 2（max 3 轮）。

### Phase 4: DOCUMENT → `@references/phase-document.md`

创建 `references/conversation_provenance.md`（原始证据 + 提取理由 + 与已有技能关系）。

### Phase 5: REPORT → `@references/phase-report.md`

输出提取报告（模式/技能/验证/注册/下一步）。

## 与 lx-skillify 的关系

| 维度 | lx-skillify | lx-learner |
|------|-----------|-----------|
| 触发 | 用户主动描述需求 | AI 被动检测对话模式 |
| 输入 | 自然语言描述 | 对话上下文（实际痕迹） |
| Phase 0 | 4 问澄清 | 扫描对话日志 |
| Phase 1 | 分析现有 skill 模式 | 展示证据 + 用户确认 |
| Phase 2-4 | 生成 → 验证 → 注册 | 复用 skillify |
| 特有 | — | conversation_provenance.md |
