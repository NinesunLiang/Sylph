---
name: lx-code-review
version: v4.1.0
description: "代码审查 — 通用框架。支持语言专项规则按需加载。"
when_to_use: "Use after writing code, before tests/commit. Trigger: 'review code', 'code review', /lx-code-review."
argument-hint: "[file path, git ref, or function name]"
harness_version: ">=6.3.0"
status: stable
role: "Code quality reviewer — 8 categories, 39 rules"
execution_mode: stepwise
triggers:
  - "/lx-code-review"
  - "review code"
  - "code review"
dependencies:
  pyyaml: ">=6.0,<7.0"
  jsonschema: "==4.17.3"
---

# lx-code-review — 通用代码质量审查

## 零、增量 Review 模式

每次 review 优先检测变更范围。支持多种基准：

| 范围 | 命令 | 适用场景 |
|------|------|---------|
| 工作区变更 | `git diff HEAD` | 开发中（默认） |
| Staged 变更 | `git diff --cached` | commit 前审查 |
| 当前分支 vs main | `git diff main...HEAD` | PR 审查 |
| Merge base | `git diff $(git merge-base HEAD main)` | 跨分支审查 |
| 指定范围 | `--range=<from>..<to>` | 特定 commit 段 |
| 全量 | `--full` | 首次入库/全面审计 |

报告必须包含：base_ref / head_ref / changed_files_count / excluded_files。

## 模式开关

| 模式 | 行为 |
|------|------|
| `report-only` | 仅输出报告，不做任何修改 |
| `fix-safe` | 自动应用 safe 级修复，review/suggest 仅报告 |
| `fix-with-confirmation` | 所有修复生成 patch 待确认 |
| `strict` | 全部阻断（含 formatter），通过后方可继续 |
| `fast` | 跳过深度分析（依赖图/跨文件），仅扫描变更文件 |
| `full` | 全量深度分析 |

**模式冲突规则**（以下组合禁止/需明确优先级）：
- `report-only` 优先级最高：任何模式下若同时指定 report-only，禁止写文件
- `strict` 禁止将 build/schema/typecheck/test 降级为通过
- `fast` 允许缩小扫描范围，但必须声明 skipped_checks
- `full` 覆盖 fast
- `fix-with-confirmation` 覆盖 fix-safe 的自动确认
- `report-only` + `fix-safe`/`fix-with-confirmation` 互斥（违反 report-only 契约）

## Auto-Fixer 安全分级

每个修复等级定义允许和禁止操作：

```yaml
autofix_policy:
  safe:
    allowed:
      - formatting-only（缩进/空格/换行）
      - typo-in-comments（注释拼写）
      - mechanical import cleanup（verifier 通过后）
    forbidden:
      - public API 变更
      - 行为/语义变更
      - 依赖变更
      - 数据迁移/schema 变更
    action: auto_apply
  review:
    requires:
      - show_diff（展示完整 diff）
      - user_confirmation
      - verifier_pass_or_explicit_override
    action: generate_patch, wait_confirm
  suggest:
    action: report_only（仅报告不修改）
```

## 错误降级策略

单节点失败 **不阻断** 整个 pipeline：

| 节点 | 失败行为 | 降级后要求 |
|------|---------|-----------|
| scanner | 跳过该扫描器，继续其他扫描器 | 报告标记 skipped_scanner |
| context_collector | 使用已有上下文继续 | confidence 不得为 high |
| auto_fixer | 降级为 suggest（仅输出建议） | 报告标记 fix_degraded |
| verifier | 视验证项而定（见下方规则） | — |
| report_generator | 输出 partial report | 标明 incomplete |

**Verifier 降级规则**（阻断矩阵优先级高于节点降级）：
- build/schema 失败：**不可降级**为普通 warn，只能生成 partial report，标记 review_inconclusive
- typecheck/test 失败：可按模式降级，但必须降低总置信度（max confidence → medium）
- formatter/lint 失败：可降级为 warn，无置信度影响
- 降级后必须在报告中声明：`degraded_verifiers: [build, schema]`

## Verifier 阻断矩阵

| 验证项 | 失败行为 | 可降级 |
|--------|---------|--------|
| formatter | 可自动修复或提示，不阻断 | ✅ 是 |
| lint | 中风险阻断（建议确认） | ✅ 是 |
| typecheck | 高风险阻断（必须确认） | ⚠️ 按模式 |
| unit tests | 高风险阻断（必须确认） | ⚠️ 按模式 |
| build | 高风险阻断（必须确认） | ❌ 否 |
| schema validation | 必须阻断（结构错误） | ❌ 否 |

## Confidence 计算规则

```yaml
confidence_rules:
  base_levels:
    - evidence_direct（有 grep/ast-grep 直接证据）: high
    - evidence_inferred（间接推导）: medium
    - evidence_suspicion（可疑模式无确认）: low
  propagation:
    - context_collector 降级后 → confidence 不得为 high
    - verifier partial 后 → auto_fix 不得超过 suggest
    - scanner 失败 → 该扫描器产出 confidence 降一级
    - 多个证据合并 → 取最低 confidence
  output:
    - low_confidence + critical_severity → 必须在报告中解释原因
    - confidence 字段不得为空
```

## 原子化声明

| 节点 | 路径 |
|------|------|
| target_resolver / context_collector / scanner / auto_fixer / verifier / report_generator / behavior_rules | `../../nodes/` |

Schema: scan_target / severity / finding / scan_report / fix_record / verdict → `../../schemas/atomic/`

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/auto-fix-templates.md` | auto fix templates 阶段 |
| `references/rules-catalog.md` | rules catalog 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
collect_context → scan → fix → re-scan → done
```

## 执行流程

### Step 0: 入口
规范文件自检（kernel.md / go-style-guide.md）→ 缺失不阻塞，用内置规则 fallback。无参数 → 引导式问答。

### Step 1-2: 解析 + 收集
解析审查目标（过滤 `*_test.go`/`vendor/`/`*.pb.go`）→ 收集 Go 版本/框架类型/项目规范/已知问题。

### Step 3: 8 类并行扫描 → `@references/rules-catalog.md`
39 条规则（A-H），每条必须执行实际 grep/ast-grep，引用原始输出。强证据协议，不可用描述替代。

### Step 4: 误报排除
FP 标记：注释/字符串/`//nolint`/go-zero 生成代码/内部函数/只读不分支。

### Step 5-6: Auto-Fix → `@references/auto-fix-templates.md`
P0+P1 自动修复 → re-scan 验证 → before/after 对比表。

### Step 6.5: 经验沉淀
成功修复 P0/P1 → 反哺 claude-next.md（去重，同规则 ≥3 条跳过）。

### Step 7: 输出报告
✅ 通过 / ⚠️ 需改进，含 blocked 项 + P2/P3 建议。报告包含：base_ref / head_ref / changed_files / degraded_items / confidence_avg。

## 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| skill 不可用 | 调用 lx-code-review | 用 references/ 规则自行审查 [降级审查] |
| >50 文件 | 全量 | 只审查高风险文件 |
| auto-fix 后仍有 P0 | 修复+重审 | 2 次后 BLOCKED |
| git 不可用 | git diff | 文件列表扫描 |
| go-style-guide 缺失 | 项目规范 | 内置规范 [降级] |

## 语言检测

1. 用户显式指定 `--lang=go` → 加载 rules-go.md
2. 文件扩展名统计（.go/.py/.java 占比）→ 加载对应语言规则
3. 配置文件检测（go.mod/package.json/pom.xml）→ 自动判断
4. 默认降级到 rules-general.md
5. 多语言项目 → 按文件类型分语言执行规则
