---

name: lx-rpe
version: v4.0.0
description: "Run RPE-driven feature dev loop on main branch: TDD, code review, security, acceptance, graded rollback."
complexity: advanced
when_to_use: "Use when user says 'rpe', 'main branch', 'feature dev', 'start feature', 'continue feature', or begins systematic feature development."
model: sonnet
effort: high
argument-hint: "new [name] [需求描述] | [feature name] | [path] (e.g. prd/payment/checkout)"
triggers:
  - "/lx-rpe"
paths:
  - "rpe/**/*.md"
  - "prd/**/*.md"
harness_version: ">=1.1.0"
role: "RPE-driven feature development — 9-step closed loop with quality gates"
execution_mode: stepwise
---

# 主分支 — RPE 系统性开发模式

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|scanner | `../../nodes/scanner.md` | 9 步闭环中的代码审查/安全扫描步骤|
|auto_fixer | `../../nodes/auto_fixer.md` | 审查问题的自动修复|
|verifier | `../../nodes/verifier.md` | 修复后复扫验证|
|report_generator | `../../nodes/report_generator.md` | 最终审查报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 全阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 变更范围目标定义|
|finding | `../../schemas/atomic/finding.yaml` | 审查发现的问题项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 审查报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长会话上下文总结 |

### 状态机
本 skill 使用**私有 9 步闭环状态机**（Read Task → Design → Code+Pre-commit → Security → Sync → Wait Acceptance → Judge → Commit → Summary），不引用 `orchestrator.md`。原因：RPE 是主分支特性开发的完整闭环，包含 TDD/安全/验收等特有阶段。
**核心状态映射**: need_clarification → executing → [Read Task → Design → Code+Pre-commit → Security → Sync → Wait Acceptance → Judge → Commit → Summary] → done

### 私有节点
本 skill 无私有节点。

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机|
|------|------|---------|
|`scripts/git_commit.py` | Git 提交 | Step 8|
|`scripts/update_progress.py` | 更新 progress.md 状态 | Step 1 进入 / Step 9 完成|
|`scripts/extract_ac.py` | 从 plan.md 提取 AC | Step 1 |
|`scripts/build_and_test.py` | 编译+测试门禁 | Step 3 |

### references/（按需知识层）
| 文件 | 内容 | 加载时机|
|------|------|---------|
|`references/rpe_phases.md` | Phase 1-3 详细流程 | Phase 1/2/3 入口|
|`references/rpe_main_loop.md` | 9 步主循环详情 | 主循环各 Step |
|`references/gate-checklist.md` | Gate-R/P/X/E 清单 | 各 Gate 检查前|
|`references/go-coding-rules.md` | Go 编码规范 | Step 2/3（Go 项目）|
|`references/frontend-coding-rules.md` | 前端编码规范 | Step 2/3（前端项目）|
|`references/security-scan-rules.md` | 安全扫描规则 | Step 4 前|
|`references/commit-convention.md` | Commit 格式 | Step 8 前|
|`references/progress-panel-template.md` | 状态面板模板 | status 命令|
|`references/progress-file-template.md` | 进度文件模板 | new 流程|
|`references/batch-accept-template.md` | 验收报告模板 | batch-accept|

---
**角色**：资深软件工程师 + 项目交付负责人，按项目类型路由（Go: go-zero / 前端: React+TS）。
**动态环境信息**：`date +%Y-%m-%d` · `git branch --show-current 2>/dev/null` · `ls rpe/ 2>/dev/null`

## 硬性约束
- **NEVER** 做验收决策（用户执行）
- **NEVER** 混入 todo 概念——RPE 只有 Step
- **NEVER** 执行脱离当前任务项的自由探索（记入 tech-debt）
- **ALWAYS** 按项目类型路由 + 9 步闭环推进
- **ALWAYS** 作为 harness 统一入口：用户只与 /lx-rpe 对话

## 统一入口路由
| 子命令 | 动作 | 说明|
|--------|------|------|
|`status` | 输出结构化进度面板 | 读所有实例状态+未提交变更|
|`new` | 初始化新特性 RPE | 创建目录+骨架文档→进入 Phase 1|
|`[name]` | 继续指定特性开发 | 恢复流程（指定特性） |
|`[path]（含 /）` | 使用 OMA 目录路径 | 恢复流程（指定路径）|
| `batch-accept` | 批量验收 | 编译+测试+门禁自动验证|
|无参数 | 自动检测恢复点 | 恢复最近活跃 RPE 实例 |

**输入不合规提示**（无法路由时）：
```
📖 /lx-rpe 使用指南
/lx-rpe status ← 全局进度面板
/lx-rpe {feature} ← 继续特性开发
/lx-rpe prd/{sub_prd}/{feature} ← OMA 目录路径
/lx-rpe new ← 新建特性 RPE
/lx-rpe batch-accept ← 批量验收
/lx-pre-push {线上commit} ← 推送前三道门禁
```

## 会话目标锚定（静默执行）
> AI 内部对齐检查，不输出给用户。Session 恢复或跨 Task 跳转时提示。
**每个 Step 前自检**：
1. 偏离当前任务项？→ 停止，重新对齐
2. 引入范围外变更？→ 记 tech-debt，继续
3. 上步完成标准未全满足？→ 回到上步补齐

