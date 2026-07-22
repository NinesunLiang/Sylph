# Auto-Fix 模板

> 每条规则对应修复模板。优先复用现有组件，匹配项目风格。每个问题最多 2 次修复尝试。

| 规则 | 修复模板 |
|------|---------|
| A1 error 被吞 | 添加 `if err != nil { return ..., err }` |
| B1 goroutine 无控制 | 添加 `context.WithCancel` + `select { case <-ctx.Done() }` |
| B2 mutex 无 defer | `Lock()` 后添加 `defer Unlock()` |
| D2 接口过大 | 按职责域拆分为 ≤5 方法的子接口 |
| E1 循环拼接 | 替换为 `strings.Builder` |
| E6 循环内正则 | 提升到包级变量 |
| H1 无 nil 检查 | 函数入口添加 `if param == nil` |
| H2 map 无 comma-ok | 改为 `val, ok := m[key]` |
| H3 类型断言无 comma-ok | 改为 `v, ok := i.(Type)` |
| H4 slice 无边界检查 | 添加 `if len(items) == 0` |
| H5 资源未释放 | 添加 `defer resource.Close(ctx)` |
| H6 无超时 | 添加 `context.WithTimeout` |
