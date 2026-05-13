# Danger Signal Self-Check

Before each step — if any matches → STOP → re-analyze current step:
| Dangerous Thought | Violation|
|-------------------|-----------|
|"Should be same-package test" | Guessing package structure (X03/X12)|
|"Just use testify" | Project may use stdlib assertions (X09)|
|"This helper probably exists" | Don't guess, grep first (X12)|
|"Too much work to mock, just connect DB" | X08|
|"Skip self-check, code is fine" | X11|
|"Don't need to check go.mod, probably 1.22" | Guessing version (X12)|
|"Sleep a bit for goroutine" | X02|
|"Fuzz should work" | Check Go version, < 1.18 can't (X15)|
|"Integration test doesn't need build tag" | X16|
|"Testing private func is simpler" | X01 |
