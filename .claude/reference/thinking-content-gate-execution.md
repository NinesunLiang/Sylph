# Thinking Content Gate — 执行方案
> 双法官审核用 | 2026-06-06 | v2（源码已确认）

## 一、概述

**目标**: 模型输出的 thinking/reasoning 内容只用于 UI 显示，不塞进 agent 的 message history/context，避免 token 膨胀。

**范围**:
| Agent | 协议 | 当前状态 | 改动量 |
|-------|------|---------|--------|
| Claude Code | Anthropic Messages API | ✅ 原生已处理，无需改动 | 0 |
| **OpenCode** | 内部 AI SDK (ModelMessage) | ❌ `reasoning` part 通过 `providerOptions` 注入 outbound | **1 个文件改 5 行** |

**验收标准**:
1. OpenCode 运行时，outbound API 请求的 messages 中无 `providerOptions.openaiCompatible.reasoning_content` 等 reasoning 字段
2. 本地存储的 `reasoning` part 不受影响（UI 可正常显示 thinking 块）
3. Claude Code 不变动，确认 Anthropic API 已隔离（已有验证）

---

## 二、Claude Code 侧 — 无需改动

### 2.1 证据链

Anthropic Messages API 规范明确声明 `type: "thinking"` content block 是协议级结构，API 层自动隔离。

### 2.2 Carror OS Hook（已部署 — 不需要再改）

| 项目 | 路径 | 状态 |
|------|------|------|
| Hook 脚本 | `.claude/hooks/thinking-gate.sh` | ✅ 已创建 |
| Settings.json 注册 | `UserPromptSubmit → .*` 匹配器 | ✅ 已添加 |
| Index.md 路由 | `.*→pretool-approve-detect\|thinking-gate` | ✅ 已添加 |
| Feature Registry | `thinking-gate` 条目 | ✅ 已添加 |
| AGENTS.md 路由索引 | Thinking Gate 条目 | ✅ 已添加 |
| 设计文档 | `.claude/reference/thinking-content-gate.md` | ✅ 已创建 |

---

## 三、OpenCode 侧 — 需要改动

### 3.1 问题根因

**文件**: `packages/opencode/src/provider/transform.ts`（源码已验证）

**关键函数**: `normalizeMessages()` (L65-321)

**问题逻辑**: L286-318 — `interleaved` 能力判断：

```typescript
// L286-318: 当前行为 — 把 reasoning 从 content 剥离后放入 providerOptions
if (model.capabilities.interleaved.field) {
    const field = model.capabilities.interleaved.field  // 通常是 "reasoning_content"
    return msgs.map((msg) => {
        if (msg.role === "assistant" && Array.isArray(msg.content)) {
            const reasoningParts = msg.content.filter(part => part.type === "reasoning")
            const reasoningText = reasoningParts.map(part => part.text).join("")
            const filteredContent = msg.content.filter(part => part.type !== "reasoning")
            
            return {
                ...msg,
                content: filteredContent,
                providerOptions: {
                    ...msg.providerOptions,
                    openaiCompatible: {
                        ...msg.providerOptions?.openaiCompatible,
                        [field]: reasoningText,  // ← 这里把 reasoning 注入 outbound
                    },
                },
            }
        }
        return msg
    })
}
```

**存储层**: reasoning 仍然以 `type: "reasoning"` 的 part 存在 ModelMessage 中 → 写入 SQLite → UI 展示正常。问题是 **`providerOptions.openaiCompatible[field]`** 把这个 reasoning 文本作为 outbound 字段发回去了。

### 3.2 改动方案

**改动点**: `transform.ts` L300-310 — 在 `interleaved` 区块中，控制是否将 reasoning 放入 `providerOptions`。

#### 方案 A（推荐 — 最简，不改配置系统）

