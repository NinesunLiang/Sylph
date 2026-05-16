---
name: lx-learner
version: v1.0.0
description: "从当前对话中提取可重复工作流并生成 lx-* skill。检测模式 → 提议提取 → 生成技能 → 附带来源文档。"
when_to_use: "Use when user says 'learner', 'extract skill', 'learn from', '从对话中学习', /learner, or when AI detects repeated workflow patterns during a session."
model: sonnet
argument-hint: "[可选：指定要提取的重复任务描述。留空则自动检测对话模式]"
paths:
  - ".claude/skills/lx-*/SKILL.md"
harness_version: ">=1.1.0"
status: draft
role: "技能学习者 — 从对话模式中检测、提议并提取可重用 lx-* skill，附带来源文档"
execution_mode: stepwise
triggers:
  - "/learner"
  - "learner"
  - "extract skill"
  - "从对话中学习"
  - "学习工作流"
---

# lx-learner — 对话技能提取器

> **从真实使用中生长技能。** AI 在对话中观察重复模式 → 提议提取 → 用户确认 → 全自动生成 → 附带来源证明。

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| scanner | `../../nodes/scanner.md` | Phase 0 扫描对话日志检测重复模式 |
| interactive_prompt | `../../nodes/interactive_prompt.md` | Phase 1 展示证据 + 确认提取 |
| explore | `../../nodes/explore.md` | Phase 1 查重 — 防止生成与已有技能重复 |
| generator | `../../nodes/generator.md` | Phase 2 基于检测到的模式生成 SKILL.md |
| report_generator | `../../nodes/report_generator.md` | Phase 5 提取报告 |
| behavior_rules | `../../nodes/behavior_rules.md` | 全程行为约束 |

### 引用的通用 Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | 提取判定 |
| finding | `../../schemas/atomic/finding.yaml` | 检测到的模式/证据 |
| scan_report | `../../schemas/atomic/scan_report.yaml` | 对话模式扫描报告 |
| severity | `../../schemas/atomic/severity.yaml` | 模式置信度分级 |
| context_summary | `../../schemas/atomic/context_summary.yaml` | 对话上下文摘要 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途 |
|------|------|------|
| 统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各阶段输出格式统一 |

### 状态机
本 skill 使用**私有 5 阶段状态机**，不引用 `orchestrator.md`。原因：learner 遵循独特的 detect→propose→confirm→generate→document 链条，其核心需要 AI 语义模式检测，非标准审查循环或门禁链。

```
DETECT → PROPOSE → GENERATE → VALIDATE → DOCUMENT → REPORT
  ↑         ↓ (reject)    ↑ (fail, <3)     ↓
  └─────────┴──────────────┴────────────────┘
```

降级路由：
- PROPOSE reject → DONE/noop（用户拒绝提取）
- VALIDATE fail (retry < 3) → GENERATE（修复）
- VALIDATE fail (retry ≥ 3) → DONE/blocked
- DETECT 无模式 → DONE/noop（无可提取内容）

### 私有节点
本 skill 无私有节点。

### 边界声明（不做什么）
| 不做的操作 | 原因 | 推荐替代 |
|-----------|------|---------|
| 未经确认自动提取技能 | 用户必须批准提取提议 | Phase 1 使用 AskUserQuestion |
| 修改已有技能 | 仅创建新技能，不修改已有 | 手动编辑或使用 /skillify |
| 从对话中推断凭据/密钥作为模式 | DLP 安全边界 | 使用 lx-varlock 处理敏感数据 |
| git commit/push | 硬边界 | 用户审查后手动提交 |
| 提取单次出现的操作 | 至少需要 3 次重复证据 | 标记为附带发现，不生成技能 |

---

## 执行流程

### Phase 0: 模式检测（DETECT）

加载 `@../../nodes/scanner.md`。扫描当前对话上下文，寻找可提取的重复模式。

**检测信号**（按置信度排序）：

