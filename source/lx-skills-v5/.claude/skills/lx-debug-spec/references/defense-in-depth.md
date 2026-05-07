# Defense-in-Depth Verification

Use after Phase 4 fix when the bug was critical or affected multiple components.

## Verification Layers

### Layer 1: Unit Test- The failing test now passes- Edge cases covered (nil, empty, boundary, concurrent)- Run: `go test -v -run TestSpecific ./pkg/...`

### Layer 2: Race Detection- No race conditions introduced by the fix- Run: `go test -race -count=10 ./pkg/...`

### Layer 3: Integration Test- Component interactions work correctly- Run: `go test -tags=integration ./...` or `go test -short=false ./...`

### Layer 4: Regression Suite- No existing tests broken- Run: `go test ./...`

### Layer 5: Related Code Review- Grep for similar patterns elsewhere in codebase- Same bug may exist in analogous code paths- Run: `rg 'pattern-from-bug' --type go`

### Layer 6: Defensive Additions (if warranted)- Input validation at boundary- Error handling for the failure mode- Logging for future diagnosis

## Checklist

```- [ ] Unit test passes- [ ] Race detection clean- [ ] Integration tests pass (if applicable)- [ ] Full regression suite passes- [ ] Similar patterns checked in codebase- [ ] Defensive additions added (if warranted)
- [ ] Unit test passes- [ ] Race detection clean- [ ] Integration tests pass (if applicable)- [ ] Full regression suite passes- [ ] Similar patterns checked in codebase- [ ] Defensive additions added (if warranted)
```

## When to Use Each Layer
| Bug Severity | Required Layers|
|-------------|-----------------|
|Low (cosmetic) | 1, 4|
|Medium (functional) | 1, 2, 4|
|High (data loss, auth) | 1, 2, 3, 4, 5|
|Critical (production) | All 6 layers |
