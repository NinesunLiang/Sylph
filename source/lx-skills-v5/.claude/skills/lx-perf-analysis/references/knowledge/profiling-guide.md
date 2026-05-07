# Go Profiling 指南

## 前置条件- Go ≥ 1.21（推荐）- 目标 package 有 `_test.go`（用于 benchmark）- 若分析运行时服务 → 需要 pprof HTTP endpoint

## CPU Profiling

### 通过 Benchmark

```bash
# 生成 CPU profilego test -bench=BenchmarkTarget -cpuprofile=cpu.prof -count=3 -benchtime=5s ./pkg/...

# 分析 top 函数（按累积耗时）go tool pprof -top -cum cpu.prof

# 查看特定函数的逐行耗时go tool pprof -list=TargetFunction cpu.prof

# Web 可视化（需要 graphviz）go tool pprof -http=:8080 cpu.prof
```

### 通过 HTTP endpoint

```bash
#
采集 30 秒 CPU profilecurl -o cpu.prof http://localhost:6060/debug/pprof/profile?seconds=30go tool pprof -top cpu.prof

```

### 解读要点- **flat**: 函数本身耗时（不含调用的子函数）- **cum**: 累积耗时（含调用的子函数）- **关注**: cum% > 10% 的函数是优化候选- **热路径**: 从 top cum 函数沿调用图向下追踪

## Memory Profiling

### Heap (在用内存)

```bash
g
o test -bench=BenchmarkTarget -memprofile=mem.prof -memprofilerate=1 ./pkg/...

# 按分配空间排序go tool pprof -top -alloc_space mem.prof

# 按在用空间排序（检测泄漏）go tool pprof -top -inuse_space mem.prof

# 查看特定函数的分配go tool pprof -list=TargetFunction mem.prof
```

### 逃逸分析

```bash
# 查看哪些变量逃逸到堆go build -gcflags="-m -m" ./pkg/... 2>&1 | grep "escapes to heap"

# 更详细（含内联决策）go build -gcflags="-m -m -l" ./pkg/... 2>&1
```

### 解读要点- **alloc_space**: 总分配量（吞吐视角）- **inuse_space**: 当前在用量（泄漏视角）- **allocs/op**: benchmem 输出的每次操作分配次数- **B/op**: 每次操作分配字节数- **关注**: allocs/op > 0 且在热路径 → 优化候选

## Goroutine 分析

### 检测泄漏

```bash
# 获取 goroutine dumpcurl http://localhost:6060/debug/pprof/goroutine?debug=2 > goroutine.txt

# 在测试中检测# before := runtime.NumGoroutine()# <run test># time.Sleep(100ms) // 等待 goroutine 退出# after := runtime.NumGoroutine()# assert after <= before + 1
```

### 竞争检测

```bash
# 启用竞争检测器go test -race -count=20 ./pkg/...

# 高并发场景go test -race -count=50 -parallel=8 ./pkg/...
```

### 解读要点- goroutine dump 中大量相同堆栈 → 泄漏- 泄漏常见原因：未关闭 channel、未取消 context、阻塞的 select 无 default/timeout- -race 报告包含两个 goroutine 的堆栈 → 定位共享变量

## 锁与阻塞分析

### Block Profile

```bash
g
o
test -bench=BenchmarkTarget -blockprofile=block.prof ./pkg/...go tool pprof -top block.prof
```

### Mutex Profile

```bash
g
o
test -bench=BenchmarkTarget -mutexprofile=mutex.prof ./pkg/...go tool pprof -top mutex.prof

```

### 解读要点- block profile: 显示 goroutine 阻塞在哪里等待- mutex profile: 显示锁竞争热点- 高延迟的 mutex → 考虑分段锁或无锁数据结构

## Benchmark 最佳实践

```gofu
n
c BenchmarkTarget(b *testing.B) { // Setup（不计入计时） setup := prepareTestData()
 b.ResetTimer() b.ReportAllocs()
 for i := 0; i < b.N; i++ { target(setup) }}
```

### 可靠结果的要求- `-count=5` 以上（统计显著性）- `-benchtime=3s` 以上（短函数需要更长）- 比较时使用 `benchstat`：`go install golang.org/x/perf/cmd/benchstat\@latest`- 关闭 CPU 频率缩放（如可能）- 避免在 CI 中做性能对比（噪声大）
