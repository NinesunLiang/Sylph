# Danger Signal Self-Check

Before each step — if any matches → STOP → re-analyze current step:
| Dangerous Thought | Violation|
|-------------------|-----------|
|"Looks like a key, report Critical directly" | No FP exclusion done (X08)|
|"Fixed it, should be fine now" | No re-scan done (X04/X11)|
|"This Low issue should also block" | Low = warn only (X07)|
|"Full scan would be safer" | Only scan git diff (X12)|
|"This vuln is hard to fix, skip it" | 🔴🟠🟡 must be fixed (X03)|
|"Import a new security library to fix" | Check existing components first (X05)|
|"Code in comments should be reported too" | Comments are FP (X08)|
|"vendor/ has issues too" | Don't scan vendor/ (X12)|
|"panic instead of error return is simpler" | Maintain Go error handling (X14)|
|"nolint annotation = ignore" | Must check justification (X13) |
