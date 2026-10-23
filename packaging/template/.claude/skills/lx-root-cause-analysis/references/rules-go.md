# Go 根因模式

## 常见 Go 根因分类
| 模式 | 典型根因 | 出现于 Why 层级|
|------|---------|---------------|
|Goroutine 泄漏 | 缺少 `ctx.Done()` / 无 `done` channel / 无界 `go func` | Why 1-2|
|nil 指针 | 链式调用前未检查 nil / interface 返回值未检查 | Why 1-2|
|竞态条件 | 共享状态无 `sync.Mutex` / channel / atomic 保护 | Why 2-3|
|连接池耗尽 | `rows.Close()` 未调用 / `defer` 位置错误 | Why 2-3|
|隐式假设 | interface 无文档约束 / 调用方假定执行顺序 | Why 4-5|
|错误吞没 | `recover()` 静默处理 / `_` 丢弃错误 | Why 2 |

## 症状专用搜索命令
| 症状 | 搜索命令|
|------|---------|
|Goroutine 泄漏 | `rg "go func" --type go` + 检查是否有对应的 `done`/`cancel`；`rg "ctx.Done()" --type go`|
|nil 指针 | `rg "\\\.\\\(\\\w+\\\)\\\." --type go` + 检查链式调用前的 nil 检查|
|竞态条件 | `git log --grep="race"` + `go test -race -count=20 ./...`|
|连接池问题 | `rg "sql\\\.Open\\\|db\\\.SetMaxOpenConns" --type go`|
|interface{} panic | `rg "\\\.\\\(" --type go` + 类型断言模式搜索|
|OOM / 内存泄漏 | `go tool pprof http://localhost/debug/pprof/heap`；在循环中 `rg "append(" --type go` |

## go-zero 专用模式
| 模式 | 根因 | Why 层级|
|------|------|---------|
|ServiceContext 泄漏 | ServiceContext 未正确初始化或连接未关闭（DB/Redis 句柄泄漏） | Why 2-3|
|RPC 超时传播失败 | RPC 调用未传递 ctx，或超时被 `context.Background()` 覆盖 | Why 3-4|
|logx 错误吞没 | `logx.Error(err)` 之后返回 `nil`——错误被静默丢弃给调用方 | Why 2 |

## go-zero 调试命令

```bash
# 检查 ServiceContext 连接清理rg "svcCtx\\\." --type go | grep -v "_test.go" | grep -v "Close\\\|cleanup"
# 检查 RPC 调用是否传递 ctx（context.Background() = 可疑）rg "context\\\.Background\\\(\\\)" --type go -A2 | grep -i "rpc\\\|call\\\|invoke"
# 检查 logx.Error 后跟 return nil（错误吞没）# 使用 AST-grep: ast-grep -p 'logx.Error($ERR)' --lang go
```

## Go 版本约束
| 版本 | 对根因分析的影响|
|------|---------------|
|< 1.21 | 无 `log/slog`；若项目同时使用 logx + slog，需在 Why 链中区分日志来源|
|≥ 1.22 | range 变量自动捕获；并行测试中不再需要 `tt := tt` 模式|
|任意版本 | `go test -race` 仅检测运行时路径的竞态；静态路径竞态需要 AST-grep 手动检查 |