```typescript
// 改动前 L300-312:
// All assistant messages include reasoning_content | reasoning_details.
// Always set the field even when empty — some providers (DeepSeek) may return
// empty reasoning_content which still needs to be sent back.

// 改动后：只保留空 reasoning（满足 DeepSeek 协议要求），剥离非空 reasoning
return {
    ...msg,
    content: filteredContent,
    providerOptions: reasoningText.trim() === "" ? {
        ...msg.providerOptions,
        openaiCompatible: {
            ...msg.providerOptions?.openaiCompatible,
            [field]: "",
        },
    } : {
        ...msg.providerOptions,
    },
}
```

**策略**: 
- reasoning 为空字符串 → 保留空字段（满足 DeepSeek 协议要求）
- reasoning 有内容 → 不放入 `providerOptions`（不进 outbound context）

#### 方案 B（带配置开关 — 更完整，但需要改 config 系统）

需要：
1. 在 provider config 或 model config 中加 `thinkingInContext: boolean`
2. 在 `transform.ts` 中读配置做判断

**复杂度**: 需要改多个文件，推荐作为 V2。

#### 选择建议：先用方案 A（5 行改动），V2 再加开关

### 3.3 精确改动位置

```
文件: packages/opencode/src/provider/transform.ts
行号: L300 → L312
改动: 将 providerOptions 注入逻辑替换为"空 reasoning 保留，非空剥离"
```

### 3.4 不修改的文件

- `packages/opencode/src/provider/processor.ts` — 存储逻辑不动（UI 展示需要）
- 前端 UI 文件 — thinking 块的渲染逻辑不动
- config 系统 — 本次不改

---

## 四、验证方法

| # | 步骤 | 操作 | 预期 |
|---|------|------|------|
| 1 | UI 验证 | 启动 OpenCode，发 "9.11 比 9.9 大吗" | AI 显示 thinking 块（UI 正常） |
| 2 | 本地存储 | `sqlite3 ~/.opencode/conv.db "SELECT content FROM messages WHERE json_extract(content, '$[0].type')='reasoning' LIMIT 1;"` | 有值（存储正常） |
| 3 | Outbound 验证 | 设置 DEBUG 环境变量或 mitmproxy 抓包 | outbound messages 中无 reasoning 字段 |
| 4 | 效果验证 | 连续对话 5 轮后检查 context token 量 | 整体 token 增长率降低 |

---

## 五、Oracle 审核重点

| 检查项 | 判定 |
|--------|------|
| 设计合理性 | ✅ 三层分离清晰 |
| 安全性 | ✅ 空 reasoning 保留（满足 DeepSeek），非空剥离（不进 context） |
| 可验证性 | ✅ 4 步验证，每步具体可执行 |
| 一致性 | ✅ #1(less) 减少 token + #6(0信任) 不信任上游 + #4(验证) |
| 改动量 | ✅ 1 文件 5 行，可回退 |

---

## 六、Meta-Oracle 审核重点

1. **运行时验证**: 改后 OpenCode 正常启动 + 对话 + UI 显示 thinking
2. **烟雾测试**: `reasoningText.trim() === ""` 分支 → DeepSeek 仍需空 reasoning
3. **对抗性**: 空的 `type: "reasoning", text: ""` 不会被误删（已保留）
4. **盲区**: 
   - 非 assistant 角色 → 无 reasoning part，不触发
   - Anthropic API 使用的模型 → `interleaved` 能力为 false，不走此路径
   - 已对 DeepSeek 做特殊处理（L268-284 强制加空 reasoning）
5. **回退**: 改回注释的 5 行代码即可恢复原行为

---

## 七、执行计划

```
Step 1: ✅ Oracle 审核本方案（静态）
Step 2: Meta-Oracle 审核（可使用已 clone 的源码做验证）
Step 3: ACCEPT → 修改 transform.ts
Step 4: 验收（抓包验证 outbound 无 reasoning_content）
Step 5: 清理 /tmp/opencode-source + 更新文档
```
