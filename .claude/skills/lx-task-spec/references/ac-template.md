# AC 模板示例（lx-task-spec Q3 参考）

## 三段式 AC 格式

```A
C
-{N} [{类型}]：{描述} 验证：{具体命令或操作步骤} 成功：{期望输出/状态} 失败：{失败时的现象}
AC-{N} [{类型}]：{描述} 验证：{具体命令或操作步骤} 成功：{期望输出/状态} 失败：{失败时的现象}
```

## 示例

```A
C
-1 [功能]：登录接口返回 200 验证：curl -X POST /api/login -d '{"phone":"138xx","code":"1234"}' 成功：HTTP 200 + {"token": "..."} 失败：HTTP 4xx / 5xx
AC-2 [测试]：单元测试通过 验证：go test ./pkg/user/... -v 成功：--- PASS (全部测试名) 失败：--- FAIL 或 编译错误
AC-3 [边界]：空手机号返回 400 验证：curl -X POST /api/login -d '{}' 成功：HTTP 400 + {"error": "phone required"} 失败：HTTP 500 或 空响应
```
