# Hooks 速查表

> 参考文件 — 非自动注入，Run Read 手动查看


| Hook | 触发 | 作用|
|------|------|------|
|`auto-snapshot` | PostToolUse/Stop | auto-snapshot.sh — 会话快照+error-dna+handoff 持久化|
|`build-validator` | PostToolUse/PostToolUseFailure | build-validator.sh — 构建失败自动记录+修复建议|
|`compact-detect` | UserPromptSubmit | compact-detect.sh — /compact 检测+知识重新注入|
|`completion-gate` | PostToolUse:TaskUpdate | completion-gate.sh — 证据质量评分+软语检测+阻断虚假完成|
|`context-guard` | PreToolUse:Edit/W | context-guard.sh — 上下文阈值阻断(R29: Edit/W 防自锁)|
|`edit-guard` | PreToolUse:Edit | edit-guard.sh — Edit 钩子守卫|
|`error-dna` | PostToolUse/PostToolUseFailure:Bash | error-dna.sh — 结构化错误 DNA 捕获+symptom 分类|
|`error-dna-auto-fix` | Stop | error-dna-auto-fix.sh — 自动修复建议生成|
|`flywheel-report` | SessionStart | flywheel-report.sh — Flywheel P0 事件告警|
|`inject-project-knowledge` | SessionStart | 注入 .claude/ 核心知识+handoff next-step|
|`intent-tracker` | PostToolUse:Edit/W | intent-tracker.sh — 声明矛盾检测+additionalContext|
|`knowledge-condenser` | Stop | knowledge-condenser.sh — claude-next.md 压缩归档|
|`lsp-suggest` | PreToolUse:Grep | lsp-suggest.sh — LSP 使用建议|
|`permission-gate` | PreToolUse:Bash | permission-gate.sh — 危险命令拦截(git/rm/sudo/gh/scope)|
|`plan-gate` | PreToolUse:Edit/W | plan-gate.sh — Plan 前置检查 [DISABLED: harness.yaml 默认关闭]|
|`posttool-bash-audit` | PostToolUse/PostToolUseFailure:Bash | 权限上下文审计 — 只提醒不阻断|
|`posttool-edit-quality` | PostToolUse:Edit/W | 代码风格自查+文档同步提醒+方案复用检测|
|`posttool-handoff-writer` | PostToolUse:TaskUpdate | 每次 TaskUpdate completed 写 handoff|
|`posttool-read-cite` | PostToolUse:Read | Read 来源标注提醒 [默认禁用]|
|`posttool-subagent-audit` | PostToolUse:Task | 子 agent 字节数审计→flywheel P0|
|`posttool-write-cite` | PostToolUse:Write | Write 后自动记录引用|
|`posttool-write-lock` | PostToolUse:Edit/W | write-lock-release.sh — OMA 并发锁释放|
|`pretool-edit-scope` | PreToolUse:Edit/W | 范围冻结拦截+auto-scope 自动推导+耦合提醒|
|`pretool-rule-anchor` | PreToolUse:Edit/W | 规则锚定提醒|
|`pretool-user-correction` | UserPromptSubmit | 用户纠正信号检测+claude-next.md 自动记录|
|`pretool-write-lock` | PreToolUse:Edit/W | write-lock-gate.sh — OMA 并发锁前置拦截|
|`privacy-gate` | PreToolUse:Read/Grep/Bash | .env/私钥读取拦截|
|`proactive-handoff` | PostToolUse:Write/Edit | 主动交接建议 [默认禁用]|
|`read-tracker` | PostToolUse:Read | 文件读取追踪日志|
|`skill-flywheel` | Stop | skill-flywheel.sh — skill 调用统计|
|`stop-drain` | Stop | stop-drain.sh — 兜底重放|
|`subagent-guard` | PreToolUse:Task | 子 agent 用量软约束+事后对账|
|`token_writer` | PostToolUse/UserPromptSubmit/SessionStart/Stop | token 用量追踪(--increment/--reset)|
|`turn-counter` | UserPromptSubmit | 轮次统计+模糊指令检测+规范漂移锚定|

默认禁用的脚本（共 3 个，已在上表标注 `[DISABLED]`/`[默认禁用]`）:
- `plan-gate` — harness.yaml 默认关闭
- `posttool-read-cite` — harness.yaml 默认关闭
- `proactive-handoff` — Enhanced only，默认关闭

### 独立工具脚本（非 Hook）

| 脚本 | 说明 |
|------|------|
| feature-probe.sh | L1-L4 证据验证工具，手动调用 |


## 默认禁用的脚本（共 3 个）
- `plan-gate` — harness.yaml 默认关闭
- `posttool-read-cite` — harness.yaml 默认关闭
- `proactive-handoff` — Enhanced only，默认关闭

## 独立工具脚本（非 Hook）
| 脚本 | 说明 |
|------|------|
| feature-probe.sh | L1-L4 证据验证工具，手动调用 |