| 模式类型 | 检测信号 | 最小证据 |
|---------|---------|---------|
| **重复工作流** | 用户多次发出同类指令（≥3 次） | 3 个上下文引用显示相同步骤序列 |
| **重复修复** | 同类 bug 用同样方法修了 ≥3 次 | 3 个文件引用：相同结构的代码变更 |
| **重复分析** | 同类分析/审查迭代 ≥3 次 | 3 个上下文提及 |
| **自定义流程** | 用户设计了 3+ 步骤的重复协议 | 3+ 个确认循环 |

**模式评分**（0-10）：
- 重复次数: 3次=3分, 5次=5分, 10+次=8分
- 步骤可结构化程度: 高=+2, 中=+1, 低=0
- 通用性（非项目特定）: 高=+2, 中=+1, 低=0

评分 ≥5 → 可提取。评分 <5 → 标记为附带发现。

**若用户指定了目标**：直接进入 Phase 1，跳过自动检测。

**输出**: `detected_patterns`:
```json
{
  "patterns": [
    {
      "type": "repeated_workflow",
      "description": "用户重复执行 Dockerfile 安全审查",
      "repeat_count": 5,
      "confidence": "high",
      "score": 8,
      "evidence": [
        "当前对话第 3 轮: 审查 Dockerfile 的 COPY --from",
        "当前对话第 7 轮: 检查 Dockerfile 的 RUN 指令",
        "当前对话第 12 轮: 扫描 Dockerfile 的 EXPOSE 端口"
      ]
    }
  ],
  "count": 1
}
```

**若无模式**: 输出 "本次对话未检测到可提取的重复模式"，退出。

### Phase 1: 提议提取（PROPOSE）

加载 `@../../nodes/interactive_prompt.md` + `@../../nodes/explore.md`。

**Step 1.1: 查重** — 探索 `.claude/skills/` 检查是否已有类似技能。若存在 → 警告用户。

**Step 1.2: 展示证据** — 使用 AskUserQuestion：

```
🔍 检测到重复模式：[类型]

证据：
1. [描述 + 上下文引用]
2. [描述 + 上下文引用]
3. [描述 + 上下文引用]

该操作在本次对话中出现了 {N} 次。

提取为可重用 skill？
```

选项：
- **"是，提取 lx-{suggested_name}"** → 继续 Phase 2
- **"修改方案"** → 用户自定义技能名称/范围 → 继续 Phase 2
- **"不，忽略"** → 退出

**若用户选择"修改方案"**：收集技能名称、额外触发词、范围调整。

**输出**: `extraction_plan`:
```json
{
  "proposed_name": "lx-dockerfile-review",
  "scope": "Dockerfile 安全漏洞和最佳实践审查",
  "triggers": ["审查 dockerfile", "dockerfile check"],
  "confirmed": true
}
```

### Phase 2: 生成技能（GENERATE）

加载 `@../../nodes/generator.md`。**复用 lx-skillify 的 Phase 1-3 生成管道**，但有关键差异：

**Learner 专用生成规则**:
1. `description` — 衍生于检测到的模式总结
2. `when_to_use` — 衍生于触发模式的用户短语
3. `triggers` — 从对话中实际使用的短语提取
4. 执行流程步骤 — 从对话中观察到的步骤序列重建
5. 所有步骤必须可追溯到对话上下文（标注来源）

**与 skillify 共享的规则**:
- 同样必填 frontmatter 字段
- 同样引用真实 nodes/schemas 路径
- 同样遵循 TEMPLATE.md 结构
- 同样 ≤300 行限制

**Skillify 管道映射**:
| skillify Phase | learner 如何使用 |
|---------------|-----------------|
| Phase 1 (Analyze) | 用对话上下文替代用户描述 → 选参考技能 |
| Phase 2 (Generate) | 相同逻辑，但步骤描述引用对话证据 |
| Phase 3 (CreateFiles) | 相同逻辑 |

