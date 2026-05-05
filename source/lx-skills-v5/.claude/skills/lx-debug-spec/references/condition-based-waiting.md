# Condition-Based Waiting (Replacing time.Sleep)

Use when code contains `time.Sleep()` or fixed timeouts in tests or production code.

## Why time.Sleep is Problematic

- **Flaky tests**: too short → intermittent failure; too long → slow suite
- **Race conditions**: sleep doesn't guarantee state change completed
- **CI variability**: different machines have different speeds

## Replacement Patterns

### Pattern 1: Channel Signal

```
go// BEFOREgo doWork()time.Sleep(100 * time.Millisecond)checkResult()
// AFTERdone := make(chan struct{})go func() { defer close(done) doWork()}()select {case <-done: checkResult()case <-time.After(5 * time.Second): t.Fatal("timeout waiting for work")}
```

### Pattern 2: Polling with Timeout

```
go// AFTERdeadline := time.After(5 * time.Second)ticker := time.NewTicker(50 * time.Millisecond)defer ticker.Stop()for { select { case <-ticker.C: if conditionMet() { return // success } case <-deadline: t.Fatal("condition not met within timeout") }}

```

### Pattern 3: sync.WaitGroup

```
go// AFTERvar wg sync.WaitGroupfor i := 0; i < workers; i++ { wg.Add(1) go func() { defer wg.Done() doWork() }()}wg.Wait()
```

### Pattern 4: Context with Timeout

```
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

```
bashrg
'time\.Sleep\(' --type go | rg -v '_test\.go' # production coderg 'time\.Sleep\(' --type go --glob '*_test.go' # test code
```
