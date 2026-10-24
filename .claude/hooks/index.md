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

## Base 注册 Hook（以 settings.json 为单一真源）

| 类别 | Hook 文件 | 触发点 |
|------|-----------|--------|
| **门禁路由** | `pretool-gate.py` → `pretool_gates/*.py` | PreToolUse（门列表单一真源 = 该文件 `_GATE_CORE`，L1=L2=14 道，2026-10-16 收敛） |
| **夜航模式** | `carroros-night-deny.py` | PreToolUse（与 pretool-gate 同次 spawn 串行） |
| **记分卡门禁** | `pretool-scorecard-gate.py` | PreToolUse:Edit/Write |
| **完成门禁** | `pre-completion-gate.py` | PreToolUse:TaskUpdate |
| **用户审批** | `pretool-user-approve.py` | UserPromptSubmit |
| **Claim审计** | `posttool-claim-audit.py` | PostToolUse:Edit/Write |
| **安全过滤** | `posttool-sensitive-filter.py` | PostToolUse |
| **完成审核** | `completion-gate.py` | PostToolUse:TaskUpdate |
| **会话启动** | `session-start.py` | SessionStart |
| **生命周期** | `precompact-lifecycle.py` | PreCompact |
| **飞轮停止** | `stop-flywheel.py` | PreCompact |
| **遥测清理** | `telemetry-ttl.py` | PreCompact |
| **用户命令门禁** | `stop-user-command-gate.py` | Stop（扫描最终回复，禁止多行/折行命令） |

> 已移除条目：`error-dna.py`（index48 随 error-dna 机制删除）、`read-tracker.py`（文件不存在，仅 harness.yaml 历史注释提及）。删除/退休 hook 的完整清单见 `references/archived/hooks-retired-20261023.md`。