### Phase 3: 验证（VALIDATE）

**与 lx-skillify Phase 4 完全相同**：
```bash
bash .claude/scripts/validate-skill.sh lx-{name}
python3 .claude/scripts/validate_skill_refs.py
```
- 通过 → Phase 4
- 失败 → 回 Phase 2 修复（max 3 轮）

### Phase 4: 来源文档（DOCUMENT）

Learner 特有阶段。创建 `references/conversation_provenance.md`：

```markdown
# 来源文档：lx-{name}

提取日期：{date}
提取自：当前对话

## 原始证据

### 证据 1
> [摘录对话，展示第一次出现]

### 证据 2
> [摘录对话，展示第二次出现]

### 证据 3
> [摘录对话，展示第三次出现]

## 提取理由
在本次对话中观察到此工作流重复 {N} 次。
每次出现：[简述模式如何重复]

## 与已有技能的关系
- 相似技能：{如有}
- 区别：{为何这是独特的}
```

### Phase 5: 报告（REPORT）

加载 `@../../nodes/report_generator.md`。

```
## /learner 提取报告 ✅

### 检测到的模式
- 类型：{pattern_type}
- 重复次数：{N}
- 置信度：{high/medium}

### 创建的技能
- lx-{name}: .claude/skills/lx-{name}/
  - SKILL.md ({N} 行)
  - references/conversation_provenance.md

### 验证结果
- 结构检查：{通过/失败}（{N} 轮修复）
- 引用检查：{通过/失败}

### 注册
- feature-registry.yaml: 已更新
- skills-catalog.md: 已更新

### 下一步
1. 审查 SKILL.md — 确保提取的行为匹配你的意图
2. 审查来源文档 — 确认对话摘录准确
3. 手动 git add .claude/skills/lx-{name}/
4. 或用 /lx-{name} 立即测试
```

---

## 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 未检测到重复模式 | 退出，输出"无可提取内容" | 提示使用 /skillify 手动创建 |
| 检测到模式但置信度低（score <5） | 标记为附带发现 | 展示证据但建议手动 /skillify |
| 用户拒绝提取 | 退出 | 记录模式供未来参考 |
| 生成管道失败 | 复用 skillify 降级策略 | 同 skillify Phase 2-4 |
| 已有同名技能 | 警告冲突 | 建议替代名称 |
| 对话上下文不足以重建步骤 | 标记哪些步骤缺少证据 | 用 AI 推断补充（标注为推测） |

## 错误恢复与中止条件

| 场景 | 动作 |
|------|------|
| 对话上下文 <3 轮 | 退出 — 上下文不足以检测模式 |
| 检测到的所有模式置信度均 <5 | 退出 — 标记附带发现 |
| Phase 2 生成的技能引用虚构路径 | Phase 3 阻断 — 回 Phase 2 修复 |
| 用户在 Phase 1 中止 | 保留 extraction_plan，后续可恢复 |

---

## 与 lx-goal 集成

- **Phase 0 和 Phase 1**: 需要人类确认（展示证据 + 批准提取）
- **确认后 Phase 2-5**: 可在 lx-goal 模式全自动运行
- **硬边界**: 与 skillify 相同 — 无 git commit

## 与 lx-skillify 的关系

| 维度 | lx-skillify | lx-learner |
|------|-----------|-----------|
| 触发方式 | 用户主动描述需求 | AI 被动检测对话模式 |
| 输入 | 自然语言描述 | 对话上下文（实际使用痕迹） |
| Phase 0 | 4 问澄清 | 扫描对话日志 |
| Phase 1 | 分析现有 skill 模式 | 展示证据 + 用户确认 |
| Phase 2-4 | 生成 → 验证 → 注册 | 复用 skillify Phase 2-4 |
| 特有产出 | — | conversation_provenance.md |
| 优势 | 精确控制 | 从真实需求生长 |
