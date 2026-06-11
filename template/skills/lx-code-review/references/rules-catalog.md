# 8 类 39 条扫描规则

## A — Error Handling (3条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| A1 | error 被吞 | P0 | AST: `$_ = $FN($$$)` |
| A2 | error 未 wrap | P1 | grep `fmt.Errorf` / `errors.Wrap` |
| A3 | error 消息格式 | P2 | grep `errors.New("` |

## B — Concurrency Safety (3条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| B1 | goroutine 无生命周期控制 | P0 | AST: `go $FN($$$)` |
| B2 | mutex 无 defer Unlock | P1 | AST: `.Lock()` → 检查 defer |
| B3 | 共享变量无保护 | P1 | 分析 goroutine 闭包变量捕获 |

## C — go-zero 架构 (6条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| C1 | handler 含业务逻辑 | P0 | 检查 handler 文件 DB 操作 |
| C2 | logic 直接操作 DB | P1 | 检查 logic 文件 SQL/ORM |
| C3 | svc 未通过 ServiceContext 注入 | P1 | 检查全局变量或直接 new |
| C4 | middleware 链顺序不当 | P1 | 检查路由注册顺序 |
| C5 | goctl 代码不同步 | P0 | 比对 .api/.proto 与 types.go |
| C6 | yaml 缺安全配置 | P1 | 检查 Timeout:0 / MaxConns:0 |

## D — Go 惯用法 + 接口设计 (5条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| D1 | 导出函数缺 doc comment | P2 | AST: 导出函数前一行注释 |
| D2 | 接口过大（>5方法） | P1 | AST: `type $NAME interface` |
| D3 | 包名与目录名不一致 | P2 | 比较 package 声明与目录名 |
| D4 | 接口有空实现 | P1 | AST: `return nil` 空方法 |
| D5 | 接口方法跨抽象层级 | P2 | 判断方法是否属同一业务域 |

## E — 性能反模式 (7条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| E1 | 循环内字符串拼接 | P1 | AST: 循环内 `$S += $V` |
| E2 | slice append 无预分配 | P2 | 检查 for + append 模式 |
| E3 | 不必要的 fmt.Sprintf | P3 | grep 简单拼接 |
| E4 | map 未预分配 | P2 | 检查 `map[K]V{}` + 循环赋值 |
| E5 | 大 struct 值接收器 | P2 | AST: 值类型方法接收器 |
| E6 | 循环内 MustCompile | P1 | grep 循环内 regexp.MustCompile |
| E7 | 热路径中 defer | P2 | 检查 for 循环体内 defer |

## F — 代码结构 (3条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| F1 | 函数超过 80 行 | P1 | 计算函数体行数 |
| F2 | 嵌套深度超过 4 层 | P2 | 分析缩进层次 |
| F3 | 重复代码块（≥10 行） | P2 | AST 结构比对 |

## G — 可观测性 (6条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| G1 | 错误路径无日志 | P1 | AST: `if err != nil` 块内无 log |
| G2 | 日志缺上下文 | P2 | grep 日志调用检查结构化字段 |
| G3 | context 未传递到日志 | P2 | AST: `logx.Error` 无 WithContext |
| G4 | 关键操作无日志 | P1 | 检查 DB/HTTP/状态机附近日志 |
| G5 | 日志级别不当 | P3 | 分析代码路径与级别匹配 |
| G6 | 缺 metric 埋点 | P2 | 检查 handler 入口 metric 调用 |

## H — 鲁棒性 (6条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| H1 | 公开函数指针参数无 nil 检查 | P1 | AST: 公开函数指针参数 |
| H2 | map 取值未用 comma-ok | P1 | AST: 单返回值 map 访问 |
| H3 | 类型断言无 comma-ok | P0 | AST: `$VAR.($TYPE)` |
| H4 | slice 首元素无 len 检查 | P0 | grep `[0]` 检查守卫 |
| H5 | 资源获取后无 defer 释放 | P1 | grep 资源获取检查 defer |
| H6 | 外部调用无超时 | P1 | grep http.Get 检查 WithTimeout |

## 误报排除

标记 FP（不报告）：注释/字符串中 | `//nolint` 且理由合理 | error 已通过其他路径处理 | go-zero 生成代码 | H1 内部函数 → P3 | H2 只读取不分支 → "待确认"
