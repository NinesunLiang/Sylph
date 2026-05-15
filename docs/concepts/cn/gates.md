# Gates（门禁系统）


> **所属层级**: 2-规则(骨架层) — Gate/Guard 门禁体系

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

## Gate / Guard 分类

Carror OS 的拦截器分为两类：

- **Gate（门禁）**：阻断后需要用户明确授权才放行（CAPTCHA 验证码机制）
- **Guard（守卫）**：自动判定，无需用户交互（如范围冻结、上下文监控）

当前共 11 个活跃门禁/守卫：

### 执行安全

**permission-gate（权限门禁）**
拦截危险操作（`rm -rf`、`git push --force`、`sudo`、base64 编码绕过）。CAPTCHA 验证码确认后才放行。
Hook: `permission-gate.sh`

**privacy-gate（隐私门禁）**
拦截敏感文件读取（`.env`、`id_rsa`、`secret.yml`）。对 AI 完全屏蔽凭据内容。
Hook: `privacy-gate.sh`

**pretool-sensitive-edit（敏感文件编辑门禁）**
拦截对治理文件（AGENTS.md、settings.json、harness.yaml、SKILL.md）的直接编辑。CAPTCHA 验证码确认。
Hook: `pretool-sensitive-edit.sh`

**subagent-guard（子代理门禁）**
限制子 Agent 类型和用量，防止账单雪崩。三层防线：声明层约束 + 执行层记录 + 人工层告警。
Hook: `subagent-guard.sh`

### 质量保障

**completion-gate（完成门禁）**
拦截虚假完成声明。要求 VERIFIED 证据（测试输出、构建日志），证据评分 ≥ 3.0 才放行。
Hook: `completion-gate.sh`

**pre-completion-gate（前置完成门禁）**
在 AI 调用 TaskUpdate(completed) 前拦截，检查证据文件是否存在且新鲜（5 分钟内），减少浪费轮次。
Hook: `pre-completion-gate.sh`

**edit-guard（编辑守卫）**
强制 Read-before-Edit：AI 必须先读取文件内容后才能编辑，防止基于记忆的盲目修改。
Hook: `edit-guard.sh`

**pretool-edit-scope（范围冻结守卫）**
拦截越界编辑：AI 修改非当前任务范围内的文件时自动阻止，防止"顺便重构"。
Hook: `pretool-edit-scope.sh`

### 上下文管理

**context-guard（上下文守卫）**
监控会话 Token 消耗。危险阈值默认 80% → 阻断写操作（Edit/Write），保留诊断通道（Read/Grep/Bash）。支持 `context-force-override` 逃生门。
Hook: `context-guard.sh`

### 哲学执行

**plan-gate（规划门禁）**
非琐碎任务强制规划。L2+ 任务必须先出执行计划，经用户确认后才允许执行。
Hook: `plan-gate.sh`

**pretool-ask-guard（哲学先行门禁）**
铁律 #8 的物化。拦截"多此一问"：AI 在问人之前，若哲学已覆盖该问题（如"需要我提交吗？"），阻断提问并强制 AI 直接执行。
Hook: `pretool-ask-guard.sh`

---

## 实现方式

每个 Gate/Guard 实现为 `.claude/hooks/` 下的一个 Hook 脚本。Hook 通过 stdin 接收原始工具输入，根据规则评估后返回：

- `exit 0` — 放行
- `exit 2` — 阻断（Gate 类附带 CAPTCHA，Guard 类附带原因说明）
- `exit 1` — 错误（Hook 本身故障）

具体实现见下列 Hook 文件：

| Gate / Guard | Hook 文件 | 类型 |
| :--- | :-------- | :--- |
| completion-gate | `completion-gate.sh` | Gate |
| pre-completion-gate | `pre-completion-gate.sh` | Gate |
| permission-gate | `permission-gate.sh` | Gate |
| privacy-gate | `privacy-gate.sh` | Gate |
| pretool-sensitive-edit | `pretool-sensitive-edit.sh` | Gate |
| subagent-guard | `subagent-guard.sh` | Guard |
| edit-guard | `edit-guard.sh` | Guard |
| pretool-edit-scope | `pretool-edit-scope.sh` | Guard |
| context-guard | `context-guard.sh` | Guard |
| plan-gate | `plan-gate.sh` | Gate |
| pretool-ask-guard | `pretool-ask-guard.sh` | Gate |
