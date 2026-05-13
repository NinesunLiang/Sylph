# Condition-Based Waiting (Replacing time.Sleep)

Use when code contains `time.Sleep()` or fixed timeouts in tests or production code.

## Why time.Sleep is Problematic
- **Flaky tests**: too short → intermittent failure; too long → slow suite- **Race conditions**: sleep doesn't guarantee state change completed- **CI variability**: different machines have different speeds

## Replacement Patterns

### Pattern 1: Channel Signal

```g
o
// BEFOREgo doWork()time.Sleep(100 * time.Millisecond)checkResult()
// AFTERdone := make(chan struct{})go func() { defer close(done) doWork()}()select {case <-done: checkResult()case <-time.After(5 * time.Second): t.Fatal("timeout waiting for work")}
```

### Pattern 2: Polling with Timeout

```g
o
// AFTERdeadline := time.After(5 * time.Second)ticker := time.NewTicker(50 * time.Millisecond)defer ticker.Stop()for { select { case <-ticker.C: if conditionMet() { return // success } case <-deadline: t.Fatal("condition not met within timeout") }}
go// AFTERdeadline := time.After(5 * time.Second)ticker := time.NewTicker(50 * time.Millisecond)defer ticker.Stop()for { select { case <-ticker.C: if conditionMet() { return // success } case <-deadline: t.Fatal("condition not met within timeout") }}

```

### Pattern 3: sync.WaitGroup

```g
o
// AFTERvar wg sync.WaitGroupfor i := 0; i < workers; i++ { wg.Add(1) go func() { defer wg.Done() doWork() }()}wg.Wait()
go// AFTERvar wg sync.WaitGroupfor i := 0; i < workers; i++ { wg.Add(1) go func() { defer wg.Done() doWork() }()}wg.Wait()
```

### Pattern 4: Context with Timeout

```g
o
// AFTERctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)defer cancel()result, err := doWorkWithContext(ctx)if err != nil { t.Fatalf("work failed: %v", err)}
go// AFTERctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)defer cancel()result, err := doWorkWithContext(ctx)if err != nil { t.Fatalf("work failed: %v", err)}

```

## Decision Matrix
| Scenario | Recommended Pattern|
|----------|-------------------|
|Wait for single goroutine | Channel signal|
|Wait for multiple goroutines | sync.WaitGroup|
|Wait for external condition | Polling with timeout|
|Production code with deadline | Context with timeout|
|Test waiting for async result | Channel + time.After |

## Grep Command to Find time.Sleep

```bash
r
g
'time\.Sleep\(' --type go | rg -v '_test\.go' # production coderg 'time\.Sleep\(' --type go --glob '*_test.go' # test code
```
