# Hook路由注册表

> 接入表: Event:Matcher→Hooks — 与 AGENTS.md 路由索引格式一致,权责不重复
> 注: 所有 hook 注册在 `settings.hooks.*` 下，settings.json 顶层无独立 hook 注册段。

──────────────────────
SessionStart
──────────────────────
*→context-compressor|knowledge-condenser|error-dna-auto-fix|meta-oracle-review|inject-project-knowledge|sessionstart-gate-check|flywheel-report|token_writer|pretool-cruise-check|ecosystem-probe|session-resume|lsp-gate|oracle-gate|cross-platform-smoke-test|session-inject

──────────────────────
PreToolUse（操作前阻断）
──────────────────────
Edit|Write→pretool-oracle-gate(py+sh)|edit-guard|pre-edit-lsp-check|pretool-purify-gate|pretool-skill-version-guard|context-guard(W50/D80)|pretool-write-lock|pretool-sensitive-file-guard|pretool-b1-detect|pretool-edit-scope|pretool-scope-gate|pretool-workflow-gate|pretool-git-gate
Edit|Write|Bash→pretool-sensitive-edit|pretool-plan-gate
Bash→permission-gate|pretool-retry-check|pretool-blast-radius|pretool-terminal-safety(max:2000)
Bash|Read|Grep→privacy-gate(.env/Token拦截)
Grep→lsp-suggest
Task→subagent-guard
TaskUpdate→pre-completion-gate
AskUserQuestion→pre-ask-guard
Agent→pretool-node-reference
Skill→pretool-skill-body-enforce
.*→fuzzy-block

──────────────────────
PostToolUse（操作后审计）
──────────────────────
Edit|Write→auto-snapshot|posttool-edit-quality|posttool-write-lock|posttool-claim-audit|intent-tracker|posttool-write-cite
TaskUpdate→completion-gate(软语)|posttool-handoff-writer|posttool-completion-audit|posttool-checkpoint
TaskUpdate|Edit|Write→posttool-format-gate|posttool-anti-pattern-detect|posttool-template-check|phase-state-tracker
Read→read-tracker|posttool-read-cite
Bash→posttool-bash-audit|posttool-output-compressor|error-dna|build-validator
Skill→skill-usage-tracker|posttool-skill-compliance
Task|Agent→posttool-subagent-audit
.*→token_writer|meta-oracle-trigger(py+sh)|agentic-ui|permission-frequency-tracker

──────────────────────
PostToolUseFailure
──────────────────────
Bash→error-dna|posttool-bash-audit|build-validator

──────────────────────
UserPromptSubmit
──────────────────────
*→pretool-user-correction|turn-counter|pretool-rules-inject
.*→pretool-approve-detect|thinking-gate

──────────────────────
Stop
──────────────────────
*→auto-snapshot|skill-flywheel|stop-drain|posttool-checkpoint