## 入口路由
| 子命令 | 动作 | 跳转|
|--------|------|------|
|**无参数** | **继续最近活跃 RPE** | → 恢复流程，直接推进|
|`new` | 创建新特性 | → 新建流程|
|`[name]` | 继续指定特性 | → 恢复流程|
|`[path]（含 /）` | OMA 目录路径 | → 恢复流程|
|`status` | 输出进度面板 | → 状态面板|
|`batch-accept` | 批量验收 | → 批量验收 |

**哲学**：`/lx-rpe`（无参数）= 直接继续；有活跃任务→恢复推进；无任务→提示创建。只有 `new` 才创建。

### 状态面板（`status`）
```
1. 扫描 rpe/ 和 prd/ 目录 → 列出所有实例
2. 对每个实例：readFile progress.md → Phase/Task/阻塞项
                 readFile executor.md → 最近 3 Task + commit
                 git diff --stat → 未提交变更
3. 聚合输出结构化面板
```
模板：`@references/progress-panel-template.md`

### 批量验收（`batch-accept`）
- 筛选 Step 6（同步完成，等待验收）的任务项
- 对每项：读 AC → 读 Evidence → 编译验证 → 测试验证 → 调 lx-pre-commit
- 验收报告：`@references/batch-accept-template.md`
- 编译 ✅ + 测试 ✅ + pre-commit ✅ + AC 全覆盖 → 建议通过；否则标记失败原因

## 新建流程（`new`）

详见 `@references/rpe_phases.md`（完整 Phase 1-3 流程）。

**初始化**：支持 3 种输入方式（一行带入 / 逐步引导 / 已有 prd.md）→ 创建 `rpe/{name}/{prd.md, research.md, plan.md, executor.md, state/}` → 自动生成 research 初稿。

**Phase 1 — Research**：研究迭代循环。用户审阅 → AI 回应 → Gate-R 自检 → 推进。
**Phase 2 — Plan**：规划迭代循环。Task 分解 + AC + 测试策略 + 回滚方案 → Gate-P/X 自检 → 推进。
**Phase 3 — Execute**：自动执行 → 进入主循环。Gate-X / Blocker / 验收 / commit 时暂停通知。

**Phase 方向指引模板**（各阶段完成输出）：
```
─── 方向指引 ───
📍 {当前阶段}
建议下一步:
  1. {下一阶段} — 推荐 ✓  说明：{做什么}  适用场景：{何时选}
  2. {备选}
  3. 自定义操作 → 输入你想要的命令
```

## 恢复流程（默认行为）

```
0. 若 ARG 含 `/`（如 prd/payment/checkout）→ BASE_DIR = ARG/，跳到 3
1. 搜索实例目录：ls rpe/ prd/*/
2. 多实例→列出选择；指定名称→BASE_DIR = rpe/{name}/；唯一→自动加载
3. readFile {BASE_DIR}state/progress.md → 提取当前阶段/步骤/任务/阻塞
4. 上下文校验：Phase 2+ 但 research 空→回退 P1；Phase 3 但 plan 空→回退 P2；主循环无任务→回退 P3 入口
5. 恢复入口：Phase 1/2/3 或主循环步骤或 Gate-X 暂停
6. 输出恢复摘要（当前阶段 + 任务 + 上次下一步 + 阻塞）
7. → 进入对应阶段/步骤
```

## 主循环（9 步）

详见 `@references/rpe_main_loop.md`（各 Step 执行序列 + 模板 + 完成标准）。

```
[1] 读任务项 → [2] 设计 → [3] 编码+pre-commit → [4] Security Review
    → [5] 同步 → [6] 等待验收 → [7] 判定 → [8] Git Commit → [9] 写摘要
    → 下一个任务项 → [1]
```

**回退机制**：编译失败 3 次 → 回 Step 2；验收不通过 → 按类型回 Step 3/4；回退 3 次→暂停讨论。

## Pipeline 集成

Pipeline 编排由 `/lx-oma-orch` 统一管理。`lx-rpe` 不做 pipeline.yaml 读写，仅接收 BASE_DIR 参数。

- 编排模式：`/lx-oma-orch advance` 将 BASE_DIR 注入 `lx-rpe {path}`
- 独立使用：`/lx-rpe {feature}` 直接指定 rpe/{feature}/
- 出口仅标注 state/progress.md 的阶段状态，不写入 pipeline.yaml

## 版本历史
| 版本 | 日期 | 变更摘要|
|------|------|---------|
|v4.0.0 | 2026-05-10 | 精简 SKILL.md 到 ≤300 行，Phase 详情→references/rpe_phases.md，主循环详情→references/rpe_main_loop.md|

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|build_and_test.py 失败 | 脚本执行 | 直接运行 go build && go test |
|git_commit.py 失败 | 脚本提交 | 直接 git add + git commit（需用户确认）|
|lx-security-review 不可用 | 调用 skill | 执行 govulncheck ./...，标注"[降级扫描]"|
|Gate-X 频繁触发（>3次）| 暂停执行 | 回 Phase 2 全面重审 |
|Phase 迭代超 5 轮 | 继续迭代 | 暂停，询问是否简化需求 |
