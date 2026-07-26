# hooks/ — CC 治理 Hook 脚本

> 每个 hook 一个 `.py` 文件，运行在 CC 事件触发点。
> 注册在 `.claude/settings.json` 中。

## 架构

| 文件 | 角色 |
|------|------|
| `harness_core.py` | 核心共享库 — `hc_enabled`, `output_continue`, `hook_report`, `read_input` |
| `harness_lib.py` | 扩展共享库 — 自动从 `harness_core` 导入所有符号 |
| `hook-launcher.py` | Hook 调度器 — 从 settings.json 按名启动 hook |
| (lib/) | 共享库 _(`agentic-ui.py`, `lifecycle_ssot.py`)_ |

## Hook 分类

| 类别 | Hook 文件 | 触发点 |
|------|-----------|--------|
| **门禁（G1-G6）** | `pretool-gate.py` | PreToolUse |
| **完成门禁** | `completion-gate.py`, `pre-completion-gate.py` | PreToolUse / UserPromptSubmit |
| **用户审批** | `pretool-user-approve.py` | PreToolUse |
| **Bash审计** | `posttool-bash-audit.py` | PostToolUse:Bash |
| **Claim审计** | `posttool-claim-audit.py` | PostToolUse |
| **安全过滤** | `posttool-sensitive-filter.py` | PostToolUse |
| **输出校验** | `posttool-output-schema.py` | PostToolUse:Bash/Edit/Write |
| **夜航模式** | `carroros-night-deny.py` | PreToolUse |
| **Error DNA** | `error-dna.py`, `error-dna-auto-fix.py` | PostToolUse |
| **token 系统** | `token_writer.py`, `turn-counter.py` | PostToolUse / UserPromptSubmit |
| **会话管理** | `session-start.py`, `session-resume.py` | SessionStart / PreCompact |
| **生命周期** | `precompact-lifecycle.py` | PreCompact |
| **飞轮** | `stop-flywheel.py` | PreCompact |
| **阅读追踪** | `read-tracker.py` | PostToolUse:Read |

## 注册方式

在 `.claude/settings.json` 中按 hook 类型注册：

```json
{
  "hooks": {
    "PreToolUse": ["pretool-gate.py"],
    "PostToolUse:Bash": ["posttool-bash-audit.py"]
  }
}
```

Hook 通过 `hook-launcher.py` 统一调度。每个 hook 启动时自动检查 `harness.yaml` 中的开关。
