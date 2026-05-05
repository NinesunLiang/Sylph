# Node: gate_checker

# node: gate_checker
# input:
# - scan_report: scan_report.yaml (required) — 扫描报告
# - gate_rules: { block_on_severity, warn_on_severity, allow_with_warnings } (required) — 门控规则
# output:
# - gate_result: gate_result.yaml — Gate 判定结果
# triggers:
# - on_pass: gate_passed
# - on_blocked: gate_blocked

> 根据 gate 规则判定通过/阻塞
> 复用: pre-commit, pre-push, security-review

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| scan_report | scan_report.yaml | 是 | — | 扫描报告 |
| gate_rules.block_on_severity | string[] | 否 | `["P0"]` | 阻塞的严重度 |
| gate_rules.warn_on_severity | string[] | 否 | `["P2", "P3"]` | 仅警告的严重度 |
| gate_rules.allow_with_warnings | boolean | 否 | true | 是否允许有警告时通过 |

## 输出契约

输出 `gate_result` schema（`schemas/atomic/gate_result.yaml`）：
```
yamlgate_name: string
passed: boolean
blockers: finding.yaml[] # 阻塞项
warnings: finding.yaml[] # 警告项
verdict: pass | blocked | warn
```

## 流程

1. 检查 scan_report.findings 中是否有 `severity` 在 `block_on_severity` 中的项
2. 有 blockers → `passed=false`, `verdict=blocked`
3. 无 blockers 但有 warnings → `passed=true`, `verdict=warn`（若 `allow_with_warnings=true`）
4. 无任何问题 → `passed=true`, `verdict=pass`
5. 输出 gate_result
