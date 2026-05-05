# Go 编码规范（lx-rpe Step 2/3 Go 项目加载）

## 架构约束

- Handler 禁止直接调用 Model，必须经由 Logic/Service 层
- 分层：Handler → Logic → Model/Repo
- 接口 ISP：单接口方法数 ≤5

## 命名规范（§4.2）

- 导出函数：PascalCase
- 内部变量：camelCase
- 常量：全大写下划线（ERROR_CODE）
- 接口名：动词+er（Reader/Writer/Handler）

## 错误处理

- 错误必须含上下文：`fmt.Errorf("doing X: %w", err)`
- 禁止裸 `err != nil` 返回（必须 wrap）
- 所有 error 必须被处理（禁止 `_`忽略）

## 代码质量

- 函数体 ≤50 行
- 导入三段式：标准库 / 第三方 / 内部包（空行分隔）
- 日志纯英文
- 禁止魔法数字（使用具名常量）

## 并发

- goroutine 必须有 WaitGroup 或 channel 控制生命周期
- 共享状态必须有 mutex 保护
- context 必须传递，禁止 context.Background() 在业务逻辑中

## 反模式（禁止）

- 循环内 DB 查询（N+1）
- 大 struct 值传递（>64B 用指针）
- 无超时保护的网络调用
- init() 函数（除框架初始化）
