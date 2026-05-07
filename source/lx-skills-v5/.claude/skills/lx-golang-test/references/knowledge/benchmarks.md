# §G Benchmarks

## Pattern

```gofu
n
c BenchmarkXxx(b *testing.B) { // Setup outside loop input := prepareInput()
 b.ResetTimer() for i := 0; i < b.N; i++ { result = FuncUnderTest(input) }}
// Allocation benchmarkfunc BenchmarkAlloc(b *testing.B) { b.ReportAllocs() for i := 0; i < b.N; i++ { _ = FuncUnderTest(input) }}
```

## Run Commands

```bash
g
o
test -bench=BenchmarkXxx -benchmem ./...go test -bench=. -count=5 -benchtime=3s ./pkg/benchstat old.txt new.txt # compare results

```

## Rules- Setup outside `b.N` loop- `b.ResetTimer()` after expensive setup- `b.ReportAllocs()` for allocation tracking- Prevent compiler optimization: assign to package-level `var result`- Run multiple times with `-count=5` for stable results- Use `benchstat` to compare before/after
