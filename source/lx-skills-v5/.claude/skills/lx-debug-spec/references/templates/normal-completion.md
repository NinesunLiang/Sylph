# Output Template: Normal Completion

```## Systematic Debugging Report
### Phase 1: Root-Cause Investigation- Error summary: [one sentence]- Repro: [stable/intermittent/cannot] — Steps: [steps]- Recent changes: [found/none]- Data flow: [bad value path]- Concurrency: [yes/no]- Localization: [X] because [evidence] [verified]
### Phase 2: Pattern Analysis- Working example: [path]- Key differences: [list with relevance tags]- Most likely root cause: [analysis] (confidence: [level])
### Phase 3: Hypothesis Verification- Hypothesis: "[X] because [Y]"- Result: [confirmed] (evidence: [output])- Confirmed root cause: [final] (confidence: [high])
### Phase 4: Fix- Failing test: [path]- Fix: [one sentence]- File: [path:line]- Target test: ✅ | Regression: ✅ | Race: ✅/N/A- Cross-phase consistency: ✅
### Conclusion- Root cause: [one sentence]- Fix: [one sentence]- Scope: [affected files/modules]- Prevention: [how to avoid recurrence]
```
