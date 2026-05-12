# OpenCode Hooks 迁移方案：基于 OMO 实现 Claude Code 同级 Hook 能力

> 日期：2026-05-13 | 状态：草案 | 目标：Carror OS 在 OpenCode 上获得与 Claude Code 同级的 Hooks 治理能力

---

## 1. 核心结论

**oh-my-openagent（OMO）已有 Claude Code hooks 兼容层**，位于 `src/hooks/claude-code-hooks/`，能将 Claude Code 的 `.claude/settings.json` hook 配置映射到 OpenCode 的 Plugin hook 点。

**现有兼容层能力矩阵：**

| Claude Code 事件 | OMO 兼容层 | 状态 |
|---|---|---|
| PreToolUse | `tool.execute.before` | ✅ 已实现 |
| PostToolUse | `tool.execute.after` | ✅ 已实现 |
| UserPromptSubmit | `chat.message` | ✅ 已实现 |
| Stop | `event.session.idle` | ✅ 已实现（含 `stopHookActive` 复活机制） |
| PreCompact | `experimental.session.compacting` | ✅ 已实现 |
| SessionStart | ❌ 无直接映射 | ⚠️ 需适配 |
| PostToolUseFailure | ❌ OpenCode 无独立事件 | ⚠️ 需适配 |

---

## 2. 事件映射详解

### 2.1 PreToolUse → `tool.execute.before`

OMO 实现（`pre-tool-use.ts`）：
- 读取 `.claude/settings.json` 的 `hooks.PreToolUse` 配置
- 按 `matcher` 匹配当前工具名
- 调用 `dispatchHook()` → shell 子进程执行 hook 脚本
- hook exit 2 → `throw new Error()` 阻断工具调用
- 支持 `modifiedInput` 修改工具参数

**Carror OS 在此事件注册了 10 个 matcher/20 个 hook 调用**，全部可直接工作。

**需要确认的差异：**
- OpenCode 的 `tool.execute.before` 不传递 `permission_mode` 字段。如果 Carror OS 的 hook 脚本依赖此字段（如 permission-gate.sh），需做兼容处理。
- `toolUseId`/`callID` 映射：OMO 传入 `input.callID` 作为 `tool_use_id`，字段名与 Claude Code 不同。

### 2.2 PostToolUse → `tool.execute.after`

OMO 实现（`post-tool-use.ts`）：
- 读取 `hooks.PostToolUse` 配置，按 matcher 匹配
- 调用 `dispatchHook()` 执行 shell 脚本
- 从 `output` 中提取 `tool_output` 等字段写入 stdin

**关键差异：**

OpenCode 的 `tool.execute.after` 在工具**无论成功或失败**都会触发。而 Claude Code 分为 `PostToolUse`（成功）和 `PostToolUseFailure`（失败）。

这意味着 Carror OS 注册的 `PostToolUseFailure` 下的 3 个 hook（error-dna.sh、posttool-bash-audit.sh、build-validator.sh）在 OpenCode 上会被 `tool.execute.after` 一并覆盖处理。无需额外的事件映射。

### 2.3 UserPromptSubmit → `chat.message`

OMO 实现（`user-prompt-submit.ts`）：
- 读取 `hooks.UserPromptSubmit` 配置
- 解析 `prompt` 字段，注入 hook stdin
- 支持 `block: true` 阻断消息

**注意：** OMO 跳过了 `parentSessionId`（子会话）的 UserPromptSubmit，仅处理主会话。这与 Claude Code 稍有行为差异。

### 2.4 Stop → `event.session.idle`

OMO 实现（`stop.ts`）：
- `event.type === "session.idle"` 时触发
- 支持 `stopHookActive` 状态机制：Stop hook 可以重新激活会话
- 支持 `injectPrompt` 返回值，注入后续消息

**Carror OS 在 Stop 事件注册了 5 个 hook：**
- auto-snapshot.sh（会话状态快照）
- stop-drain.sh（transcript 兜底扫描）
- skill-flywheel.sh（飞轮日志刷写）
- error-dna-auto-fix.sh（错误自动修复）
- knowledge-condenser.sh（知识压缩）

全部可直接工作。`stopHookActive` 机制可确保处理不中断。

