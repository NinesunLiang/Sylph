---

name: lx-perf-analysis

version: v4.0.0

description: "Go performance analysis: CPU/memory profiling, goroutine leak detection, benchmark analysis, optimization verification."

when_to_use: "Use when user says 'performance', 'slow', 'profile', 'benchmark', 'memory leak', 'goroutine leak', 'optimize', 'pprof'."

model: sonnet

argument-hint: "<function/package name or performance symptom>"

paths:

 - "*.go"

 - "go.mod"

 - "*_test.go"

harness_version: ">=1.1.0"

---

# Go 性能分析与优化

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析性能分析目标|
|context_collector | `../../nodes/context_collector.md` | 收集基准数据 + 已知反模式|
|scanner | `../../nodes/scanner.md` | 按 6 域性能规则扫描|
|auto_fixer | `../../nodes/auto_fixer.md` | 性能优化方案实施|
|verifier | `../../nodes/verifier.md` | 优化后 benchmark 验证|
|report_generator | `../../nodes/report_generator.md` | 性能分析报告|
|behavior_rules | `../../nodes/behavior_rules.md` | 分析阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 分析目标定义|
|severity | `../../schemas/atomic/severity.yaml` | 性能问题严重度|
|finding | `../../schemas/atomic/finding.yaml` | 性能瓶颈发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 性能分析报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 优化实施记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 分析判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长分析会话的上下文总结 |

### 状态机
本 skill 使用**私有 analyze→optimize→verify 流程**，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [baseline → profile → optimize → verify] → done

### 私有节点
本 skill 无私有节点。

---

## 执行流程

### Step 0: 入口检查
无参数时加载 `@../../nodes/interactive_prompt.md`，进入引导式问答。
加载 `@../../nodes/behavior_rules.md`，应用分析阶段行为约束。

```bash
l
s
go.mod # 缺失 → "不适用"grep -rl "func Benchmark" --include="*_test.go" . # 检查现有 benchmark
```

### Step 1: 解析分析目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。根据症状分类到分析域：
| 症状 | 分析域 | 主要工具|
|------|--------|---------|
|"接口慢"、"响应时间长" | CPU | pprof CPU profile + benchmark|
|"内存涨"、"OOM"、"GC 频繁" | Memory | pprof heap + allocs profile|
|"goroutine 数量增长"、"泄漏" | Goroutine | pprof goroutine + runtime 监控|
|"数据库慢"、"查询超时" | I/O | SQL 分析 + 连接池检查|
|"锁争用"、"并发吞吐低" | Concurrency | pprof mutex/block profile|
|不确定 / 通用优化 | 全域 | 基准测试 → 热点定位 |\|

### Step 2: 收集基线
加载 `@../../nodes/context_collector.md`，收集：现有 Benchmark 函数、`claude-next.md` 中性能相关条目、目标函数完整代码、已知性能反模式（循环内 string +=、未预分配 slice/map、大结构体值传递、defer 在热循环内等）。

### Step 3: 剖析与瓶颈定位
加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的剖析规则：
**域 A — CPU 剖析**：`go test -bench=BenchmarkTarget -cpuprofile=cpu.prof -count=3` → `go tool pprof -top -cum cpu.prof` → top 10 累积耗时函数
**域 B — 内存剖析**：`go test -bench=BenchmarkTarget -memprofile=mem.prof -memprofilerate=1` → `go tool pprof -top -alloc_space mem.prof` + 逃逸分析 `go build -gcflags="-m -m"`
**域 C — Goroutine 泄漏**：测试前后 `runtime.NumGoroutine()` 对比，检查未关闭 channel/context、缺少退出信号的 `go func()`
**域 D — I/O 性能**：SQL N+1 查询、缺少索引、连接池配置（MaxOpenConns/MaxIdleConns）、网络超时/重试/连接复用
**域 E — 并发效率**：`go test -bench=BenchmarkTarget -blockprofile=block.prof -mutexprofile=mutex.prof` → 锁持有时间、锁粒度、channel 缓冲区大小、sync.Pool 使用合理性

#### 优化模式库（本 skill 私有领域知识）
| 模式 | 适用场景 | 预期效果|
|------|---------|---------|
|**O1 预分配** | slice/map 已知容量 | 减少 allocs，降低 GC|
|**O2 strings.Builder** | 循环内字符串拼接 | O(n) → O(n)，减少分配|
|**O3 sync.Pool** | 高频临时对象 | 减少 heap 分配|
|**O4 指针接收器** | 大结构体（>64B）方法 | 避免复制|
|**O5 减少逃逸** | 热路径变量逃逸到堆 | stack 分配，零 GC|
|**O6 批量操作** | 循环内单条 DB/IO 操作 | 减少 I/O 往返|
|**O7 索引优化** | 慢 SQL 查询 | 查询时间数量级提升|
|**O8 连接池调优** | DB/Redis 连接瓶颈 | 提高吞吐|
|**O9 分段锁** | 全局锁热争用 | 降低锁等待|
|**O10 并行化** | CPU 密集且可分治 | 利用多核 |\|
**反模式拦截**（自动拒绝）：过早优化非热路径、用 `unsafe` 替代正常优化、增加 `GOMAXPROCS` 不解决根本问题、用缓存掩盖 O(n²)、牺牲可读性的微优化（<5% 提升）。

### Step 4: 优化方案与实施
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 上述优化模式库。每个方案必须包含：瓶颈位置（file:line）、问题分析、优化代码（before/after）、预期效果（量化）、风险评估。**单一变量原则**：每次只实施一个优化。

### Step 5: 验证
加载 `@../../nodes/verifier.md`，传入 `fix_record[]` + 原始 `finding[]`。验证序列：编译 → 功能测试 → 性能 benchmark → -race 检测 → 对比基线。

### Step 5.7: 经验沉淀
优化实施成功（性能改善 ≥10%）时，追加到 `.claude/claude-next.md`：

```markdown
##
[Perf Analysis 反哺] {优化模式}: {效果}- **文件**: `{file:line}` - **问题**: {瓶颈一句话} - **改进**: {优化方式} - **效果**: {Before → After}- **来源**: lx-perf-analysis

```

**跳过条件**：同类模式已有 ≥3 条 / 微优化（改善 <10%）。

### Step 5.8: 飞轮日志
| 触发条件 | 执行命令|
|---------|---------|
|严重性能问题 | `echo "$(date +%Y-%m-%d),perf_critical,P0,$(basename $(pwd))" >> ~/.claude/flywheel-buffer.jsonl`|
|性能建议 | `echo "$(date +%Y-%m-%d),perf_suggestion,P1,$(basename $(pwd))" >> ~/.claude/flywheel-buffer.jsonl` |\|

### Step 6: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。输出含基线数据对比表、瓶颈分析、优化措施、验证结果、后续建议。

## 错误恢复与中止条件- 无 `go.mod` → "不适用"- 无法运行 benchmark 且无 profiling 数据 → "受阻"报告- 优化后性能回归超过 10% → 全部回滚- 3 个优化方案均无效 → 输出"部分优化"报告，建议架构级调整

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|pprof 不可用 | CPU/内存分析 | 用 go test -benchmem 获取基础内存数据|
|无法复现性能问题 | 压测复现 | 记录"[无法稳定复现]"，分析代码路径|
|基准测试波动>20% | 对比分析 | 增加 -count=5 取平均值，标注置信度 |
