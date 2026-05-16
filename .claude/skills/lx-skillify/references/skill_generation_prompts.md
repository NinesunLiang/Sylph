# Skill 生成提示模板

> 由 lx-skillify Phase 2 加载。每个技能类型对应一组生成规则。

---

## 审查类技能（Reviewer）

生成模式：`scan → fix → re-scan 循环`

**必选节点**: behavior_rules, scanner, report_generator
**可选节点**: auto_fixer, verifier, gate_checker, context_collector
**必选 Schema**: verdict, finding, scan_report, severity

**执行流程模板**:
1. Step 0: 入口检查（项目类型检测）
2. Step 1: 解析目标（加载 target_resolver）
3. Step 2: 收集上下文（加载 context_collector）
4. Step 3: 扫描（加载 scanner，传入规则集）
5. Step 4: 误报排除
6. Step 5: 生成改进建议（按 P0→P3 排序）
7. Step 6: 自动修复（加载 auto_fixer，P0+P1）
8. Step 6.5: 重扫验证（加载 verifier）
9. Step 7: 输出报告（加载 report_generator）

**规则集格式**:
```
| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| A1 | {描述} | P0 | {方式} |
```

---

## 生成类技能（Generator）

生成模式：`analyze → generate → verify 流程`

**必选节点**: behavior_rules, generator, report_generator
**可选节点**: context_collector, target_resolver, verifier
**必选 Schema**: verdict, context_summary

**执行流程模板**:
1. Step 0: 入口检查
2. Step 1: 解析输入（加载 target_resolver）
3. Step 2: 收集上下文（加载 context_collector）
4. Step 3: 生成（加载 generator）
5. Step 4: 验证（加载 verifier）
6. Step 5: 输出（加载 report_generator）

---

## 门禁类技能（Gate）

生成模式：`门禁型`

**必选节点**: behavior_rules, gate_checker, report_generator
**可选节点**: scanner, context_collector
**必选 Schema**: verdict, gate_result

**执行流程模板**:
1. Step 0: 前置条件检查
2. Step 1: 收集证据
3. Step 2: 逐项判定（加载 gate_checker）
4. Step 3: 汇总输出（加载 report_generator）

---

## 工作流类技能（Workflow）

生成模式：`私有 X 阶段`

**必选节点**: behavior_rules, context_collector, report_generator
**可选节点**: interactive_prompt, explore, target_resolver
**必选 Schema**: verdict

**执行流程模板**:
1. Step 0: 入口路由
2. Step 1-N: 自定义阶段
3. Step N+1: 输出报告

---

## Frontmatter 生成规则

| 字段 | 生成规则 |
|------|---------|
| name | `lx-{用户指定}` |
| version | `v1.0.0`（新技能默认） |
| description | 用户描述的精简版（≤80 字符） |
| when_to_use | `"Use when user says '{triggers}'."` |
| model | `sonnet`（默认），高复杂度用 `opus` |
| argument-hint | 根据输入类型生成 |
| harness_version | 读 `.claude/skills/VERSION`，默认 `">=1.1.0"` |
| status | `draft`（新技能默认） |
| execution_mode | 审查/门禁→stepwise，并行→race，其他→stepwise |
| triggers | 用户指定 + 自动推断 1-2 个中文触发词 |

## 降级策略生成规则

每个技能至少 3 条降级路径：
1. 输入缺失 → 提示用户
2. 核心工具不可用 → 降级到基础方法
3. 多次失败 → 暂停，请求人工介入
