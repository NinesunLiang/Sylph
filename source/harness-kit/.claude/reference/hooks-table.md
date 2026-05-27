## Hooks 速查（共 50 个）
| Hook | 触发 | 作用|
|------|------|------|
|`agentic-ui` | PostToolUse | agentic-ui.sh — 共享库（非 Hook） — Agentic UI 标准化输出函数|
|`auto-snapshot` | PostToolUse / Stop | auto-snapshot.sh — Stop / PostToolUse:Edit|Write — 会话结束时自动保存状态快照（分支/轮次/未提交文件）|
|`build-validator` | PostToolUse / PostToolUseFailure | build-validator.sh — PostToolUse:Bash / PostToolUseFailure:Bash — 构建失败自动记录错误日志并给|
|`compact-detect` | UserPromptSubmit | compact-detect.sh — UserPromptSubmit — /compact 后知识恢复（压缩版）|
|`completion-gate` | PostToolUse | completion-gate.sh — PostToolUse:TaskUpdate — 强制 TaskUpdate 前提供结构化证据文件|
|`context-compressor` | SessionStart | context-compressor.sh — SessionStart — 移花接木：源文件不动，运行时拼接压缩缓存|
|`context-guard` | PreToolUse | context-guard.sh — PreToolUse:Edit|Write — 基于真实 token 百分比阻断写操作，防止上下文溢出|
|`ecosystem-probe` | SessionStart | ecosystem-probe.sh — SessionStart — 生态探针|
|`edit-guard` | PreToolUse | edit-guard.sh — PreToolUse:Edit — 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁|
|`error-dna` | PostToolUse / PostToolUseFailure | error-dna.sh — PostToolUse:Bash / PostToolUseFailure:Bash — 轻量错误捕获（Oracle 瘦身后 v2|
|`flywheel-report` | SessionStart | flywheel-report.sh — SessionStart — 读取飞轮日志，生成 30 天频率摘要注入会话|
|`fuzzy-block` | PreToolUse | fuzzy-block.sh — PreToolUse — 模糊指令硬阻断（C1 指令清晰度门禁）|
|`inject-project-knowledge` | SessionStart | inject-project-knowledge.sh — SessionStart — 注入 .claude/ 核心知识到 AI context|
|`intent-tracker` | PostToolUse | intent-tracker.sh — PostToolUse:Edit|Write — 跟踪文件级编辑统计 + revert 检测|
|`lsp-suggest` | PreToolUse | lsp-suggest.sh — PreToolUse:Grep — 检测 Grep 搜索导出符号时建议改用 LSP 工具|
|`meta-oracle-trigger.py` | PostToolUse | ── Platform detection ──────────────────────────────────────────────|
|`meta-oracle-trigger` | PostToolUse | meta-oracle-trigger.sh — PostToolUse:.* — Meta-Oracle 最后守门员自动触发（G1-G4）|
|`posttool-anti-pattern-detect` | PostToolUse | posttool-anti-pattern-detect.sh — PostToolUse:TaskUpdate|Edit|Write — 反模式自动检测|
|`posttool-bash-audit` | PostToolUse / PostToolUseFailure | posttool-bash-audit.sh — PostToolUse:Bash / PostToolUseFailure:Bash — Bash 执行后审计|
|`posttool-checkpoint` | PostToolUse / Stop | posttool-checkpoint.sh — PostToolUse:TaskUpdate + Stop — 工作流闭环：所有工作流结束时输出结构化 che|
|`posttool-claim-audit` | PostToolUse | posttool-claim-audit.sh — PostToolUse:Edit|Write — 铁律 #1「禁止编造」强制校验|
|`posttool-completion-audit` | PostToolUse | posttool-completion-audit.sh — PostToolUse — 独立验证 evidence 质量（E3/E7 防御纵深）|
|`posttool-edit-quality` | PostToolUse | posttool-edit-quality.sh — PostToolUse:Edit|Write — 编辑后自查代码风格、文档同步、方案复用检测|
|`posttool-format-gate` | PostToolUse | posttool-format-gate.sh — PostToolUse:TaskUpdate — 以人为本输出格式门禁（哲学 #5 物化）|
|`posttool-handoff-writer` | PostToolUse | posttool-handoff-writer.sh — PostToolUse:TaskUpdate — 每次 Task 完成后写 handoff|
|`posttool-subagent-audit` | PostToolUse | posttool-subagent-audit.sh — PostToolUse:Task — 子 agent 执行后审计 content 用量，超限告警|
|`posttool-write-cite` | PostToolUse | posttool-write-cite.sh — PostToolUse:Write|Edit — 检测写入 claude-next.md 时验证教训格式|
|`posttool-write-lock` | PostToolUse | posttool-write-lock.sh — PostToolUse:Edit|Write — 写操作后释放 OMA 并发锁|
|`pre-ask-guard` | PreToolUse | pre-ask-guard.sh — PreToolUse:AskUserQuestion — 问人前强制过决策链四层评估|
|`pre-completion-gate` | PreToolUse | pre-completion-gate.sh — PreToolUse:TaskUpdate — 前置完成门禁，阻止无证据的 completed 调用|
|`pre-edit-lsp-check` | PreToolUse | pre-edit-lsp-check.sh — PreToolUse:Edit — 编辑前强制诊断检查 (v2)|
|`pretool-approve-detect` | UserPromptSubmit | pretool-approve-detect.sh — PreToolUse:Bash — 在 permission-gate 之前运行|
|`pretool-blast-radius` | PreToolUse | pretool-blast-radius.sh — PreToolUse:Bash — 全局破坏性命令拦截 (DG-101)|
|`pretool-edit-scope` | PreToolUse | pretool-edit-scope.sh — PreToolUse:Edit|Write — 范围管理 + 规则锚定（合并 pretool-rule-anch|
|`pretool-oracle-gate.py` | PreToolUse | Platform routing: on macOS/Linux the bash .sh version handles execution|
|`pretool-oracle-gate` | PreToolUse | pretool-oracle-gate.sh — PreToolUse:Edit|Write — Oracle 审查前置门禁 (DG-115)|
|`pretool-retry-check` | PreToolUse | pretool-retry-check.sh — PreToolUse — 阻断超过重试上限的 Bash 命令|
|`pretool-rules-inject` | UserPromptSubmit | pretool-rules-inject.sh — UserPromptSubmit — 3级脱水分层注入|
|`pretool-sensitive-file-guard` | PreToolUse | pretool-sensitive-file-guard.sh — PreToolUse:Edit|Write — 保护门禁文件不被 AI 直接写入|
|`pretool-skill-version-guard` | PreToolUse | pretool-skill-version-guard.sh — PreToolUse:Edit|Write — SKILL.md 版本格式 + 引用有效性门禁|
|`pretool-terminal-safety` | PreToolUse | pretool-terminal-safety.sh — PreToolUse:Bash — 终端命令格式校验|
|`pretool-user-correction` | UserPromptSubmit | pretool-user-correction.sh — UserPromptSubmit — 检测用户纠正信号，强制记录到 claude-next.md|
|`pretool-write-lock` | PreToolUse | pretool-write-lock.sh — PreToolUse:Edit|Write — 写操作前获取 OMA 并发锁，防止多终端冲突|
|`privacy-gate` | PreToolUse | privacy-gate.sh — PreToolUse:Bash|Read|Grep — 防止隐私数据泄露（DLP 门禁）|
|`read-tracker` | PostToolUse | read-tracker.sh — PostToolUse:Read — 记录已读文件路径供 edit-guard 检查 Read-before-Edit|
|`session-resume` | SessionStart | session-resume.sh — SessionStart — 跨会话恢复: 注入进行中的 goal/ghost 任务上下文|
|`skill-usage-tracker` | PostToolUse | skill-usage-tracker.sh — UserPromptSubmit|PostToolUse:Skill — 记录 skill 调用频率|
|`stop-drain` | Stop | stop-drain.sh — Stop — Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）|
|`subagent-guard` | PreToolUse | subagent-guard.sh — PreToolUse:Task — 约束子 agent 用量，防账单雪崩（软约束+事后对账）|
|`turn-counter` | UserPromptSubmit | turn-counter.sh — UserPromptSubmit — 统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测|

### 已注册但默认禁用的脚本（共 5 个）

以下脚本已注册到 settings.json，但在 harness.yaml 中默认关闭，按需启用：

| 脚本 | 事件 | 说明 |
|------|------|------|
| knowledge-condenser | (未注册) | knowledge-condenser.sh — Stop — 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议 |
| permission-gate | PreToolUse | permission-gate.sh — PreToolUse:Bash — 执行危险命令前检查权限申请格式 |
| pretool-plan-gate | (未注册) | pretool-plan-gate.sh — PreToolUse:Edit|Write|Bash — Plan-before-Execute 门禁 |
| pretool-sensitive-edit | PreToolUse | pretool-sensitive-edit.sh — PreToolUse:Edit|Write|Bash — 治理文件编辑验证码门禁（哲学 #6 物化） |
| skill-flywheel | (未注册) | skill-flywheel.sh — Stop — 停止时更新 skill 使用频率，驱动飞轮优化（含时间戳追踪） |
