# False Positive Exclusion Rules

For each scan hit, check against these rules. Use `readFile` ±10 lines for context.
| # | Scenario | Verdict | Action|
|---|----------|---------|--------|
|FP01 | Hit is inside comment (`//` or `/* */`) | False positive | Exclude (except 🟢 sensitive comments — keep as warning)|
|FP02 | Hit is in `_test.go` file (leaked through filter) | False positive | Exclude|
|FP03 | Hit is in `testdata/` directory | False positive | Exclude|
|FP04 | Hit line has parameterized query (`db.Query` + `?` placeholder) | False positive | Exclude|
|FP05 | Hit line uses project's existing security helper | False positive | Exclude (grep to confirm helper exists)|
|FP06 | Hit line has `//nolint:gosec` annotation | Human review | Check if annotation has valid justification; no justification → keep as vulnerability|
|FP07 | Hit is constant with placeholder value (`"your-secret-here"`, `"TODO"`) | False positive | Exclude|
|FP08 | Cannot determine | Pending | Mark "待确认: [reason]", do not report as confirmed |
