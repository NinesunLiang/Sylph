# Hook 配置指南

> 基于源码 `.claude/hooks/`（37 个脚本）+ `.claude/harness.yaml` + `.claude/settings.json` 实测提取。

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

验证命令：
```bash
bash .claude/scripts/audit-hooks.sh
```

## hooks_enabled 完整参考

`harness.yaml` 中 `hooks_enabled` 的每个开关：

| 开关 | 默认 | 作用 |
|------|------|------|
| `completion_gate` | true | AI 标记任务完成前要求证据文件 |
| `context_guard` | true | 上下文超 90% 时阻断写操作 |
| `subagent_guard` | true | 约束子 agent 用量，防账单雪崩 |
| `pretool_edit_scope` | true | 编辑范围检查 + 自动加入关联文件 |
| `edit_guard` | true | 编辑前强制先 Read 源文件 |
| `lsp_suggest` | true | Grep 搜索时建议改用 LSP 工具 |
| `posttool_read_cite` | false | 读取后提示引用规范 |
| `posttool_bash_audit` | true | Bash 执行后审计权限上下文 |
| `posttool_write_cite` | true | 写入教训文件时验证格式 |
| `permission_gate` | true | 危险命令前检查权限申请格式 |
| `auto_snapshot` | true | 会话结束保存状态快照 |
| `posttool_edit_quality` | true | 编辑后自查风格/文档同步 |
| `inject_project_knowledge` | true | 注入核心知识到 AI 上下文 |
| `plan_gate` | false | 编辑前检查是否跳过规划 |
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
| `build_validator` | false | 已废弃（ROI 为零） |
| `user_correction_detector` | true | 检测用户纠正信号，强制记录 |
| `rule_anchor` | true | 高轮次时注入锚定规则 |
| `proactive_handoff` | false | 主动会话交接提示 |
| `ecosystem_probe` | true | 检测运行平台与 OMO 安装状态 |

## 常见配置场景

### 关闭某个 gate（如 completion-gate 太严格）

编辑 `.claude/harness.yaml`，在 `hooks_enabled` 中：
```yaml
hooks_enabled:
  completion_gate: false  # 改为 false
```

### 调整 context-guard 触发阈值

在 `harness.yaml` 中：
```yaml
context_guard:
  max_percent: 85  # 默认 90，降低到 85 更保守
```

### 添加自定义危险命令拦截

在 `harness.yaml` 的 `bash_audit.dangerous_patterns` 中添加：
```yaml
bash_audit:
  dangerous_patterns: "git commit git push ... your_custom_pattern"
```

### 修改 permission-gate 拦截范围

```yaml
permission_gate:
  gh_write_regex: 'gh\s+(release|pr|issue|repo|secret)'  # 拦截 gh 写操作
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
⚠️ CONTEXT THRESHOLD — 上下文使用率达 90%+
```

**操作**：使用 `/compact` 压缩上下文，或手动关闭不必要的对话历史。

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
# 检查三方一致性
bash .claude/scripts/audit-hooks.sh

# 运行全量 smoke 测试
bash .claude/scripts/harness-smoke-test.sh

# 运行 hook 生产验证
bash .claude/scripts/hook-production-verify.sh
```
