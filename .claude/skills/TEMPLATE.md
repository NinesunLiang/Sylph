# Skill 模板 — 新建 skill 时复制此文件

> >
> **目录结构（三层规范 v6.0.0）**
> ```
> skills/lx-{name}/
> ├── SKILL.md ← AI 判断层（必须）
> ├── scripts/ ← 确定性执行层（有固定逻辑时创建）
> │ └── xxx.py ← 纯 Python，exit code，JSON 输出
> └── references/ ← 按需知识层（有大块结构化知识时创建）
> └── xxx.md ← SKILL.md 写死加载时机
> >
> ```
> **判断标准**：
> - 步骤固定、无需 AI 判断 → `scripts/`
> - 大块结构化知识（
> 30行）、按阶段加载 → `references/`
> - 需要 AI 语义理解才能执行 → 留在 `SKILL.md`
> 复制 `.claude/skills/lx-{name}/SKILL.md` 并替换所有 `{name}`、`{description}` 等占位符。

```yam
l
---name: lx-{name}description: "{一句话描述}"when_to_use: "Use when user says '{trigger1}', '{trigger2}'."argument-hint: "[参数提示]"paths: - "*.{ext}"harness_version: ">=1.1.0"---
# {Skill 标题}
## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。
### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析目标|
|context_collector | `../../nodes/context_collector.md` | 收集项目上下文|
|scanner | `../../nodes/scanner.md` | 按规则扫描（如适用）|
|auto_fixer | `../../nodes/auto_fixer.md` | 自动修复（如适用）|
|verifier | `../../nodes/verifier.md` | 验证修复（如适用）|
|gate_checker | `../../nodes/gate_checker.md` | Gate 判定（如适用）|
|report_generator | `../../nodes/report_generator.md` | 报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 行为约束 |\|
### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 目标定义|
|severity | `../../schemas/atomic/severity.yaml` | 严重度分级|
|finding | `../../schemas/atomic/finding.yaml` | 问题发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|gate_result | `../../schemas/atomic/gate_result.yaml` | Gate 判定（如适用）|
|verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |\|
### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长会话上下文总结 |\|
### 状态机
> > 说明本 skill 的状态机类型：
> - **scan→fix→re-scan 循环**（审查类）
> - **analyze→generate→verify 流程**（生成类）
> - **门禁型**（Gate 链）
> - **私有 X 阶段**（说明为什么不引用 orchestrator.md）
### 私有节点
> 本 skill 无私有节点。（如有私有节点，说明为什么不能提升为通用节点）
### 边界声明（不做什么）
> 显式列出本 skill **不会**执行的操作，防止隐性目标漂移。
| 不做的操作 | 原因 | 推荐替代|
|-----------|------|---------|
|{不做的操作 1} | {原因} | 使用 {替代 skill}|
|{不做的操作 2} | {原因} | 使用 {替代 skill} |\|
---
## 执行流程
### Step 0: 入口检查
```bash
#
检查项目是否适用本 skill

```

### Step 1: 解析目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。- 过滤规则：保留/排除的文件类型

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：框架版本、配置、已知问题。

### Step 3: 扫描/分析
加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的规则集：
**类别 A — {类别名}（N 条规则）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| A1 | {规则描述} | P0 | {检查方式} |

### Step 4: 误报排除
**误报场景**：{列出误报场景}

### Step 5: 生成改进建议
对每个真阳性问题：位置 + 问题本质 + 修改建议。排序：P0 → P1 → P2 → P3。

### Step 6: Auto-Fix（P0 + P1）
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略：
| 规则 | 修复模板|
|------|---------|
|A1 {规则名} | {修复方式} |
### Step 6.5: Re-scan 验证
加载 `@../../nodes/verifier.md`，传入 `fix_record[]` + 原始 `finding[]`。

### Step 7: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。

## 错误恢复与中止条件- 不适用场景 → "不适用"报告- 过滤后无目标文件 → "无变更"报告- 全部命中为误报 → "通过"报告- 待确认项超过 5 个 → 暂停，请求用户输入
```
