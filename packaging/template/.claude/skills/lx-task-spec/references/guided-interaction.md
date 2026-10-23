# 引导式交互（3 问）

逐个引导，每次只问一个。

## Q1: 任务名称
简短描述，如 "add-login-api"、"fix-memory-leak"

## Q2: 任务目标
具体需求，如 "在用户模块新增登录接口，支持手机号+验证码"

## Q3: 验收标准
可观测标准。用户说"帮我生成" → AI 自动生成 AC 草稿：

```
基于你的任务目标，建议以下验收标准：
AC-1 [功能]：{核心功能可正常调用} 验证：{具体命令} 期望：{预期结果}
AC-2 [测试]：{单元/集成测试通过} 验证：{测试命令} 期望：PASS
AC-3 [边界]：{关键边界场景}（如有） 验证：{边界验证方式} 期望：{期望行为}
这样可以吗？
```

生成规则：AC-1 必有 / AC-2 必有（Go→go test / 前端→npm test）/ AC-3 可选（识别不到则省略）/ 必须可观测可执行。

## 收集完成后

AI 生成 task_input YAML：

```yaml
task_input:
  task_name: "add-login-api"
  target: "在用户模块新增登录接口"
  pass_criteria:
    - id: "AC-1" type: test description: "接口返回 200" how_to_check: "curl..." expected: "200"
    - id: "AC-2" type: test description: "单元测试通过" how_to_check: "go test..." expected: "PASS"
  executor_mode: stepwise
  priority: p1
```

确认后进入 规划 → 执行 → 验收。3 问收集完毕直接开始，默认 stepwise + p1。