### 2.5 PreCompact → `experimental.session.compacting`

OMO 实现（`pre-compact.ts`）：
- 映射到 OpenCode 的 `experimental.session.compacting` 事件
- 读取 `hooks.PreCompact` 配置

**Carror OS 当前未注册 PreCompact hook。** compact-detect.sh 注册在 UserPromptSubmit 下。如果需要压缩前 hook，可直接添加。

### 2.6 SessionStart → 无直接映射（需适配）

**问题：** OpenCode 的 Plugin API 没有 `session:start` 事件。OMO 的 `chat.message` handler 首次触发时可作为 SessionStart 的替代。

**Carror OS 在 SessionStart 注册了 3 个 hook：**
- inject-project-knowledge.sh（项目知识注入）
- flywheel-report.sh（飞轮报告）
- token_writer.sh --reset（Token 计数器重置）

**适配方案：**
- 在 OMO 的 `createChatMessageHandler` 中检测是否为首条消息（通过 session hook state 判断）
- 首条消息时额外执行 SessionStart 的 hook 脚本
- 或者：这些脚本直接注册到 `chat.message` matcher，在首次 UserPromptSubmit 时触发

### 2.7 PostToolUseFailure → OpenCode 无独立事件

**问题：** Claude Code 有独立的 `PostToolUseFailure` 事件（仅失败时触发），但 OpenCode 的 `tool.execute.after` 对成功/失败都触发。

**实际上这更简单：**
- `tool.execute.after` 参数中包含错误信息（`output.error` 或类似字段）
- 检测到失败时，额外调用 Carror OS 注册在 `PostToolUseFailure` 下的 hook

**Carror OS 在 PostToolUseFailure 注册了 3 个 hook（都在 Bash matcher 下）：**
- error-dna.sh
- posttool-bash-audit.sh
- build-validator.sh

**适配方案：**
- 在 `createToolExecuteAfterHandler` 中检测工具执行结果
- 如果失败，额外调用 PostToolUseFailure 对应的 hook
- 这些 hook 本身已是 schema 双轨兼容（同时吃 success 和 failure 两种 stdin 格式）

---

## 3. 差距分析

### 3.1 stdin Schema 差异

Carror OS 的 hook 脚本从 stdin 读取 JSON 输入。Claude Code 传递的字段与 OpenCode 的字段存在差异：

| Claude Code 字段 | OpenCode (通过 OMO) | 影响 |
|---|---|---|
| `session_id` | ✅ `sessionID` | 少数字段名不同，影响小 |
| `cwd` | ✅ `ctx.directory` | 已映射 |
| `tool_name` | ✅ `input.tool` | 已映射 |
| `tool_input` | ✅ `output.args` | 已映射 |
| `tool_use_id` | ✅ `input.callID` | 字段名不同 |
| `permission_mode` | ❌ 无 | 部分 hook（permission-gate）可能依赖 |
| `transcript_path` | ⚠️ 需确认 | stop-drain.sh 依赖转录路径 |
| `hook_source` | `opencode-plugin`（固定） | 与 `claude-code-hook` 不同，部分检测脚本可能需要适配 |

### 3.2 阻断机制差异

| 行为 | Claude Code | OpenCode (通过 OMO) |
|---|---|---|
| hook exit 2 阻断工具 | ✅ 原生支持 | ✅ `throw new Error()` 模拟 |
| additionalContext 输出 | ✅ 原生注入到 AI 上下文 | ⚠️ 需通过 `ctx.client.tui.showToast()` 通知用户 |
| 修改 tool_input | ✅ 返回 `modifiedInput` | ✅ `Object.assign(output.args, modifiedInput)` |
| 超时机制 | `timeout` 字段 | ✅ OMO 支持 timeout 参数 |

### 3.3 Stop Hook 复活机制

OMO 的 Stop hook 实现比 Claude Code 更强大：
- `stopHookActive` 状态追踪——Stop hook 可以重新激活会话
- 支持 `injectPrompt` 返回值，注入后续消息
- Carror OS 的 `auto-snapshot.sh` 等 5 个 Stop hook 可直接兼容

### 3.4 Exit Code 语义

