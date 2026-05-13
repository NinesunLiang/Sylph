# 输出模板：免疫验证失败 (v1.0)

用 Phase 门禁数据填写所有括号字段。

```## 🔬 Root Cause Analysis (Immunity Verification Failed) v1.0
### 问题- Phase 5 immunity test did not pass- 验证命令: [command]- 验证输出原文: [raw output, ≤10 lines]- Failure: [what specifically failed — test failure / race detected / attack not intercepted]
### 根因回溯- Phase 3 root cause: [one sentence]- Phase 4 fix applied: [one sentence]- Gap: fix did not fully cover [specific uncovered scenario]
### 修复状态- Round: [N]/3- If N < 3: returning to Phase 4 with expanded fix scope- If N = 3: escalating to Oracle
### 扩展修复范围 (if continuing)- Previously covered: [packages/scenarios]- Now adding: [packages/scenarios]- Reason: [evidence from failed verification]
### Oracle 提交 (if round 3/3)[Follow oracle-escalation.md template with all 3 rounds' failure evidence]
```
