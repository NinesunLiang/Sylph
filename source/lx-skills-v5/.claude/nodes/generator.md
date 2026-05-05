# Node: generator

# node: generator
# input:
# - context_summary: context_summary.yaml (required) — 收集的项目上下文
# - template_spec: { sections, rules, output_format } (required) — 生成模板规范
# - domain_rules: array of string (optional) — 领域特定规则
# output:
# - generated_content: string — 生成的文档/代码/Spec
# - quality_check: { passed, issues } — 质量检查结果
# triggers:
# - on_success: content_generated
# - on_quality_fail: quality_check_failed

> 根据上下文和模板规范生成文档/代码/Spec
> 适用: tdd-spec, prd, golang-test, frontend-test

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| context_summary | context_summary.yaml | 是 | — | 项目上下文摘要 |
| template_spec.sections | { name, required, description }[] | 是 | — | 输出文档的章节定义 |
| template_spec.rules | string[] | 是 | — | 生成规则约束 |
| template_spec.output_format | string | 否 | "markdown" | 输出格式 |
| domain_rules | string[] | 否 | [] | 领域特定规则 |

## 输出契约

```
yamlgenerated_content: string # 生成的完整内容
quality_check:
  passed: boolean # 是否通过质量检查
  issues: string[] # 未通过的问题列表
```

## 流程

1. 加载 context_summary 理解项目上下文
2. 按 template_spec.sections 逐节生成内容
3. 应用 template_spec.rules 约束生成质量
4. 执行质量自检（完整性、一致性、可执行性）
5. 输出生成内容 + 质量检查结果
