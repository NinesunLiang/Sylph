# hooks/ — CC 治理 Hook 脚本

> 每个 hook 一个 `.py` 文件，运行在 CC 事件触发点。
> Base 注册在 `.claude/settings.json`，Enhance 独有文件存于此但不在 Base settings 注册。

## 共享库

| 文件 | 角色 |
|------|------|
| `harness_core.py` | 核心共享库 — `hc_enabled`, `output_continue`, `hook_report`, `read_input` |
| `harness_lib.py` | 扩展共享库 — 自动从 `harness_core` 导入所有符号 |
| `hook-launcher.py` | Hook 调度器 — 从 settings.json 按名启动 hook |
| `(lib/)` | 共享库 _(`lifecycle_ssot.py` 等)_ |

## Base 注册 Hook（settings.json 激活）

| 类别 | Hook 文件 | 触发点 |
|------|-----------|--------|
| **门禁路由** | `pretool-gate.py` → `pretool_gates/*.py` | PreToolUse |
| **记分卡门禁** | `pretool-scorecard-gate.py` | PreToolUse:Edit/Write |
| **完成门禁** | `pre-completion-gate.py` | PreToolUse:TaskUpdate |
| **用户审批** | `pretool-user-approve.py` | UserPromptSubmit |
| **夜航模式** | `carroros-night-deny.py` | PreToolUse |
| **Claim审计** | `posttool-claim-audit.py` | PostToolUse:Edit/Write |
| **安全过滤** | `posttool-sensitive-filter.py` | PostToolUse |
| **输出校验** | `posttool-output-schema.py` | PostToolUse |
| **Error DNA 采集** | `error-dna.py` | PostToolUse |
| **完成审核** | `completion-gate.py` | PostToolUse:TaskUpdate |
| **会话启动** | `session-start.py` | SessionStart |
| **生命周期** | `precompact-lifecycle.py` | PreCompact |
| **飞轮停止** | `stop-flywheel.py` | PreCompact |
| **阅读追踪** | `read-tracker.py` | PostToolUse:Read |

## Base 未注册（Enhance 域 / 开发中）

这些文件存在于磁盘但不在 Base settings.json 注册，供 Enhanc 版本或按需激活：

| 文件 | 用途 |
|------|------|
| `posttool-bash-audit.py` | Bash 输出审计 — Enhance 版才启用 |
| `compound-verify-gate.py` | 复合 Verify Gate — 增强层 |
| `session-resume.py` | 会话恢复 — Enhance 域 |
| `token_writer.py` | Token 写回 — Enhance 域 |
| `turn-counter.py` | 轮次计数 — Enhance 域 |
| `verify_contract.py` | Gate Contract 验证 — 被 compound-verify-gate 引用 |
