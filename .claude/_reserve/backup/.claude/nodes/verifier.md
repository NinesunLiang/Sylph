# Node: verifier

# node: verifier
# input:
# - fix_records: array of fix_record.yaml (required) — 修复记录
# - original_findings: array of finding.yaml (required) — 原始问题列表
# - scan_rules: array of { id, check_method } (optional) — 复扫规则（默认复用原始规则）
# output:
# - verification_report: { total, passed, failed, residual_findings } — 验证报告
# triggers:
# - on_pass: all_verified
# - on_fail: residual_found

> 执行修复后的复扫/复测，确认问题已解决
> 复用: code-review, security-review, browser-verify, pre-commit, todo, react-review, style-guide, web-perf, frontend-test, golang-test, perf-analysis

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| fix_records | fix_record.yaml[] | 是 | — | 修复记录列表 |
| original_findings | finding.yaml[] | 是 | — | 原始问题列表 |
| scan_rules | { id, check_method }[] | 否 | 复用原始规则 | 复扫规则集 |

## 输出契约

输出验证报告：
```yaml
total: number # 验证总数
passed: number # 通过数
failed: number # 失败数
residual_findings: # 残留问题列表
  - finding_id: string
    original_severity: string
    residual_evidence: string # 复扫证据
    status: still_present | new_issue
```

## 流程

1. 对每个 fix_record 执行复扫/复测（使用相同命令）
2. 对比原始 finding，确认问题是否消除
3. 检测是否引入新问题
4. 标记 verification=pass/fail
5. 有残留 → 触发 `on_fail: residual_found`；全部通过 → 触发 `on_pass: all_verified`
6. 输出验证摘要（before/after 对比表）
