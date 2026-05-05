# Node: report_generator

# node: report_generator
# input:
# - scan_report: scan_report.yaml (required) — 扫描/审查/验证报告
# - verdict: verdict.yaml (required) — 最终判定
# - report_template: string (optional) — 报告模板名称（pass/blocked/warn）
# output:
# - report: string — 结构化 Markdown 报告
# triggers:
# - on_success: report_generated

> 将 findings + verdict 格式化为结构化报告
> 复用: ALL 17 个 lx-* skills

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| scan_report | scan_report.yaml | 是 | — | 扫描/审查/验证报告 |
| verdict | verdict.yaml | 是 | — | 最终判定 |
| report_template | string | 否 | 根据 verdict.status 自动选择 | 报告模板（pass/blocked/warn） |

## 输出契约

输出结构化 Markdown 报告，包含：
```
mark
down## {skill_name} 报告 {✅/⚠️/⏭️}

### 范围
- 目标：{scan_report.target}
- 文件数：{N}
- 规则数：{N}

### 结果
- 按严重度分组的计数表
- before/after 对比表（如有修复）

### 详情
- 按 severity 分组的 finding 列表
- 每项：位置 + 描述 + 证据 + 建议

### 判定
- verdict.summary
- next_actions（如有）
```

## 流程

1. 根据 `verdict.status` 选择报告模板（pass/blocked/warn）
2. 汇总 scan_report.summary（总数、按严重度分组）
3. 按 severity 分组 findings，逐项输出
4. 附加 verdict 和 next_actions
5. 输出结构化 Markdown 报告
