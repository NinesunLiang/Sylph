# Go 高级代码审查规则（14条，性能+可观测性）

> Enhance 域 skill。适用于高阶模型深度审查。
> 核心错误防护规则见 Base 版 `lx-code-review/references/rules-go.md`。

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

## G — 可观测性 (6条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| G1 | 错误路径无日志 | P1 | AST: `if err != nil` 块内无 log |
| G2 | 日志缺上下文 | P2 | grep 日志调用检查结构化字段 |
| G3 | context 未传递到日志 | P2 | AST: `logx.Error` 无 WithContext |
| G4 | 关键操作无日志 | P1 | 检查 DB/HTTP/状态机附近日志 |
| G5 | 日志级别不当 | P3 | 分析代码路径与级别匹配 |
| G6 | 缺 metric 埋点 | P2 | 检查 handler 入口 metric 调用 |

## C5 — goctl 代码同步 (1条)

| # | 规则 | 严重度 | 检查方式 |
|---|------|--------|---------|
| C5 | goctl 代码不同步 | P0 | 比对 .api/.proto 与 types.go |
