# Prohibited Actions & Danger Signals

## Prohibited Actions
Before every action, self-check against these. If triggered → stop → return to current Phase:
| Code | Prohibited | Correct Action|
|---|---|---|
|X01 | Proposing fix before Phase 1 complete | Continue investigation|
|X02 | Changing multiple locations at once | One change at a time|
|X03 | Skipping failing test creation | Phase 4 step 1 is mandatory|
|X04 | Implementing fix on unverified hypothesis | Phase 3 gate required|
|X05 | 4th fix attempt after 3 failures | Architecture challenge, discuss with user|
|X06 | Claiming Phase complete without gate output | Every Phase must output its gate|
|X07 | Skimming reference implementation | Phase 2 requires reading every line|
|X08 | Proposing fix without understanding | Tag "Don't understand: [what]", continue investigating|
|X09 | Skipping regression verification | Phase 4 gate requires it|
|X10 | Stating unverified conclusions as fact | Use "Speculative: ..." with confidence level|
|X11 | Fixing symptoms instead of root cause | Phase 3 confirms root cause first|
|X12 | Stacking changes (adding on top of failed hypothesis) | Revert old changes, form new hypothesis|
|X13 | Skipping `-race` for concurrency issues | Race detection mandatory|
|X14 | Single-run verification for intermittent bugs | Use `-count=20` or higher |

## Danger Signal Self-Check
If you catch yourself thinking any of these → stop → re-analyze in current Phase:
| Dangerous Thought | Violation|
|-------------------|-----------|
|"Let me quickly fix this, investigate later" | X01|
|"Let's try changing X and see" | X04|
|"Change a few things at once" | X02|
|"Skip the test, manual check is fine" | X03|
|"It's probably X, just fix it" | X11|
|"Don't fully understand but might work" | X08|
|"Try once more" (after 3 failures) | X05|
|"Race condition doesn't need -race" | X13|
|"Ran once without repro, should be fine" | X14|
|"Hypothesis failed, add a bit more on top" | X12 |
