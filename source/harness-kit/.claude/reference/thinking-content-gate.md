# Thinking Content Gate
> Carror OS 第 7 号治理机制：在消息进入 agent context 之前过滤 thinking/reasoning 内容

## 1. 问题定义

### 1.1 症状

使用 DeepSeek R1 等带 thinking 输出的模型时，`reasoning_content`（OpenAI 协议）或 `type: "thinking"` block（Anthropic 协议）被：
- 存入 message history
- 在后续请求中重新发送给模型作为 context
- 大量消耗 token（DeepSeek R1 的 thinking 通常占 ~50% 的输出 token）
- 导致 context 膨胀，过期信息污染模型输入

### 1.2 根因

| 平台 | 协议 | 字段 | 当前行为 |
|------|------|------|---------|
| Claude Code | Anthropic Messages API | `type: "thinking"` content block | ✅ API 协议层隔离，不进 history |
| OpenCode | OpenAI Chat Completions | `reasoning_content` (streaming) / `reasoning` (non-stream) | ❌ 存入 SQLite history 并在 outbound 时重新发回 |
| Hermes (9998 proxy) | Anthropic→OpenAI 转换 | `reasoning_content` | ❌ 无过滤 |

### 1.3 目标

```
显示层（UI）     → ✅ 用户可以看到 thinking（保留使用体验）
存储层（history）→ ✅ 本地可存档（用于复盘/回放）
发送层（outbound）→ ❌ 发送给模型时剥离（不进入 context）
```

## 2. 架构分层

```
┌─────────────────────────────────────────┐
│          模型 (DeepSeek/Claude)           │
└──────────────┬──────────────────────────┘
               │ response stream
               ▼
┌──────────────────────────────┐
│  协议层 thinking 内容         │
│  reasoning_content / thinking│
└─────┬───────────────────┬───┘
      │                   │
      ▼                   ▼
┌────────────┐   ┌────────────────┐
│ UI 展示    │   │ thinking-gate   │
│ (给用户看) │   │ (剥离 thinking) │
└────────────┘   └───────┬────────┘
                         │ stripped content
                         ▼
                ┌──────────────────┐
                │ agent message    │
                │ history (纯净版)  │
                └──────────────────┘
                         │
                         ▼ (后续请求)
                ┌──────────────────┐
                │ outbound API     │
                │ (无 thinking)    │
                └──────────────────┘
```

## 3. 实现策略（按平台）

### 3.1 Claude Code (Anthropic API) — ✅ 无需改动

Anthropic Messages API 协议原生处理：
- `type: "thinking"` content block 是 API 协议层结构
- 文档明确声明：thinking blocks 自动隔离，不进 message history
- 后续请求的 messages 数组不包含 thinking blocks
- **验证**: 已通过 Anthropic API 文档 + Claude Code 源码确认

**不需要 hook，不需要代理层改动。**

### 3.2 OpenCode (OpenAI 兼容 API) — ❌ 需要改动

#### 3.2.1 问题位置

OpenCode 的 `processor.ts` 在构建 assistant message 时：

```typescript
// processor.ts — 当前行为（将 reasoning_content 存入 history）
let message: OpenAI.ChatCompletionMessageParam = {
    role: 'assistant',
    content: content
};
// Include reasoning_content | reasoning_details directly on the message
// for all assistant messages.
// reasoning_content which still needs to be sent back in subsequent requests.
if (reasoningContent || details) {
    (message as any).reasoning_content = reasoningContent;
    (message as any).reasoning = details;
}
```

然后 `transform.ts` 在 outbound 转换时：

```typescript
// transform.ts — 当前行为（保持 reasoning_content 在 outbound 消息中）
if ('reasoning_content' in msg && msg.reasoning_content) {
    // 保留并发送
}
```

#### 3.2.2 修改方案

在 `transform.ts` 的 outbound 消息转换中，**剥离 `reasoning_content` 和 `reasoning` 字段**：

```typescript
// transform.ts — 修改后
// Strip reasoning fields from outbound messages — they bloat context
// and the model doesn't need its own thinking as input
if ('reasoning_content' in msg) {
    delete (msg as any).reasoning_content;
}
if ('reasoning' in msg) {
    delete (msg as any).reasoning;
}
```

注意：
- 只影响 outbound (发送给模型的) 消息
- 不影响本地 SQLite history 中的存储（UI 仍可显示）
- 不影响 `processor.ts` 中的存储逻辑

#### 3.2.3 可选：配置开关

在 `opencode.config.json` 中增加：

```json
{
    "thinkingInContext": false  // default: false (不塞入 outbound)
}
```

### 3.3 Hermes (9998 代理) — 可选增强

如果 Hermes 网关后面挂 OpenCode（非标准 OpenAI API），需要在代理层也过滤。

已在 `anproxy.py` 中历史存在过滤代码（L482-483, L549-550），可复用。但 Boss 明确要求**不依赖代理**，所以仅作为可选的二次防御。

## 4. Carror OS 注册

### 4.1 哲学归属

