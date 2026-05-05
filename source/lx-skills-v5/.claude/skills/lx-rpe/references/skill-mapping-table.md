## Skill 映射表

>
> **调用方式**：所有 Skill 均通过 `Invoke the Skill tool with skill: "<name
> "` 调用，不使用斜杠命令。
| 步骤 | Skill（Skill tool name） | 项目类型 | 触发条件 | 模式|
|------|--------------------------|---------|---------|------|
|[2] | 无（直接设计） | 通用 | - | grep + readFile + LSP|
|[3] | `lx-pre-commit` | 通用 | 编译通过后必须执行 | 统一门禁（CR + 测试 + 补测）|
|[3] | ↳ `lx-code-review` | Go | lx-pre-commit 内部调用 | 专项规则 + auto-fix|
|[3] | ↳ `lx-golang-test` | Go | lx-pre-commit 内部检测缺口 | table-driven + mock|
|[3] | ↳ `lx-react-review` | 前端 | lx-pre-commit 内部调用 | 组件质量规则|
|[3] | ↳ `lx-frontend-test` | 前端 | lx-pre-commit 内部检测缺口 | Jest/Vitest + RTL|
|[4] | `lx-security-review` | Go | Step 3 通过后必须执行 | 15 条 + govulncheck|
|[4] | npm audit + ESLint security | 前端 | Step 3 通过后必须执行 | 依赖漏洞 + 代码模式扫描|
|[8] | git commit | 通用 | 验收通过后 | 需用户确认 |
