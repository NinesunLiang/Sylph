# §L Race Condition Detection

## Run with Race Detector

```bash
g
o
test -race ./...go test -race -count=100 ./pkg/ # stress test

```

## Common Patterns to Test

### Shared State

```gofu
n
c
TestConcurrentAccess(t *testing.T) { counter := NewSafeCounter() var wg sync.WaitGroup for i := 0; i < 100; i++ { wg.Add(1) go func() { defer wg.Done() counter.Inc() }() } wg.Wait() if got := counter.Value(); got != 100 { t.Errorf("counter = %d, want 100", got) }}
```

### Channel-Based Synchronization

```gofu
n
c
TestAsync(t *testing.T) { done := make(chan struct{}) go func() { defer close(done) // async work }() select { case <-done: // success case <-time.After(5 * time.Second): t.Fatal("timeout waiting for async work") }}

```

## Rules- NEVER use `time.Sleep()` for synchronization- Use `sync.WaitGroup`, channels, or `context.WithTimeout`- Always run `-race` for concurrent code- Use `-count=N` to stress-test race conditions- Auto-append race tests when function touches shared state
