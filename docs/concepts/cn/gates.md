# Gates（门禁系统）

> **在 AI 与文件系统边界实施物理拦截。**

---

## 什么是 Gate？

Gate 不是一个建议。它是一个位于 Hook 层的**物理拦截器**，在 AI 行为到达文件系统之前将其截停。

大多数 AI 安全工具使用 **Prompt 约束**——在系统提示词中写入规则并让 AI 自我监督。这行不通，因为：
- 长对话中 AI 会忽略或遗忘规则
- AI 存在自我验证偏差：即使没有遵守也相信自己在遵守

Carror OS 的 Gate 不同。它位于 AI 和工具调用之间。当 AI 尝试写文件、执行命令或读取敏感数据时，Gate 截获原始工具输入并决定：**放行、阻断、或升级。**

AI 无法用语言绕过 Gate。Gate 不听提示词——它只读取原始工具输入。

---

## 四种 Gate 类型

### completion-gate（完成门禁）

拦截未经验证的完成声明。当 AI 说"完成了"但未提供证据（测试输出、构建日志）时，Gate 阻断提交并强制验证。

触发条件：AI 声明任务完成但未附加证据。

### permission-gate（权限门禁）

拦截危险的文件系统操作（`rm -rf`、`git push --force`、批量删除）。要求用户明确确认后才放行。

触发条件：工具输入匹配危险命令模式。

### privacy-gate（隐私门禁）

拦截敏感文件读取（`.env`、`id_rsa`、`secret.yml`、凭据文件）。将访问路由到本地金库，完全对 AI 模型屏蔽凭据。

触发条件：文件路径匹配敏感文件模式。

### context-guard（上下文守卫）

监控会话 Token 消耗。在上下文窗口达到**危险阈值**（默认 80%）时，物理终止会话（`exit 2`），防止幻觉驱动的破坏。

触发条件：实时 Token 用量超过危险阈值。
配置：`harness.yaml` 中的 `context_guard.warn_threshold` / `context_guard.danger_threshold`（参见[上下文控制](./context-control.md)）。

---

## 实现方式

每个 Gate 实现为 `.claude/hooks/` 下的一个 Hook 脚本。Hook 通过 stdin 接收原始工具输入，根据 Gate 规则评估后返回：

- `exit 0` — 放行
- `exit 2` — 阻断（附带选项菜单）
- `exit 1` — 错误（Hook 本身故障）

具体实现见下列 Hook 文件：

| Gate | Hook 文件 |
| :--- | :-------- |
| completion-gate | `.claude/hooks/completion-gate.sh` |
| permission-gate | `.claude/hooks/permission-gate.sh` |
| privacy-gate | `.claude/hooks/privacy-gate.sh` |
| context-guard | `.claude/hooks/context-guard.sh` |
