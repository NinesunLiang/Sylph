# 输出模板：BLOCKED (v1.0)

用 Phase 门禁数据填写所有括号字段。

```
## ⛔ Root Cause Analysis BLOCKED v1.0
### 阻塞原因: [repair loop exhausted / confidence insufficient / Oracle failed]
### 调查历史
- Symptom: [one sentence]
- Root cause (best hypothesis): [one sentence] (confidence: [X]/25)
- Repair rounds: [N]/3 (exhausted: [yes/no])
### 每轮失败日志 (if repair loop exhausted)| Round | Fix Applied | Result | Failure Mode ||-------|------------|--------|--------------|| 1 | [fix description] | ❌ | [new root cause / same recurrence] || 2 | [fix description] | ❌ | [new root cause / same recurrence] || 3 | [fix description] | ❌ | [new root cause / same recurrence] |
### Oracle 咨询结果
- Submitted: [yes/no]
- Oracle finding: [summary]
- Resolved: [no — reason]
### 需要外部输入
- What is needed: [specific data, access, or environment]
- Suggested user action: 1. [action 1, e.g., "Provide production pprof goroutine dump"] 2. [action 2, e.g., "Enable trace logging at [path] for 24h"] 3. [action 3, e.g., "Run `go tool pprof http://server/debug/pprof/goroutine`"]
### 已收集证据 (for future investigation)
- [evidence 1] (source: [tool]) [verified/speculative]
- [evidence 2] (source: [tool]) [verified/speculative]
### 已排除假设
1. [hypothesis]: excluded because [evidence]
2. [hypothesis]: excluded because [evidence]
```
