## [RCA 反哺] {根因一句话}

- **影响**: `{package/function}`- **根因**: {Why N 得出的根因}- **免疫**: {测试防护 + 验证防护 + 监控防护，各一句}- **置信度**: {N}/25- **来源**: lx-root-cause-analysis

```

### 6. 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。
根据结果选择模板，从 `${CLAUDE_SKILL_DIR}/docs/templates/` 加载：
| 结果 | 模板|
|------|------|
|全部 5 个阶段通过 | `readFile("${CLAUDE_SKILL_DIR}/docs/templates/normal-completion.md")`|
|阶段 5 验证失败 | `readFile("${CLAUDE_SKILL_DIR}/docs/templates/immunity-failed.md")`|
|置信度 < 18，需要 Oracle | `readFile("${CLAUDE_SKILL_DIR}/docs/templates/oracle-consultation.md")`|
|修复循环耗尽（3/3） | `readFile("${CLAUDE_SKILL_DIR}/docs/templates/blocked.md")`|
|非复现 / 非 Go 项目 | `readFile("${CLAUDE_SKILL_DIR}/docs/templates/not-applicable.md")` |
用各阶段门控数据填充模板。版本标签：`v1.0`。
**完成标准**：- ✅ 正确模板已选择（匹配实际结果）- ✅ 模板中所有括号字段已用 Phase 门控数据填充（无空占位符）- ✅ 版本标签 `v1.0` 已包含- ❌ 任何占位符未填充 → 返回对应 Phase 补充数据
