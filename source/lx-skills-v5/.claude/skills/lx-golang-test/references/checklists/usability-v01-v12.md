# Usability Self-Check (V01-V12)

Execute ALL 12 items. Cannot skip.
| # | Check | Pass Condition | Fix Limit|
|---|-------|----------------|-----------|
|V01 | Package declaration | Matches project (same-pkg / `_test`) | 2|
|V02 | Import paths | Correct module path + directory | 2|
|V03 | Mock strategy | Matches project convention | 2|
|V04 | Helper reuse | No recreated existing helpers | 2|
|V05 | `t.Helper()` | All helper functions marked | 2|
|V06 | `t.Cleanup()` | All resources registered | 2|
|V07 | Range var capture | Correct for Go version | 2|
|V08 | Assertion style | Matches project convention | 2|
|V09 | No real services | All external deps mocked | 2|
|V10 | No `time.Sleep()` | Zero occurrences | 2|
|V11 | No private func testing | All tested symbols exported | 2|
|V12 | Integration isolation | Correct tag/flag used | 2 |
Fail after 2 fixes → mark "BLOCKED: [V##] [detail]", report to user.
