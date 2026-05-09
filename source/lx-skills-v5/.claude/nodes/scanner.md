# Node: scanner

# node: scanner
# input:
# - scan_target: scan_target.yaml (required) — 扫描目标
# - rules: array of { id, description, severity, check_method } (required) — 扫描规则集
# output:
# - findings: array of finding.yaml — 问题发现列表
# triggers:
# - on_success: scan_complete
# - on_empty: no_findings

> 按规则集扫描目标，产出 finding 列表
> 复用: code-review, security-review, browser-verify, perf-analysis, web-perf, react-review, style-guide, golang-test

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| scan_target | scan_target.yaml | 是 | — | 目标定义 |
| rules | { id, description, severity, check_method }[] | 是 | — | 扫描规则集（由 skill 提供领域规则） |

## 输出契约

输出 `finding[]` 数组，每项符合 `schemas/atomic/finding.yaml`：
```yaml
id: string # 自动生成，如 "FIND-001"
rule_id: string # 触发的规则 ID（如 "A1", "SEC-01"）
severity: severity.yaml # 严重度
file: string # 涉及文件
line: number (optional) # 涉及行号
description: string # 问题描述
evidence: string # 证据（代码片段/命令输出/截图描述）
suggestion: string (optional) # 修复建议
auto_fix_applied: boolean (optional) # 是否已自动修复
```

## 流程

1. 加载规则集
2. 逐规则扫描目标（每条规则必须执行实际 grep/ast-grep 命令）
3. 对每个命中项生成 finding（id, rule_id, severity, file, evidence）
4. 按 severity 排序输出
5. 零命中 → 触发 `on_empty: no_findings`

## 5-Why 根因记录（强制）

对每个 P0/P1 finding，必须附加根因分析：
```yaml
finding:
  rule_id: "A1"
  severity: "P0"
  root_cause:
    symptom: "error 被吞"
    why_1: "函数返回值未检查 err"
    why_2: "开发者假设该调用不会失败"
    why_3: "缺少错误处理规范培训"
    fix_direction: "添加 if err != nil 检查 + 更新 kernel.md 规范"
```
**不记录 5-Why 的 finding 不得进入 auto_fixer 节点。**