Carror OS 的 hook 脚本用 `exit 2` 表示阻断。OMO 的 `executePreToolUseHooks` 会检查 `result.decision === "deny"` 然后 `throw new Error()`。需要确认 OMO 对 hook 脚本 exit code 的翻译逻辑是否与 Claude Code 一致。

---

## 4. 实施方案

### Phase 1：兼容层适配（2-3 天）

```
修改目标：OMO claude-code-hooks 兼容层
优先级：P0（核心）
```

#### 4.1 添加 SessionStart 支持

在 `session-event-handler.ts` 的 `session.idle` 处理前，增加首次会话启动检测机制：

```typescript
// 在 session-event-handler.ts 中
if (event.type === "session.created" || 检测首次 chat.message) {
  const sessionStartHooks = findMatchingHooks(config, "SessionStart")
  for (const hook of sessionStartHooks) {
    await dispatchHook(hook, sessionStartStdin, cwd)
  }
}
```

或者更简单：在 `createChatMessageHandler` 首次调用时执行 SessionStart hooks。

#### 4.2 添加 PostToolUseFailure 支持

在 `tool-execute-after-handler.ts` 中检测失败：

```typescript
// 检测工具执行失败
const isFailure = output?.error !== undefined || hasErrorExitCode(output)
if (isFailure) {
  const failureHooks = findMatchingHooks(config, "PostToolUseFailure", input.tool)
  for (const hook of failureHooks) {
    await dispatchHook(hook, failureStdin, cwd)
  }
}
```

#### 4.3 补充 stdin 缺失字段

在 OMO 的 claude-code-hooks 配置中增加 OpenCode 环境下的缺失字段补全：

```typescript
// pre-tool-use.ts 中的 stdinData 补充
const stdinData = {
  ...baseStdinData,
  permission_mode: "bypassPermissions",  // 固定值，OpenCode 无此字段
  hook_source: "opencode-plugin",
}
```

#### 4.4 确认 Exit Code 翻译

验证 OMO 的 `executeHookCommand` 是否将 shell exit 2 正确翻译为 `{ decision: "deny" }`。如果不一致，修改 `dispatch-hook.ts`：

```typescript
// 在 executeHookCommand 结果处理中
if (result.exitCode === 2) {
  return { decision: "deny", reason: result.stderr || "Hook blocked" }
}
```

### Phase 2：Carror OS 侧适配（1-2 天）

```
修改目标：Carror OS 的 hook 脚本
优先级：P1（基础兼容）
```

#### 2.1 检查 hook_source 依赖

搜索所有 Carror OS hook 脚本中是否检测 `hook_source` 字段：

```bash
grep -r "hook_source" .claude/hooks/*.sh
```

如果存在，需要添加 `opencode-plugin` 作为合法值。

#### 2.2 检查 permission_mode 依赖

搜索所有 hook 脚本中对 `permission_mode` 的引用：

```bash
grep -r "permission_mode" .claude/hooks/*.sh
```

如果存在，需要做 OpenCode 降级处理（默认放行或固定值）。

#### 2.3 检查 transcript_path 依赖

确认 `stop-drain.sh` 等脚本读取 `transcript_path` 的逻辑。OpenCode 的转录文件路径可能与 Claude Code 不同，需要适配。

#### 2.4 settings.json 兼容性验证

确认 OMO 的 config-loader 能正确解析 Carror OS 的 `.claude/settings.json` 格式。特别是 matcher 使用 `|` 分隔符（如 `"Edit|Write"`）的语法。

### Phase 3：测试与验证（1-2 天）

```
优先级：P0（不验证不上线）
```

#### 3.1 Hook 触发验证清单

逐项验证每个 Carror OS hook 在 OpenCode + OMO 上能否正确触发：

| Event | Matcher | Hook | 验证方式 |
|-------|---------|------|---------|
| PreToolUse | Edit | edit-guard.sh | 尝试编辑未 Read 的文件 → 预期阻断 |
| PreToolUse | Bash | permission-gate.sh | 执行 git push → 预期阻断 |
| PreToolUse | Bash\|Read\|Grep | privacy-gate.sh | Read .env → 预期阻断 |
| PreToolUse | Edit\|Write | context-guard.sh | 95% 上下文时写文件 → 预期阻断 |
| PostToolUse | TaskUpdate | completion-gate.sh | 更新任务 → 预期注入证据提醒 |
| Stop | - | auto-snapshot.sh | 结束会话 → 预期生成 snapshot |
| UserPromptSubmit | - | turn-counter.sh | 提交消息 → 预期注入轮次信息 |

