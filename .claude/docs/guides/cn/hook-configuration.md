# Hook 配置指南

> 基于源码 `.claude/hooks/`（60 个脚本）+ `.claude/harness.yaml` + `.claude/settings.json` 实测提取。

## 什么是 Hook？

Hook 是 Carror OS 的门禁机制。每个 hook 在特定时机（工具调用前/后、会话停止等）触发一段脚本，对 AI 的行为进行检查或约束。

**类比**：Git hooks（pre-commit / pre-push），但针对 AI 工具调用。

## Hook 生命周期

```
事件发生（如 AI 准备 Edit 文件）
  → settings.json 匹配工具名 + 事件类型
    → 脚本执行
      → exit 0（放行）或 echo '{"continue": true}' + exit 2（阻断+消息）
```

## 配置文件位置

| 文件 | 作用 |
|------|------|
| `.claude/harness.yaml` | 开关控制（`hooks_enabled`）+ 阈值配置 |
| `.claude/settings.json` | 事件注册（`hooks` 数组，定义事件名/匹配器/超时） |
| `.claude/hooks/*.sh` | 实际脚本逻辑 |

**三方必须一致**：磁盘脚本存在 ↔ `settings.json` 注册 ↔ `harness.yaml` 开关 `true`。任一缺失会导致 hook 不生效。

验证方法：直接检查 `harness.yaml` 的 `hooks_enabled` 段，确认目标 hook 为 `true`。

## hooks_enabled 完整参考

`harness.yaml` 中 `hooks_enabled` 的每个开关（v6.3.8）：

| 开关 | 默认 | 作用 |
|------|------|------|
| `completion_gate` | true | AI 标记任务完成前要求证据文件 |
| `context_guard` | true | 上下文超 80% 时阻断写操作 |
| `subagent_guard` | true | 约束子 agent 用量，防账单雪崩 |
| `pretool_edit_scope` | true | 编辑范围检查 + 自动加入关联文件 |
| `edit_guard` | true | 编辑前强制先 Read 源文件 |
| `lsp_suggest` | true | Grep 搜索时建议改用 LSP 工具 |
| `posttool_bash_audit` | true | Bash 执行后审计权限上下文 |
| `posttool_write_cite` | true | 写入教训文件时验证格式 |
| `permission_gate` | true | 危险命令前检查权限申请格式 |
| `auto_snapshot` | true | 会话结束保存状态快照 |
| `posttool_edit_quality` | true | 编辑后自查风格/文档同步 |
| `inject_project_knowledge` | true | 注入核心知识到 AI 上下文 |
| `plan_gate` | true | 编辑前检查是否跳过规划 |
| `turn_counter` | true | 轮次统计 + 模糊指令检测 |
| `read_tracker` | true | 记录已读文件供 edit-guard 检查 |
| `error_dna` | true | 错误 DNA 捕获 + 跨会话记忆 |
| `knowledge_condenser` | true | 高频教训自动升华建议 |
| `posttool_claim_audit` | true | 铁律 #1 强制执行 — 禁止编造代码事实 |
| `intent_tracker` | true | 跟踪编辑次数 + 检测内容回退 |
| `posttool_handoff_writer` | true | 每次 Task 完成写交接笔记 |
| `posttool_output_format` | true | 检查输出格式方向感 |
| `pretool_sensitive_edit` | true | 治理文件编辑 CAPTCHA 确认 |
| `skill_flywheel` | true | Skill 使用频率追踪 |
| `privacy_gate` | true | .env/密钥/Token 绝对禁阅 |
| `anti_pattern_detect` | true | 反模式检测（软完成语等） |
| `compact_detect` | true | /compact 后知识恢复注入 |
| `fuzzy_block` | true | 模糊指令（"优化一下"等）硬阻断 |
| `pre_completion_gate` | true | 完成声明前置审判 |
| `pre_ask_guard` | true | 拦截可自主决策的提问，降低心智负担 |
| `meta_oracle_trigger` | true | Meta-Oracle 最高审判触发 |
| `posttool_completion_audit` | true | completion-gate 第二道防御 |
| `posttool_subagent_audit` | true | 子 agent token 消耗事后对账 |
| `posttool_write_lock` | true | OMA 写锁冲突检测 |
| `pretool_write_lock` | true | OMA 写锁预检 |
| `retry_budget_check` | true | 修复上限 3 轮执法 |
| `stop_drain` | true | 会话停止时兜底扫 transcript |
| `token_writer` | true | 上下文使用率实时追踪 |
| `skill_usage_tracker` | true | Skill/hook 使用频率统计 |
| `ecosystem_probe` | true | 检测运行平台与 OMO 安装状态 |
| `issue_triage` | true | Issue 分类自动化 |

> ⚠️ 以下 hook 已在 v6.3.8 移除：`posttool_read_cite`、`rule_anchor`（锚定逻辑已融入 `pretool_edit_scope`）、`proactive_handoff`、`build_validator`。

## 常见配置场景

### 关闭某个 gate（如 completion-gate 太严格）

编辑 `.claude/harness.yaml`，在 `hooks_enabled` 中：
```yaml
hooks_enabled:
  completion_gate: false
```

