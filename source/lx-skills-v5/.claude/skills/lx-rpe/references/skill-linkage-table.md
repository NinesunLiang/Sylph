## 跨 Skill 联动

| 方向 | Skill | 项目类型 | 触发条件 | 数据契约|
|------|-------|---------|---------|---------|
|内部调用 | `lx-pre-commit` | 通用 | Step 3 编译通过后必须执行 | 传递：变更文件；接收：CR+测试+补测综合判定|
|↳ | `lx-code-review` | Go | lx-pre-commit 内部调用 | 专项规则判定 + auto-fix 结果|
|↳ | `lx-golang-test` | Go | lx-pre-commit 检测测试缺口 | 缺口函数名 + 测试类型|
|↳ | `lx-react-review` | 前端 | lx-pre-commit 内部调用 | 前端组件质量判定|
|↳ | `lx-frontend-test` | 前端 | lx-pre-commit 检测测试缺口 | 缺口组件/Hook + 测试类型|
|内部调用 | `lx-security-review` | Go | Step 4 必须执行 | 传递：变更文件；接收：15 条 + govulncheck 判定|
|内部调用 | npm audit + ESLint security | 前端 | Step 4 必须执行 | 传递：变更文件；接收：依赖漏洞+代码模式判定|
|内部调用 | `lx-pre-commit` | 通用 | 里程碑全量检查 | 传递：全部文件；接收：综合判定|
|关联 | `lx-task-spec` | 通用 | 里程碑 buglist 中中等复杂问题 | 传递：问题描述 + AC → task-spec|
|上游来自 | `lx-tdd-spec` | 通用 | 新特性需求规格 | 接收：AC 列表 + GWT 场景 |
