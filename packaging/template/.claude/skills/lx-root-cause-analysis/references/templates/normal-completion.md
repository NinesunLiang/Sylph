# 输出模板：正常完成 (v1.0)

用 Phase 门禁数据填写所有括号字段。

```## 🔬 Root Cause Analysis v1.0
### Phase 1：症状映射- 原始目标: [from Session Goal Anchor]- 症状: [one sentence]- 影响范围: [package/module/service]- 时间线: [first] → [fix1] → [recurrence1] → ... → [current]- 历史修复 (≤3): 1. [date] [commit]: [content] → [result: ✅/⚠️/❌]- 故障链: [trigger] → [A] → [B] → ... → [failure]- 复发: confirmed ([evidence])
### Phase 2：断点隔离- 断点位置: [packageA] → [packageB] (function names)- 工具输出原文 (≤3 lines): [raw output]- 解读: [conclusion]- 直接原因: [one sentence]- 并发相关: [yes (race report summary) / no]
### Phase 3：五层 Why- Why 1: [answer] Tool: [cmd] | Output: [raw] | Evidence: [type] | Interpretation: [text] | Consistency: [✅/⚠️]- Why 2: [answer] Tool: [cmd] | Output: [raw] | Evidence: [type] | Interpretation: [text] | Consistency: [✅/⚠️]- Why 3: [answer] Tool: [cmd] | Output: [raw] | Evidence: [type] | Interpretation: [text] | Consistency: [✅/⚠️]- Why 4: [answer] (or "Early termination: [reason]") Tool: [cmd] | Output: [raw] | Evidence: [type] | Interpretation: [text] | Consistency: [✅/⚠️]- Why 5: [answer] (or "Early termination: [reason]")- 根本原因: [one sentence]- 置信度: [X]/25 (Evidence [N] + Repro [N] + Cross-system [N] + Traceability [N] + Actionability [N])- 修复层级: [root-cause / systemic]- 匹配 Go 根因模式: [goroutine leak / nil pointer / race / pool exhaustion / error swallowing / implicit assumption / go-zero specific / other]
### Phase 4：根因消除- 修复轮次: [N]/3- 修复层级: [root-cause / systemic]- 修复内容: [specific changes]- 修复文件: [path:line] for each changed file- 验证命令: [command]- 验证输出原文 (≤10 lines): [raw output]- Original problem: ✅ | Similar issues: ✅ | Regression: ✅ | -race: ✅/N/A- 跨 Phase 一致性: Phase 3 root cause = Phase 4 fix ✅
### Phase 5：免疫防护- 修复轮次: [N]/3- 防护清单: ✅ 测试: [path] — covers root cause scenario [with -race if applicable] ✅ 校验: [constraint type] at [location] ✅ 监控: [log pattern] at [critical path]- 验证命令: [full command]- 验证输出原文 (≤10 lines): [raw output]- 攻击测试: ✅ | Root cause trigger intercepted: ✅ | -race clean: ✅/N/A- 免疫覆盖: [compile-time interception] + [runtime interception] + [test regression] + [monitoring alert]
### 结论- 症状: [one sentence]- 直接原因: [one sentence]- 根本原因: [one sentence]- 修复内容: [one sentence]- 免疫: [compile-time] + [test] + [monitoring] triple defense
```
