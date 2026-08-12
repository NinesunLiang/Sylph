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
| **门禁路由** | `pretool-gate.py` → `pretool_gates/*.py` | PreToolUse（L1 5 道真安全门 / L2 15 道含末端校验） |
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

## 已删除 Hook（index15 降噪·ROI 清理）

以下 hook 因 ROI 考量已删除（`git rm` 可恢复），不属有效治理资产：

| 已删除文件 | 删除原因 |
|------|------|
| `posttool-bash-audit.py` | 仅被 error-dna 注释提及，无实际注册/引用 |
| `session-resume.py` | 零引用死代码 |
| `token_writer.py` | harness.yaml 显式禁用（token_writer: false） |
| `turn-counter.py` | hc_enabled 门控但未启用 |
| `compound-verify-gate.py` / `verify_contract.py` | 文档描述但文件从未存在（虚构引用） |