### 调整 context-guard 触发阈值

在 `harness.yaml` 中：
```yaml
context_guard:
  warn_threshold: 50   # 默认 50%
  danger_threshold: 80  # 默认 80%，达到即阻断写操作
```

### 添加自定义危险命令拦截

在 `harness.yaml` 的 `bash_audit.dangerous_patterns` 中添加：
```yaml
bash_audit:
  dangerous_patterns: git commit git push ... your_custom_pattern
```

### 修改 permission-gate 拦截范围

```yaml
permission_gate:
  gh_write_regex: 'gh\s+(release|pr|issue|repo|secret)'
```

## 被 Gate 阻断后怎么办？

### completion-gate 阻断

```
⛔ COMPLETION BLOCKED — 没有验证证据
```

**操作**：运行验证命令，将输出写入证据文件。AI 会自动处理。

### permission-gate 阻断

```
🚫 PERMISSION REQUIRED — 危险命令需批准
```

**操作**：在输入框中输入 `! <命令>` 前缀执行，或明确表达批准。

### context-guard 阻断

```
⚠️ CONTEXT THRESHOLD — 上下文使用率达 80%+
```

**操作**：使用 `/compact` 压缩上下文，或手动关闭不必要的对话历史。

### pre-ask-guard 阻断

```
🤔 ASK BLOCKED — 你已经有答案了
```

**操作**：AI 被要求自主决策而不是问你。这是正常的——说明文档里已有明确答案。

### sensitive-edit 阻断（CAPTCHA）

```
🔒 SENSITIVE FILE EDIT — 治理文件需确认
```

**操作**：按提示在输入框中输入确认命令。这是防止 AI 擅自修改治理文件的保护机制。

---

## Hook 事件类型

| 事件 | 触发时机 | 可用的工具名匹配 |
|------|----------|-----------------|
| `PreToolUse` | 工具调用前 | 所有工具名（Bash/Edit/Write/Read/Grep/Task 等） |
| `PostToolUse` | 工具成功调用后 | 同上 |
| `PostToolUseFailure` | 工具调用失败后 | 同上 |
| `Stop` | 会话停止时 | — |
| `SessionStart` | 新会话开始时 | — |
| `PreCompact` | /compact 执行前 | — |
| `Notification` | 系统通知 | — |

---

## 排查

```bash
# 检查三方一致性 — 对照 harness.yaml + settings.json + 磁盘 hooks/
grep -A200 'hooks_enabled:' .claude/harness.yaml | head -50

# 查看最近 hook 拦截记录
ls -lt .omc/state/ | head -10

# 查看 error-dna 历史错误
cat .omc/state/error-dna.jsonl 2>/dev/null | tail -20
```


## Gate 阻断协议 (v6.3.8)

| 协议 | 机制 | 适用 |
|------|------|------|
| continue:false | Python硬阻断,停止工具链 | permission-gate,privacy-gate |
| exit2+continue:true | Bash阻断工具,不打断链 | oracle-gate,blast-radius,terminal-safety |


## posttool-checkpoint.sh

TaskUpdate(completed) + Stop 双事件。输出结构化收尾摘要到 stderr(人类可见) + additionalContext(AI上下文)。


## v6.3.x 新增 Hook

| Hook | 事件 | 功能 | 版本 |
|------|------|------|------|
| pretool-blast-radius.sh | PreToolUse:Bash | git checkout . / git reset --hard 硬阻断 (DG-100) | v6.3.1 |
| pretool-purify-gate.sh | PreToolUse:Edit\|Write | lx-purify runtime hook, 哲学纯度提醒 | v6.3.5 |
| pretool-node-reference.sh | PreToolUse:Agent | nodes/ 编排节点 bridge, Agent spawn时注入节点列表 | v6.3.6 |
| posttool-template-check.sh | PostToolUse:Write | task_sys/ 模板格式校验 | v6.3.6 |
| posttool-checkpoint.sh | PostToolUse:TaskUpdate + Stop | 工作流结束统一checkpoint | v6.3.2 |

## v6.3.x 移除/禁用

| Hook | 状态 | 原因 | 版本 |
|------|------|------|------|
| build-validator.sh | 文件已删除, 注册已清理 | ROI为零, 被 blast-radius 取代 (DG-100) | v6.2.38→v6.3.7 |
| pretool-sensitive-edit.sh | 禁用 (harness.yaml false) | 门禁体系原子化重构, 功能分散到 oracle-gate + sensitive-file-guard | v6.3.1 |
| permission-gate.sh | 禁用 (harness.yaml false) | 原子化重构, continue:false 仅用于安全暂停 | v6.3.1 |


## 已废弃能力

| 能力 | 废弃时间 | 替代 |
|------|---------|------|
| AGENTS.md 直接AI上下文 | v6.3.2 | context-cache.md 单源三层注入 |
| CLAUDE.md 完整配置 | v6.3.2 | 降级为 @AGENTS.md 桥接 |
| pretool-rules-inject AGENTS.md extract_section | v6.3.2 | context-cache.md Python section parser |
