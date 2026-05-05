# Go 优化模式库

## O1 — 预分配 Slice/Map

**适用场景**：已知容量的 slice 或 map。

```
go// Before ❌var users []Userfor _, raw := range raws { users = append(users, convert(raw))}
// After ✅users := make([]User, 0, len(raws))for _, raw := range raws { users = append(users, convert(raw))}
```
**预期效果**：减少 allocs/op（每次扩容 = 1 次分配 + 1 次复制），典型改善 30-70%。

---

## O2 — strings.Builder 替代字符串拼接

**适用场景**：循环内或多次字符串拼接。

```
go// Before ❌ O(n²)var result stringfor _, item := range items { result += item.Name + ","}
// After ✅ O(n)var b strings.Builderb.Grow(len(items) * avgLen) // 可选：预估容量for _, item := range items { b.WriteString(item.Name) b.WriteByte(',')}result := b.String()
```
**预期效果**：大量拼接时 ns/op 降低 90%+，allocs/op 从 O(n) 降到 O(1)。

---

## O3 — sync.Pool 复用临时对象

**适用场景**：高频创建的临时对象（buffer、struct），且对象生命周期短。

```
go// Before ❌func process(data []byte) { buf := make([]byte, 4096) // use buf...}
// After ✅var bufPool = sync.Pool{ New: func() interface{} { b := make([]byte, 4096) return \&b },}
func process(data []byte) { bp := bufPool.Get().(*[]byte) buf := *bp defer func() { bufPool.Put(bp) }() // use buf...}
```
**预期效果**：减少 heap allocs，降低 GC 压力。注意：不适合长生命周期对象。

---

## O4 — 指针接收器避免复制

**适用场景**：方法接收器为大结构体（>64 bytes）。

```
go// Before ❌ 每次调用复制整个结构体func (c Config) Validate() error { ... }
// After ✅ 传指针func (c *Config) Validate() error { ... }
```
**判断标准**：`unsafe.Sizeof(struct{})` > 64 → 用指针。**注意**：一致性原则——同一类型的所有方法应使用相同的接收器类型。

---

## O5 — 减少逃逸（Stack 分配）

**适用场景**：热路径中变量逃逸到堆。

```
go// Before ❌ result 逃逸到堆func process() *Result { result := \&Result{Value: compute()} return result}
// After ✅ 调用方分配，被调方填充func process(result *Result) { result.Value = compute()}
```
**检测**：`go build -gcflags="-m" ./...` 查看 "escapes to heap"。**注意**：仅在 profiling 证实为瓶颈时优化，不要过度。

---

## O6 — 批量 I/O 操作

**适用场景**：循环内单条 DB/网络操作。

```
go// Before ❌ N 次 DB 往返for _, id := range ids { user, _ := db.GetUser(ctx, id) results = append(results, user)}
// After ✅ 1 次 DB 往返users, err := db.GetUsersByIDs(ctx, ids)
```
**预期效果**：N 次往返 → 1 次，延迟降低 (N-1) × RTT。

---

## O7 — 索引优化

**适用场景**：慢 SQL 查询。
**诊断**：

```
sqlEX
PLAIN
ANALYZE SELECT ... WHERE ...;

```
**常见问题**：
- 全表扫描（Seq Scan）→ 添加索引
- 索引失效（函数包裹、类型不匹配）→ 修正查询
- N+1 查询 → 改为 JOIN 或 IN 查询

---

## O8 — 连接池调优

**适用场景**：DB/Redis 连接成为瓶颈。

```
go// 合理配置db.SetMaxOpenConns(25) // 不超过 DB 最大连接数 / 实例数db.SetMaxIdleConns(10) // 略低于 MaxOpenConnsdb.SetConnMaxLifetime(5 * time.Minute)db.SetConnMaxIdleTime(3 * time.Minute)

```

**诊断**：`db.Stats()` 查看 `WaitCount`（等待连接次数）、`WaitDuration`（等待总时长）。

---

## O9 — 分段锁（Sharded Lock）

**适用场景**：全局 `sync.Mutex` 热争用。

```
go// Before ❌ 全局锁type Cache struct { mu sync.RWMutex items map[string]Item}
// After ✅ 分段锁const shardCount = 32
type Cache struct { shards [shardCount]struct { mu sync.RWMutex items map[string]Item }}
func (c *Cache) getShard(key string) *shard { h := fnv.New32a() h.Write([]byte(key)) return \&c.shards[h.Sum32()%shardCount]}
```
**预期效果**：锁争用降低至 1/N（N=分段数）。**替代方案**：`sync.Map`（读多写少场景）。

---

## O10 — 并行化

**适用场景**：CPU 密集且可分治的任务。

```
go// Before ❌ 串行for _, item := range items { results = append(results, heavyCompute(item))}
// After ✅ 并行（使用 errgroup）g, ctx := errgroup.WithContext(ctx)results := make([]Result, len(items))for i, item := range items { i, item := i, item g.Go(func() error { results[i] = heavyCompute(item) return nil })}if err := g.Wait(); err != nil { return err}
```
**注意**：
- 仅在任务 CPU 密集且互不依赖时使用
- I/O 密集任务需控制并发数（`semaphore` 或带缓冲 channel）
- 小任务并行化反而更慢（goroutine 调度开销）