| 哲学 | 对应条款 |
|------|---------|
| #4 验证 | Gate 有效性需验证—thinking 是否真的不进 context |
| #6 零信任 | 不相信上游（模型/API）会自动过滤 thinking |
| #1 Less | 减少 context token 消耗是最大收益 |
| #3 守护 | 保护 agent 不因 context 膨胀而退化 |

### 4.2 路由表入口（index.md）

添加到 PostToolUse 或新增 Thinking 段：

```
──────────────────────
Thinking Gate
──────────────────────
*→thinking-gate-strip | thinking-gate-verify
```

推荐嵌入点：
- **UserPromptSubmit**: 用户提交消息时检查上一轮响应中是否有 thinking 残留
- **PostToolUse**: 每次工具调用后检查上下文是否被 thinking 污染

### 4.3 Feature Registry 注册

```yaml
- name: thinking-gate
  philosophy: ["#1", "#6", "#4"]
  type: gate
  category: quality
  description: Thinking/Reasoning 内容门禁 — 在消息进入 context 前剥离 reasoning_content，防止 token 膨胀
  enabled_by_default: true
  evidence_level: L2
```

## 5. 实现优先级

| 优先级 | 项目 | 复杂度 | 影响 |
|--------|------|--------|------|
| P0 | OpenCode transform.ts 修改 | 低（2行代码） | 直接影响使用体验 |
| P1 | Carror OS 注册（路由表+feature registry） | 低 | 治理框架完整 |
| P2 | OpenCode 配置开关 | 低 | 用户可控 |
| P3 | Hermes 代理层二次防御 | 低 | 兜底防御 |
| — | Claude Code | 无需 | 原生已支持 |

## 6. 验证方法

### 6.1 OpenCode 验证

```bash
# 1. 启动 OpenCode 并发送一个需要 thinking 的 prompt
echo "9.11 和 9.9 哪个大" | opencode

# 2. 检查 SQLite history
sqlite3 ~/.opencode/conv.db "SELECT reasoning_content, reasoning FROM messages WHERE role='assistant' LIMIT 1;"
# → 应有 reasoning_content（本地存储正常）

# 3. 抓取 outbound API 请求
# 启动请求时用环境变量 DEBUG=1 或代理抓包
# → outbound 请求的 messages 中不应有 reasoning_content 字段

# 4. 对比 context token 用量
# 改前后各跑一轮，对比 token 差异
```

### 6.2 Claude Code 验证

Anthropic API 原生已隔离，只需确认：
```bash
# 检查 thinking block 是否出现在 message history 中
# Anthropic API response 的 usage 不包含 thinking tokens
# 已验证：API 文档确认 thinking blocks 自动隔离
```

## 7. 反模式

| 反模式 | 描述 | 对策 |
|--------|------|------|
| 过度过滤 | 把用户的 `reasoning` 相关的自然语言也过滤了 | 只过滤 JSON 字段 `reasoning_content` / `reasoning` / `type: "thinking"` |
| 修改存储层 | 把 `processor.ts` 的写入逻辑也改了，导致 UI 无法展示 | 只改 `transform.ts` outbound，不动 `processor.ts` 写入 |
| 假设上游已过滤 | "Anthropic API 已经处理了，不需要确认" | 必须抓包验证，不能假设 |
| 一刀切开关 | 用户可能想在调试时看到 thinking in context | 提供配置开关，默认关 |
| 只改一处 | 改了 outbound 没改 Hermes 代理，某些路径还在泄漏 | 所有入口都要覆盖 |

## 8. 关联机制

| 机制 | 关系 |
|------|------|
| context-guard | thinking 膨胀是 context 超限的根因之一 |
| completion-gate | thinking 导致的假"完成" |
| anti-pattern | F1（伪诚信）= 知道 thinking 膨胀但不管 |
| token-writer | token 追踪可暴露 thinking 导致的浪费 |

## 9. 待决策

1. **OpenCode 配置开关命名**：`thinkingInContext` vs `reasoningInContext` vs `thinkingGate.enabled`
2. **默认行为**：默认关（即 thinking 不进 context）— 与 Boss 需求一致
3. **是否需要在 OpenCode 的 UI 上显示 thinking**：processor.ts 保留写入，UI 组件渲染 thinking 块用 CSS 折叠

---

## 附录 A：OpenCode 源码改动

### A.1 transform.ts — outbound 剥离 reasoning_content

```typescript
// 在 assistant 消息 outbound 转换后
// 直接剥离 reasoning 字段，防止它们膨胀 context
function stripReasoning(msg: Record<string, unknown>): void {
    if ('reasoning_content' in msg) {
        delete msg.reasoning_content;
    }
    if ('reasoning' in msg) {
        delete msg.reasoning;
    }
}
```

位置：在 outbound messages 数组组装完成后、发送前调用。

### A.2 processor.ts — 保留存储逻辑（不改动）

保持当前行为：reasoning_content 存入 SQLite history，用于 UI 展示。

---

> **版本**: v1.0  
> **日期**: 2026-06-06  
> **归属**: Carror OS #7 机制 — Thinking Content Gate
