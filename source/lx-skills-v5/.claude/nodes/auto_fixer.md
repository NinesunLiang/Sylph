# Node: auto_fixer

# node: auto_fixer
# input:
# - findings: array of finding.yaml (required) — 扫描发现的问题列表
# - fix_policy: { max_attempts, allowed_severities, fix_templates } (required) — 修复策略
# output:
# - fix_records: array of fix_record.yaml — 修复记录列表
# triggers:
# - on_success: fixes_applied
# - on_blocked: fix_blocked

> 对符合条件的 finding 执行自动修复
> 复用: code-review, security-review, todo, debug-spec, react-review, style-guide, web-perf, frontend-test, golang-test, perf-analysis, browser-verify

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| findings | finding.yaml[] | 是 | — | 扫描发现的问题列表 |
| fix_policy.max_attempts | number | 否 | 2 | 每个问题最多修复尝试次数 |
| fix_policy.allowed_severities | string[] | 否 | `["P0", "P1"]` | 允许自动修复的严重度 |
| fix_policy.fix_templates | { rule_id, fix_template }[] | 否 | [] | 规则→修复模板映射表 |

## 输出契约

输出 `fix_record[]` 数组，每项符合 `schemas/atomic/fix_record.yaml`：
```
yamlfinding_id: string # 被修复的 finding ID
fix_type: code_change | config_change | test_add | doc_update | workaround
files_changed: string[] # 变更文件列表
before_after:
  before: string # 修复前代码/状态
  after: string # 修复后代码/状态
verification: pass | fail | pending
```

## 流程

1. 筛选 `severity` 在 `fix_policy.allowed_severities` 中的 finding
2. 对每个 finding 查找匹配的 `fix_template`
3. 执行修复（最小变更原则，最多 `max_attempts` 次）
4. 记录 before/after 和变更文件
5. 标记 `fix_record.verification=pending`
6. 超限 → 触发 `on_blocked: fix_blocked`
