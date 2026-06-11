# Hook 路由注册表（用户版）

> 精简版 — 仅注册核心治理 hook，完整代码库保留在 hooks/ 中以备扩展

## SessionStart
- `session-resume.py` — compact 后恢复会话状态

## PreToolUse

**Edit|Write** → 编辑保护
- `edit-guard.py` — 编辑合法性校验
- `pretool-edit-scope.py` — 一次只改一个范围

**Bash** → 安全保护
- `permission-gate.py` — Bash 执行安全门禁
- `pretool-retry-check.py` — 3 次修复上限

**Bash|Read|Grep** → 隐私
- `privacy-gate.py` — 防止读取 .env/密钥

**AskUserQuestion** → 事前检查
- `pre-ask-guard.py` — 问人前先走哲学

**TaskUpdate** → 完成预检
- `pre-completion-gate.py` — 完成前检查

## PostToolUse

**TaskUpdate** → 诚实门禁
- `completion-gate.py` — 软完成语拦截

**Bash** → 错误追踪
- `error-dna.py` — 错误 DNA 记录
- `posttool-error-dna-shard.py` — 错误碎片分析

## UserPromptSubmit
- `pretool-approve-detect.py` — 对话内 /approve
- `thinking-gate.py` — Thinking 内容过滤
- `turn-counter.py` — 10 轮铁律锚定注入
- `pretool-rules-inject.py` — 规则注入

## PreCompact
- `pretool-compact-writer.py` — compact 前保存会话状态
