# Go Test Commands Quick Reference

## Basic

```
bashgo
test ./... # Run all testsgo test ./pkg/... # Run package testsgo test -v ./... # Verbose outputgo test -run TestName ./pkg/ # Run specific testgo test -run TestGroup/subtest ./pkg/ # Run specific subtest

```

## Race & Coverage

```
bashgo
test -race ./... # Race detectiongo test -coverprofile=c.out ./... # Coverage profilego tool cover -html=c.out # Coverage HTMLgo tool cover -func=c.out # Coverage summary
```

## Benchmark

```
bashgo
test -bench=. ./... # All benchmarksgo test -bench=BenchmarkXxx -benchmem # With memorygo test -bench=. -count=5 # Stable results

```

## Fuzz (Go ≥ 1.18)

```
bashgo
test -fuzz=FuzzXxx -fuzztime=30s # Fuzz for 30s
```

## Flags

```
bash-short # Skip slow tests-count=1 # Disable cache-timeout=5m # Set timeout-parallel=4 # Max parallel tests-failfast # Stop on first failure

```