#### 3.2 回归测试

在 OMO 的 claude-code-hooks 兼容层上运行 Carror OS 的 `harness-smoke-test.sh`：

```bash
bash .claude/scripts/harness-smoke-test.sh
```

#### 3.3 端到端验收

```bash
# 1. 隐私门禁
echo "API_KEY=sk-xxx" > .env && cat .env
→ 预期：被 privacy-gate 阻断

# 2. 权限门禁
git push origin main
→ 预期：被 permission-gate 阻断

# 3. Context 门禁
# 触发 95% 上下文后写文件
→ 预期：被 context-guard 阻断

# 4. Stop hook
# 结束会话后检查
ls .omc/state/session-snapshot.json
→ 预期：文件存在
```

### Phase 4：Ops 与监控

```
优先级：P2（上线前完成）
```

#### 4.1 Error DNA 在 OpenCode 上的兜底

OpenCode 的 `tool.execute.after` 覆盖所有工具结果。Carror OS 的 `error-dna.sh` 和 `build-validator.sh` 原本依赖 `PostToolUseFailure` 捕获失败，在 OpenCode 上需要确认 `tool.execute.after` 的参数中是否包含判断失败所需的信息。

**建议：** 如果 `tool.execute.after` 的参数不足以判断失败，改为通过 `transcript.jsonl` 绕行（类似 stop-drain.sh 的兜底方式）。

#### 4.2 三方一致性审计

修改 `audit-hooks.sh`，使其支持 OpenCode + OMO 环境的检测。新增 OpenCode 平台标识，检查 OMO 是否注册了所有必要的 hook 事件。

---

## 5. 风险与限制

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| OpenCode Plugin API 稳定性 | API 变更可能导致 hooks 失效 | 锁定 OMO 版本，上游变更时做回归 |
| stdin 字段缺失 | 部分 hook 行为异常 | Phase 2 补充缺失字段 |
| exit 2 阻断翻译 | 阻断逻辑失效 | Phase 1.4 验证 |
| SessionStart 无直接映射 | 项目知识不注入 | Phase 1.1 适配 |
| transcript_path 路径差异 | stop-drain 无法读取转录 | Phase 2.3 适配 |
| OMO 版本更新 | 兼容层代码变动 | PR review 关注 claude-code-hooks 目录变更 |

---

## 6. 不在此方案范围内

- 不修改 OMO 核心架构（只改 claude-code-hooks 兼容层）
- 不重构 Carror OS 的 hook 脚本逻辑（只做兼容性调整）
- 不涉及 OMO 的 70+ 个 TypeScript hooks 体系
- 不覆盖 OpenCode 上没有的独占功能（如 model routing）

---

## 7. 验收标准

```
[ ] Phase 1 全部完成 — OMO 兼容层适配
  [ ] SessionStart hook 在首次 chat.message 时触发
  [ ] PostToolUseFailure hook 在 tool.execute.after 检测到失败时触发
  [ ] stdin 缺失字段已补充
  [ ] exit 2 阻断逻辑验证通过

[ ] Phase 2 全部完成 — Carror OS 侧适配
  [ ] hook_source 兼容
  [ ] permission_mode 兼容
  [ ] transcript_path 兼容
  [ ] settings.json 格式兼容

[ ] Phase 3 全部完成 — 测试验证
  [ ] 全部 PreToolUse hook 触发正确
  [ ] 全部 PostToolUse hook 触发正确
  [ ] 全部 Stop hook 触发正确
  [ ] 全部 UserPromptSubmit hook 触发正确
  [ ] harness-smoke-test.sh 全绿通过
  [ ] 端到端 5 项验收通过

[ ] Phase 4 全部完成 — Ops
  [ ] Error DNA 在 OpenCode 上正常捕获
  [ ] audit-hooks.sh 支持 OpenCode + OMO
```
